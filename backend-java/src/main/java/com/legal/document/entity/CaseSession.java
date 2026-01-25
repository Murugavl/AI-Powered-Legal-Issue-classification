package com.legal.document.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "case_sessions")
public class CaseSession {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "session_id")
    private String sessionId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;

    @Column(name = "status")
    private String status; // ACTIVE, COMPLETED, ABANDONED

    @Column(name = "current_step")
    private Integer currentStep = 0;

    @Column(name = "detected_intent")
    private String detectedIntent;

    @Column(name = "detected_domain")
    private String detectedDomain;

    @Column(name = "confidence_score")
    private Double confidenceScore;

    @Column(name = "readiness_score")
    private Integer readinessScore; // 0-100

    @Column(name = "readiness_status")
    private String readinessStatus; // READY, WEAK_CASE, NOT_ACTIONABLE

    @Column(name = "filing_guidance", columnDefinition = "TEXT")
    private String filingGuidance; // JSON string of filing advice

    @Column(name = "suggested_sections", columnDefinition = "TEXT")
    private String suggestedSections; // JSON string of suggested legal sections

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public CaseSession() {
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
        if (status == null)
            status = "ACTIVE";
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }

    // Getters and Setters

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public User getUser() {
        return user;
    }

    public void setUser(User user) {
        this.user = user;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Integer getCurrentStep() {
        return currentStep;
    }

    public void setCurrentStep(Integer currentStep) {
        this.currentStep = currentStep;
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

    public String getFilingGuidance() {
        return filingGuidance;
    }

    public void setFilingGuidance(String filingGuidance) {
        this.filingGuidance = filingGuidance;
    }

    public String getSuggestedSections() {
        return suggestedSections;
    }

    public void setSuggestedSections(String suggestedSections) {
        this.suggestedSections = suggestedSections;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }
}
