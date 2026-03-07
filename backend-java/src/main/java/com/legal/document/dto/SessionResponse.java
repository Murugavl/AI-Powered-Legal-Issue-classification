package com.legal.document.dto;

import java.util.Map;

public class SessionResponse {
    private String sessionId;
    private String status;
    private String message;          // chat message shown to user
    private String detectedIntent;
    private Map<String, String> extractedEntities; // facts collected so far
    private boolean isComplete;
    private boolean isConfirmation;  // true when showing summary for user to confirm
    private Integer readinessScore;
    private String documentPayload;  // JSON string of bilingual document (when isComplete=true)

    public SessionResponse() {}

    public String getSessionId()                              { return sessionId; }
    public void   setSessionId(String v)                      { this.sessionId = v; }

    public String getStatus()                                 { return status; }
    public void   setStatus(String v)                         { this.status = v; }

    public String getMessage()                                { return message; }
    public void   setMessage(String v)                        { this.message = v; }

    public String getDetectedIntent()                         { return detectedIntent; }
    public void   setDetectedIntent(String v)                 { this.detectedIntent = v; }

    public Map<String, String> getExtractedEntities()         { return extractedEntities; }
    public void   setExtractedEntities(Map<String, String> v) { this.extractedEntities = v; }

    public boolean isComplete()                               { return isComplete; }
    public void    setComplete(boolean v)                     { this.isComplete = v; }

    public boolean isConfirmation()                           { return isConfirmation; }
    public void    setConfirmation(boolean v)                 { this.isConfirmation = v; }

    public Integer getReadinessScore()                        { return readinessScore; }
    public void    setReadinessScore(Integer v)               { this.readinessScore = v; }

    public String getDocumentPayload()                        { return documentPayload; }
    public void   setDocumentPayload(String v)                { this.documentPayload = v; }
}
