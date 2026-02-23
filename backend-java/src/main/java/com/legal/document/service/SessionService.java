package com.legal.document.service;

import com.legal.document.dto.SessionResponse;
import com.legal.document.dto.StartSessionRequest;
import com.legal.document.dto.SubmitAnswerRequest;
import com.legal.document.entity.CaseAnswer;
import com.legal.document.entity.CaseSession;
import com.legal.document.entity.DBFile;
import com.legal.document.entity.User;
import com.legal.document.repository.CaseAnswerRepository;
import com.legal.document.repository.CaseSessionRepository;
import com.legal.document.repository.ExtractedEntityRepository;
import com.legal.document.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import java.io.IOException;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class SessionService {

    @Autowired
    private CaseSessionRepository sessionRepository;

    @Autowired
    private CaseAnswerRepository answerRepository;

    @Autowired
    private ExtractedEntityRepository entityRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private LegalServiceAgent legalServiceAgent;

    @Autowired
    private com.legal.document.repository.DBFileRepository dbFileRepository;

    @Transactional
    public SessionResponse startSession(StartSessionRequest request, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        // Create new session
        CaseSession session = new CaseSession();
        session.setUser(user);
        session.setStatus("ACTIVE");
        session.setConfidenceScore(0.0);
        session = sessionRepository.save(session);

        // Process initial interaction
        return processInteraction(session, request.getInitialText());
    }

    @Transactional
    public SessionResponse submitAnswer(String sessionId, SubmitAnswerRequest request, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        return processInteraction(session, request.getAnswerText());
    }

    @Transactional
    public SessionResponse getSessionStatus(String sessionId, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        // For status, we can't easily re-fetch the last agent response structure
        // without storing it fully.
        // For now, we return a basic response or we could cache the last response JSON
        // in the session entity.
        // To keep it simple as per "Java matches User input", we just return empty or
        // last question text.
        // But since we need "Map" for buildResponse, we'll create a dummy map.
        // In a real impl, we'd store the last JSON blob.

        return buildResponse(session, Map.of("content", "Session Active"));
    }

    @Transactional
    public SessionResponse submitVoiceAnswer(String sessionId, MultipartFile audioFile, String transcript,
            String language, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        if (audioFile != null && !audioFile.isEmpty()) {
            saveAudioFile(session, audioFile);
        }

        // Use transcript as the answer
        return processInteraction(session, transcript != null ? transcript : "");
    }

    @Transactional
    public SessionResponse uploadEvidence(String sessionId, MultipartFile file, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        if (file != null && !file.isEmpty()) {
            saveEvidenceFile(session, file);
        }

        return buildResponse(session, Map.of("content", "Evidence Uploaded"));
    }

    @Transactional
    public void deleteSession(String sessionId, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        // Delete associated data
        entityRepository.deleteAll(entityRepository.findBySession_SessionId(sessionId));
        answerRepository.deleteAll(answerRepository.findBySession_SessionIdOrderByCreatedAtAsc(sessionId));
        sessionRepository.delete(session);
    }

    private String saveEvidenceFile(CaseSession session, MultipartFile file) {
        try {
            DBFile dbFile = new DBFile(file.getOriginalFilename(), file.getContentType(), file.getBytes(), session);
            dbFileRepository.save(dbFile);
            return "db:" + dbFile.getId();
        } catch (IOException e) {
            e.printStackTrace();
            return null;
        }
    }

    private String saveAudioFile(CaseSession session, MultipartFile file) {
        try {
            DBFile dbFile = new DBFile(file.getOriginalFilename(), file.getContentType(), file.getBytes(), session);
            dbFileRepository.save(dbFile);
            return "db:" + dbFile.getId();
        } catch (IOException e) {
            e.printStackTrace();
            return null;
        }
    }

    private SessionResponse processInteraction(CaseSession session, String userMessage) {
        // 1. Save the user message locally
        CaseAnswer answer = new CaseAnswer();
        answer.setSession(session);
        answer.setUserResponse(userMessage);
        answerRepository.save(answer);

        // 2. Call Python Agent via LegalServiceAgent
        Map<String, Object> agentResponse = legalServiceAgent.processUserMessage(session.getSessionId(), userMessage);

        String content = (String) agentResponse.getOrDefault("content", "");

        // 3. Save the Agent's "Question" or response
        CaseAnswer agentEntry = new CaseAnswer();
        agentEntry.setSession(session);
        agentEntry.setQuestionText(content);
        answerRepository.save(agentEntry);

        // 4. Return DTO
        return buildResponse(session, agentResponse);
    }

    @SuppressWarnings("unchecked")
    private SessionResponse buildResponse(CaseSession session, Map<String, Object> agentResponse) {
        SessionResponse response = new SessionResponse();
        response.setSessionId(session.getSessionId());
        response.setStatus(session.getStatus());

        String content = (String) agentResponse.get("content");
        response.setNextQuestion(content);

        // Extract metadata
        if (agentResponse.containsKey("intent")) {
            response.setDetectedIntent((String) agentResponse.get("intent"));
        }

        if (agentResponse.containsKey("readiness_score")) {
            Object scoreObj = agentResponse.get("readiness_score");
            if (scoreObj instanceof Number) {
                response.setReadinessScore(((Number) scoreObj).intValue());
            }
        }

        if (agentResponse.containsKey("entities")) {
            try {
                Map<String, Object> entities = (Map<String, Object>) agentResponse.get("entities");
                if (entities != null) {
                    Map<String, String> stringEntities = entities.entrySet().stream()
                            .collect(Collectors.toMap(Map.Entry::getKey, e -> String.valueOf(e.getValue())));
                    response.setExtractedEntities(stringEntities);
                }
            } catch (Exception e) {
                // ignore
            }
        }

        // Determine completion
        Boolean isDoc = (Boolean) agentResponse.get("is_document");
        if (Boolean.TRUE.equals(isDoc)) {
            response.setComplete(true);
            if (response.getReadinessScore() == null)
                response.setReadinessScore(100);
        } else {
            response.setComplete(false);
        }

        // Determine confirmation phase
        Boolean isConf = (Boolean) agentResponse.get("is_confirmation");
        if (Boolean.TRUE.equals(isConf)) {
            response.setConfirmation(true);
        } else {
            response.setConfirmation(false);
        }

        return response;
    }
}
