package com.legal.document.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "legal_cases")
public class LegalCase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "case_id")
    private Long caseId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "reference_number", unique = true, nullable = false, length = 50)
    private String referenceNumber;

    @Column(name = "issue_type", nullable = false, length = 50)
    private String issueType;

    @Column(name = "sub_category", nullable = false, length = 50)
    private String subCategory;

    @Column(name = "status", length = 30)
    private String status = "draft";

    @Column(name = "suggested_authority", length = 200)
    private String suggestedAuthority;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @Column(name = "session_id", length = 100)
    private String sessionId;

    public LegalCase() {
    }

    public LegalCase(Long caseId, User user, String referenceNumber, String issueType, String subCategory,
            String status, String suggestedAuthority, LocalDateTime createdAt, LocalDateTime updatedAt,
            LocalDateTime completedAt, String sessionId) {
        this.caseId = caseId;
        this.user = user;
        this.referenceNumber = referenceNumber;
        this.issueType = issueType;
        this.subCategory = subCategory;
        this.status = status;
        this.suggestedAuthority = suggestedAuthority;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.completedAt = completedAt;
        this.sessionId = sessionId;
    }

    public Long getCaseId() {
        return caseId;
    }

    public void setCaseId(Long caseId) {
        this.caseId = caseId;
    }

    public User getUser() {
        return user;
    }

    public void setUser(User user) {
        this.user = user;
    }

    public String getReferenceNumber() {
        return referenceNumber;
    }

    public void setReferenceNumber(String referenceNumber) {
        this.referenceNumber = referenceNumber;
    }

    public String getIssueType() {
        return issueType;
    }

    public void setIssueType(String issueType) {
        this.issueType = issueType;
    }

    public String getSubCategory() {
        return subCategory;
    }

    public void setSubCategory(String subCategory) {
        this.subCategory = subCategory;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getSuggestedAuthority() {
        return suggestedAuthority;
    }

    public void setSuggestedAuthority(String suggestedAuthority) {
        this.suggestedAuthority = suggestedAuthority;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public LocalDateTime getCompletedAt() {
        return completedAt;
    }

    public void setCompletedAt(LocalDateTime completedAt) {
        this.completedAt = completedAt;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
