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
import com.legal.document.repository.DBFileRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class SessionService {

    @Autowired private CaseSessionRepository  sessionRepository;
    @Autowired private CaseAnswerRepository   answerRepository;
    @Autowired private ExtractedEntityRepository entityRepository;
    @Autowired private UserRepository         userRepository;
    @Autowired private LegalServiceAgent      legalServiceAgent;
    @Autowired private DBFileRepository       dbFileRepository;

    // ----------------------------------------------------------------
    // START SESSION
    // ----------------------------------------------------------------
    @Transactional
    public SessionResponse startSession(StartSessionRequest request, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = new CaseSession();
        session.setUser(user);
        session.setStatus("ACTIVE");
        session.setConfidenceScore(0.0);
        session = sessionRepository.save(session);

        return processInteraction(session, request.getInitialText());
    }

    // ----------------------------------------------------------------
    // SUBMIT TEXT ANSWER
    // ----------------------------------------------------------------
    @Transactional
    public SessionResponse submitAnswer(String sessionId, SubmitAnswerRequest request, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        return processInteraction(session, request.getAnswerText());
    }

    // ----------------------------------------------------------------
    // SUBMIT VOICE ANSWER
    // ----------------------------------------------------------------
    @Transactional
    public SessionResponse submitVoiceAnswer(String sessionId, MultipartFile audioFile,
                                              String transcript, String language, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        if (audioFile != null && !audioFile.isEmpty()) {
            saveFile(session, audioFile);
        }

        // Voice transcript is processed exactly like a text answer
        String text = (transcript != null && !transcript.isBlank()) ? transcript : "";
        return processInteraction(session, text);
    }

    // ----------------------------------------------------------------
    // UPLOAD EVIDENCE FILE
    // ----------------------------------------------------------------
    @Transactional
    public SessionResponse uploadEvidence(String sessionId, MultipartFile file, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        if (file != null && !file.isEmpty()) {
            saveFile(session, file);
            // Inform the NLP engine so it records this as evidence
            String name = file.getOriginalFilename() != null ? file.getOriginalFilename() : "evidence file";
            return processInteraction(session, "I have uploaded evidence: " + name);
        }

        SessionResponse response = new SessionResponse();
        response.setSessionId(session.getSessionId());
        response.setStatus(session.getStatus());
        response.setMessage("No file received. Please try uploading again.");
        return response;
    }

    // ----------------------------------------------------------------
    // GET SESSION STATUS
    // ----------------------------------------------------------------
    @Transactional(readOnly = true)
    public SessionResponse getSessionStatus(String sessionId, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        SessionResponse response = new SessionResponse();
        response.setSessionId(session.getSessionId());
        response.setStatus(session.getStatus());
        response.setDetectedIntent(session.getDetectedIntent());
        response.setReadinessScore(session.getReadinessScore());
        response.setMessage("Session is " + session.getStatus().toLowerCase() + ".");
        return response;
    }

    // ----------------------------------------------------------------
    // DELETE SESSION
    // ----------------------------------------------------------------
    @Transactional
    public void deleteSession(String sessionId, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        entityRepository.deleteAll(entityRepository.findBySession_SessionId(sessionId));
        answerRepository.deleteAll(answerRepository.findBySession_SessionIdOrderByCreatedAtAsc(sessionId));
        sessionRepository.delete(session);
    }

    // ----------------------------------------------------------------
    // LIST USER SESSIONS
    // ----------------------------------------------------------------
    @Transactional(readOnly = true)
    public List<SessionResponse> getUserSessions(String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        return sessionRepository.findByUser_UserIdOrderByUpdatedAtDesc(user.getUserId())
                .stream()
                .map(s -> {
                    SessionResponse r = new SessionResponse();
                    r.setSessionId(s.getSessionId());
                    r.setStatus(s.getStatus());
                    r.setDetectedIntent(s.getDetectedIntent());
                    r.setReadinessScore(s.getReadinessScore());
                    return r;
                })
                .collect(Collectors.toList());
    }

    // ----------------------------------------------------------------
    // CORE INTERACTION — calls Python NLP, saves to DB, returns DTO
    // ----------------------------------------------------------------
    private SessionResponse processInteraction(CaseSession session, String userMessage) {
        // 1. Persist user message
        CaseAnswer userEntry = new CaseAnswer();
        userEntry.setSession(session);
        userEntry.setUserResponse(userMessage);
        answerRepository.save(userEntry);

        // 2. Call Python NLP agent
        Map<String, Object> agentResponse = legalServiceAgent.processUserMessage(
                session.getSessionId(), userMessage);

        String content = (String) agentResponse.getOrDefault("content", "");
        Boolean isDoc  = (Boolean) agentResponse.get("is_document");

        // 3. Persist assistant reply (store abbreviated text, not the full document JSON)
        CaseAnswer agentEntry = new CaseAnswer();
        agentEntry.setSession(session);
        agentEntry.setQuestionText(Boolean.TRUE.equals(isDoc) ? "[DOCUMENT GENERATED]" : content);
        answerRepository.save(agentEntry);

        // 4. Update session metadata
        String intent = (String) agentResponse.get("intent");
        if (intent != null && !intent.isBlank()) {
            session.setDetectedIntent(intent);
        }

        Object scoreObj = agentResponse.get("readiness_score");
        if (scoreObj instanceof Number) {
            session.setReadinessScore(((Number) scoreObj).intValue());
        }

        if (Boolean.TRUE.equals(isDoc)) {
            session.setStatus("COMPLETED");
        }

        sessionRepository.save(session);

        // 5. Build and return DTO
        return buildResponse(session, agentResponse);
    }

    // ----------------------------------------------------------------
    // BUILD RESPONSE DTO
    // ----------------------------------------------------------------
    @SuppressWarnings("unchecked")
    private SessionResponse buildResponse(CaseSession session, Map<String, Object> agentResponse) {
        SessionResponse response = new SessionResponse();
        response.setSessionId(session.getSessionId());
        response.setStatus(session.getStatus());

        String  content = (String)  agentResponse.getOrDefault("content", "");
        Boolean isDoc   = (Boolean) agentResponse.get("is_document");
        Boolean isConf  = (Boolean) agentResponse.get("is_confirmation");

        if (Boolean.TRUE.equals(isDoc) && content.startsWith("DOCUMENT_READY")) {
            // Strip the prefix — send only the clean JSON payload to the frontend
            String docPayload = content.substring("DOCUMENT_READY".length()).trim();
            response.setDocumentPayload(docPayload);
            response.setMessage("Your legal document has been prepared. You can preview and download it below.");
            response.setComplete(true);
            // Use readiness score from the document payload (recalculated at generation time)
            int finalScore = session.getReadinessScore() != null ? session.getReadinessScore() : 0;
            try {
                com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
                com.fasterxml.jackson.databind.JsonNode node = mapper.readTree(docPayload);
                if (node.has("readiness_score")) {
                    finalScore = node.get("readiness_score").asInt(finalScore);
                    session.setReadinessScore(finalScore);
                }
            } catch (Exception ignored) {}
            response.setReadinessScore(finalScore);
        } else {
            // Strip any accidental markdown the LLM may produce
            String cleanContent = content.replace("**", "").replace("__", "");
            response.setMessage(cleanContent);
            response.setComplete(false);
            response.setConfirmation(Boolean.TRUE.equals(isConf));

            Object scoreObj = agentResponse.get("readiness_score");
            if (scoreObj instanceof Number) {
                response.setReadinessScore(((Number) scoreObj).intValue());
            }
        }

        // Intent
        String intent = (String) agentResponse.get("intent");
        if (intent != null && !intent.isBlank()) {
            response.setDetectedIntent(intent);
        }

        // Extracted entities (facts collected so far — shown in the sidebar)
        try {
            Map<String, Object> entities = (Map<String, Object>) agentResponse.get("entities");
            if (entities != null) {
                Map<String, String> stringEntities = entities.entrySet().stream()
                        .filter(e -> e.getValue() != null)
                        .collect(Collectors.toMap(
                                Map.Entry::getKey,
                                e -> String.valueOf(e.getValue())));
                response.setExtractedEntities(stringEntities);
            }
        } catch (Exception ignored) {}

        return response;
    }

    // ----------------------------------------------------------------
    // FILE HELPER
    // ----------------------------------------------------------------
    private void saveFile(CaseSession session, MultipartFile file) {
        try {
            DBFile dbFile = new DBFile(
                    file.getOriginalFilename(),
                    file.getContentType(),
                    file.getBytes(),
                    session);
            dbFileRepository.save(dbFile);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
