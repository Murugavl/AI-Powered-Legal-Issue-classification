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
import com.legal.document.entity.ExtractedEntity;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.ArrayList;
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

        // Inject the user's phone (from auth) as a pre-filled fact so the
        // NLP engine never needs to ask the user for their phone number.
        // The __PREFILL__ prefix is stripped by graph.py before classification.
        String fullName = user.getFullName() != null ? user.getFullName() : "";
        String seedMsg = "__PREFILL__ user_phone=" + phoneNumber + " user_full_name=\"" + fullName + "\" || " + request.getInitialText();
        return processInteraction(session, seedMsg);
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
                                              String transcript, String language,
                                              boolean transcriptConfirmed, String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        CaseSession session = sessionRepository.findBySessionIdAndUser_UserId(sessionId, user.getUserId())
                .orElseThrow(() -> new RuntimeException("Session not found"));

        if (audioFile != null && !audioFile.isEmpty()) {
            saveFile(session, audioFile);
        }

        // Voice inputs are accepted only with explicit transcript confirmation in text.
        String text = (transcript != null) ? transcript.trim() : "";
        if (text.isBlank() || !transcriptConfirmed) {
            SessionResponse response = new SessionResponse();
            response.setSessionId(session.getSessionId());
            response.setStatus(session.getStatus());
            response.setMessage(
                    "For voice accessibility, please review the transcript and confirm it in text before submission.");
            response.setComplete(false);
            response.setConfirmation(true);
            return response;
        }
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
        response.setDocumentPayload(session.getDocumentPayload());
        response.setComplete("COMPLETED".equals(session.getStatus()));

        // Populate entities
        List<ExtractedEntity> entities = entityRepository.findBySession_SessionId(sessionId);
        Map<String, String> entityMap = entities.stream()
                .collect(Collectors.toMap(ExtractedEntity::getEntityKey, ExtractedEntity::getEntityValue, (a, b) -> a));
        response.setExtractedEntities(entityMap);

        // Populate history
        List<CaseAnswer> answers = answerRepository.findBySession_SessionIdOrderByCreatedAtAsc(sessionId);
        List<SessionResponse.MessageDTO> history = new ArrayList<>();
        
        for (CaseAnswer ans : answers) {
            if (ans.getUserResponse() != null && !ans.getUserResponse().isBlank()) {
                // Skip prefill messages for history display
                String text = ans.getUserResponse();
                if (text.startsWith("__PREFILL__")) {
                    int idx = text.indexOf(" || ");
                    if (idx != -1) text = text.substring(idx + 4);
                }
                history.add(new SessionResponse.MessageDTO("user", text, ans.getId()));
            }
            if (ans.getQuestionText() != null && !ans.getQuestionText().isBlank()) {
                history.add(new SessionResponse.MessageDTO("system", ans.getQuestionText(), ans.getId()));
            }
        }
        response.setHistory(history);

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

        purgeSessionData(session);
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
    @SuppressWarnings("unchecked")
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
            
            // Extract and persist document payload
            if (content.startsWith("DOCUMENT_READY")) {
                String docPayload = content.substring("DOCUMENT_READY".length()).trim();
                session.setDocumentPayload(docPayload);
                
                // Force readiness score update from payload if it has one
                try {
                    com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
                    com.fasterxml.jackson.databind.JsonNode node = mapper.readTree(docPayload);
                    if (node.has("readiness_score")) {
                        session.setReadinessScore(node.get("readiness_score").asInt(session.getReadinessScore() != null ? session.getReadinessScore() : 0));
                    }
                } catch (Exception ignored) {}
            }
        }

        sessionRepository.save(session);
        sessionRepository.flush(); // Explicit flush to ensure persistence within the transaction

        // Persist entities to database for session restoration
        try {
            Map<String, Object> entities = (Map<String, Object>) agentResponse.get("entities");
            if (entities != null) {
                for (Map.Entry<String, Object> entry : entities.entrySet()) {
                    if (entry.getValue() != null) {
                        String key = entry.getKey();
                        String val = String.valueOf(entry.getValue());
                        
                        ExtractedEntity entity = entityRepository.findBySession_SessionIdAndEntityKey(
                                session.getSessionId(), key).orElse(new ExtractedEntity());
                        
                        entity.setSession(session);
                        entity.setEntityKey(key);
                        entity.setEntityValue(val);
                        entityRepository.save(entity);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        // 5. Build and return DTO
        return buildResponse(session, agentResponse);
        // NOTE: Sessions are NOT purged on completion — they are saved to the dashboard.
        // Purge is handled only by SessionCleanupService (7-day TTL) or explicit user delete.
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
            // Use the payload already set/extracted
            String docPayload = session.getDocumentPayload();
            response.setDocumentPayload(docPayload);
            response.setMessage("Your legal document has been prepared. You can preview and download it below.");
            response.setComplete(true);
            response.setReadinessScore(session.getReadinessScore());
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

        // Practical next steps (only present on document completion)
        try {
            @SuppressWarnings("unchecked")
            List<String> nextSteps = (List<String>) agentResponse.get("next_steps");
            if (nextSteps != null && !nextSteps.isEmpty()) {
                response.setNextSteps(nextSteps);
            } else if (Boolean.TRUE.equals(isDoc)) {
                // Also try reading from the document payload
                String docPayload = response.getDocumentPayload();
                if (docPayload != null) {
                    com.fasterxml.jackson.databind.ObjectMapper m2 = new com.fasterxml.jackson.databind.ObjectMapper();
                    com.fasterxml.jackson.databind.JsonNode n2 = m2.readTree(docPayload);
                    if (n2.has("next_steps")) {
                        List<String> ns = new ArrayList<>();
                        n2.get("next_steps").forEach(node -> ns.add(node.asText()));
                        response.setNextSteps(ns);
                    }
                }
            }
        } catch (Exception ignored) {}

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

    private void purgeSessionData(CaseSession session) {
        String sid = session.getSessionId();
        entityRepository.deleteAll(entityRepository.findBySession_SessionId(sid));
        answerRepository.deleteAll(answerRepository.findBySession_SessionIdOrderByCreatedAtAsc(sid));
        dbFileRepository.deleteAll(dbFileRepository.findBySession_SessionId(sid));
        sessionRepository.delete(session);
    }
}
