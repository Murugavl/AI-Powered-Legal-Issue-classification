package com.legal.document.service;

import com.legal.document.dto.SessionResponse;
import com.legal.document.dto.StartSessionRequest;
import com.legal.document.dto.SubmitAnswerRequest;
import com.legal.document.entity.CaseAnswer;
import com.legal.document.entity.CaseSession;
import com.legal.document.entity.DBFile;
import com.legal.document.entity.ExtractedEntity;
import com.legal.document.entity.User;
import com.legal.document.repository.CaseAnswerRepository;
import com.legal.document.repository.CaseSessionRepository;
import com.legal.document.repository.ExtractedEntityRepository;
import com.legal.document.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import java.util.HashMap;
import java.util.Map;
import org.springframework.web.multipart.MultipartFile;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
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
    private com.fasterxml.jackson.databind.ObjectMapper objectMapper;

    @Autowired
    private UserRepository userRepository;

    private final RestTemplate restTemplate = new RestTemplate();
    private final String NLP_SERVICE_URL = "http://localhost:8000/analyze";

    @Transactional
    public SessionResponse startSession(StartSessionRequest request, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        // Create new session
        CaseSession session = new CaseSession();
        session.setUser(user);
        session.setStatus("ACTIVE");
        session.setConfidenceScore(0.0);
        sessionRepository.save(session);

        // Treat initial text as the first "Answer" to the implicit question "What is
        // your issue?"
        // We call NLP immediately
        return processInteraction(session, "What is your issue?", request.getInitialText());
    }

    @Transactional
    public SessionResponse submitAnswer(String sessionId, SubmitAnswerRequest request, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        // Retrieve the last question asked (if we tracked it robustly, for now we
        // assume implicit flow)
        // In a real system, we'd store the "pending question" in the session.
        String contextQuestion = getLastQuestion(session);

        return processInteraction(session, contextQuestion, request.getAnswerText());
    }

    @Transactional
    public SessionResponse getSessionStatus(String sessionId, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        return buildResponse(session, null);
    }

    @Transactional
    public SessionResponse submitVoiceAnswer(String sessionId, MultipartFile audioFile, String transcript,
            String language, String phoneNumber) {
        // ... (existing implementation)
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        String audioPath = null;
        if (audioFile != null && !audioFile.isEmpty()) {
            audioPath = saveAudioFile(session, audioFile);
        }

        String contextQuestion = getLastQuestion(session);
        return processInteraction(session, contextQuestion, transcript, audioPath, language);
    }

    @Transactional
    public SessionResponse uploadEvidence(String sessionId, MultipartFile file, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        if (file != null && !file.isEmpty()) {
            String filePath = saveEvidenceFile(session, file);
            // We can record this as an "Entity" or just a generic artifact.
            // For now, let's add it to extracted entities as "Evidence: <Filename>"
            saveOrUpdateExtractedEntity(session, "Evidence-" + System.currentTimeMillis(),
                    "File: " + file.getOriginalFilename());
        }

        return buildResponse(session, null);
    }

    @Transactional
    public void deleteSession(String sessionId, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        // Delete extracted entities
        entityRepository.deleteAll(entityRepository.findBySession_SessionId(sessionId));
        // Delete answers
        answerRepository.deleteAll(answerRepository.findBySession_SessionIdOrderByCreatedAtAsc(sessionId));
        // Delete session
        sessionRepository.delete(session);

        // Note: In production, we should also delete the files from disk.
    }

    @Autowired
    private com.legal.document.repository.DBFileRepository dbFileRepository;

    // ...

    private String saveEvidenceFile(CaseSession session, MultipartFile file) {
        try {
            DBFile dbFile = new DBFile(file.getOriginalFilename(), file.getContentType(), file.getBytes(), session);
            dbFileRepository.save(dbFile);
            return "db:" + dbFile.getId(); // Return a reference ID
        } catch (java.io.IOException e) {
            e.printStackTrace();
            return null;
        }
    }

    private String saveAudioFile(CaseSession session, MultipartFile file) {
        try {
            DBFile dbFile = new DBFile(file.getOriginalFilename(), file.getContentType(), file.getBytes(), session);
            dbFileRepository.save(dbFile);
            return "db:" + dbFile.getId();
        } catch (java.io.IOException e) {
            e.printStackTrace();
            return null;
        }
    }

    private SessionResponse processInteraction(CaseSession session, String questionText, String userResponse) {
        return processInteraction(session, questionText, userResponse, null, "en");
    }

    private SessionResponse processInteraction(CaseSession session, String questionText, String userResponse,
            String audioPath, String language) {
        // 1. Save the Q&A pair
        CaseAnswer answer = new CaseAnswer();
        answer.setSession(session);
        answer.setQuestionText(questionText);
        answer.setUserResponse(userResponse);
        answer.setAudioFilePath(audioPath);
        answer.setDetectedLanguage(language);
        answerRepository.save(answer);

        // 2. Aggregate all info for context (simplistic: full history concatenation)
        // In pro version: send structured context
        String combinedHistory = getCombinedHistory(session);

        // 3. Call NLP Service
        Map<String, Object> nlpRequest = new HashMap<>();
        nlpRequest.put("text", combinedHistory);

        Map<String, Object> nlpResponse = callNlpService(nlpRequest);

        // 4. Update Session extracted facts
        updateSessionWithNlpResult(session, nlpResponse);

        // 5. Determine Next Step
        // If NLP says "next_question" is present, we ask it.
        String nextQuestion = (String) nlpResponse.get("next_question");

        return buildResponse(session, nextQuestion);
    }

    private Map<String, Object> callNlpService(Map<String, Object> payload) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(payload, headers);

            // This expects the exact JSON structure from main.py's AnalysisResponse
            return restTemplate.postForObject(NLP_SERVICE_URL, entity, Map.class);
        } catch (Exception e) {
            e.printStackTrace();
            // Fallback
            Map<String, Object> fallback = new HashMap<>();
            fallback.put("confidence", 0.0);
            return fallback;
        }
    }

    private void updateSessionWithNlpResult(CaseSession session, Map<String, Object> nlpData) {
        if (nlpData == null)
            return;

        // Update Entity Extracted
        if (nlpData.containsKey("entities")) {
            Map<String, Object> entities = (Map<String, Object>) nlpData.get("entities");
            // "issue_type" is a special one
            if (entities.containsKey("issue_type")) {
                session.setDetectedIntent((String) entities.get("issue_type"));
            }

            // Save facts
            for (Map.Entry<String, Object> entry : entities.entrySet()) {
                if (entry.getValue() != null) {
                    saveOrUpdateExtractedEntity(session, entry.getKey(), entry.getValue().toString());
                }
            }
        }

        if (nlpData.containsKey("legal_sections")) {
            session.setSuggestedSections((String) nlpData.get("legal_sections"));
        }

        if (nlpData.containsKey("filing_guidance")) {
            try {
                String guidanceJson = objectMapper.writeValueAsString(nlpData.get("filing_guidance"));
                session.setFilingGuidance(guidanceJson);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        if (nlpData.containsKey("readiness")) {
            Map<String, Object> readiness = (Map<String, Object>) nlpData.get("readiness");
            if (readiness != null) {
                if (readiness.get("score") instanceof Number) {
                    session.setReadinessScore(((Number) readiness.get("score")).intValue());
                }
                session.setReadinessStatus((String) readiness.get("status"));
            }
        }

        if (nlpData.containsKey("confidence")) {
            Object conf = nlpData.get("confidence");
            if (conf instanceof Number) {
                session.setConfidenceScore(((Number) conf).doubleValue());
            }
        }

        sessionRepository.save(session);
    }

    private void saveOrUpdateExtractedEntity(CaseSession session, String key, String value) {
        ExtractedEntity entity = entityRepository.findBySession_SessionIdAndEntityKey(session.getSessionId(), key)
                .orElse(new ExtractedEntity());

        entity.setSession(session);
        entity.setEntityKey(key);
        entity.setEntityValue(value);
        entityRepository.save(entity);
    }

    private String getCombinedHistory(CaseSession session) {
        List<CaseAnswer> answers = answerRepository.findBySession_SessionIdOrderByCreatedAtAsc(session.getSessionId());
        return answers.stream()
                .map(CaseAnswer::getUserResponse)
                .collect(Collectors.joining(". "));
    }

    private String getLastQuestion(CaseSession session) {
        return "Follow up question";
    }

    private SessionResponse buildResponse(CaseSession session, String nextQuestion) {
        SessionResponse response = new SessionResponse();
        response.setSessionId(session.getSessionId());
        response.setStatus(session.getStatus());
        response.setDetectedIntent(session.getDetectedIntent());
        response.setConfidenceScore(session.getConfidenceScore());
        response.setNextQuestion(nextQuestion);
        response.setSuggestedSections(session.getSuggestedSections());
        response.setReadinessScore(session.getReadinessScore());
        response.setReadinessStatus(session.getReadinessStatus());

        if (session.getFilingGuidance() != null) {
            try {
                Map<String, Object> guidance = objectMapper.readValue(session.getFilingGuidance(), Map.class);
                response.setFilingGuidance(guidance);
            } catch (Exception e) {
                // ignore
            }
        }

        // Entities for frontend
        List<ExtractedEntity> entities = entityRepository.findBySession_SessionId(session.getSessionId());
        Map<String, String> entityMap = entities.stream()
                .collect(Collectors.toMap(ExtractedEntity::getEntityKey, ExtractedEntity::getEntityValue));
        response.setExtractedEntities(entityMap);

        // Check if complete (simple logic)
        response.setComplete(nextQuestion == null && session.getConfidenceScore() > 0.8);

        return response;
    }
}
