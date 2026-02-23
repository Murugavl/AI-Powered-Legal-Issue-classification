package com.legal.document.dto;

import java.util.Map;

public class SessionResponse {
    private String sessionId;
    private String status;
    private String nextQuestion; // The clarification question
    private String detectedIntent;
    private String detectedDomain;
    private Double confidenceScore;
    private Map<String, String> extractedEntities; // Confirmed facts
    private boolean isComplete;
    private boolean isConfirmation;
    private String suggestedSections;
    private Integer readinessScore;
    private String readinessStatus;
    private String readinessFeedback;
    private Map<String, Object> filingGuidance;

    public SessionResponse() {
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getNextQuestion() {
        return nextQuestion;
    }

    public void setNextQuestion(String nextQuestion) {
        this.nextQuestion = nextQuestion;
    }

    public String getDetectedIntent() {
        return detectedIntent;
    }

    public void setDetectedIntent(String detectedIntent) {
        this.detectedIntent = detectedIntent;
    }

    public String getDetectedDomain() {
        return detectedDomain;
    }

    public void setDetectedDomain(String detectedDomain) {
        this.detectedDomain = detectedDomain;
    }

    public Double getConfidenceScore() {
        return confidenceScore;
    }

    public void setConfidenceScore(Double confidenceScore) {
        this.confidenceScore = confidenceScore;
    }

    public Map<String, String> getExtractedEntities() {
        return extractedEntities;
    }

    public void setExtractedEntities(Map<String, String> extractedEntities) {
        this.extractedEntities = extractedEntities;
    }

    public boolean isComplete() {
        return isComplete;
    }

    public void setComplete(boolean complete) {
        isComplete = complete;
    }

    public boolean isConfirmation() {
        return isConfirmation;
    }

    public void setConfirmation(boolean confirmation) {
        isConfirmation = confirmation;
    }

    public String getSuggestedSections() {
        return suggestedSections;
    }

    public void setSuggestedSections(String suggestedSections) {
        this.suggestedSections = suggestedSections;
    }

    public Integer getReadinessScore() {
        return readinessScore;
    }

    public void setReadinessScore(Integer readinessScore) {
        this.readinessScore = readinessScore;
    }

    public String getReadinessStatus() {
        return readinessStatus;
    }

    public void setReadinessStatus(String readinessStatus) {
        this.readinessStatus = readinessStatus;
    }

    public String getReadinessFeedback() {
        return readinessFeedback;
    }

    public void setReadinessFeedback(String readinessFeedback) {
        this.readinessFeedback = readinessFeedback;
    }

    public Map<String, Object> getFilingGuidance() {
        return filingGuidance;
    }

    public void setFilingGuidance(Map<String, Object> filingGuidance) {
        this.filingGuidance = filingGuidance;
    }
}
