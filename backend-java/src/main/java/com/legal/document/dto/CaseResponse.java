package com.legal.document.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.time.LocalDateTime;
import java.util.Map;

public class CaseResponse {
    private Long caseId;
    private String referenceNumber;
    private String issueType;
    private String subCategory;
    private String status;
    private String suggestedAuthority;
    private Map<String, EntityInfo> entities;
    private Double completeness;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public CaseResponse() {
    }

    public CaseResponse(Long caseId, String referenceNumber, String issueType, String subCategory, String status,
            String suggestedAuthority, Map<String, EntityInfo> entities, Double completeness, LocalDateTime createdAt,
            LocalDateTime updatedAt) {
        this.caseId = caseId;
        this.referenceNumber = referenceNumber;
        this.issueType = issueType;
        this.subCategory = subCategory;
        this.status = status;
        this.suggestedAuthority = suggestedAuthority;
        this.entities = entities;
        this.completeness = completeness;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Long getCaseId() {
        return caseId;
    }

    public void setCaseId(Long caseId) {
        this.caseId = caseId;
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

    public Map<String, EntityInfo> getEntities() {
        return entities;
    }

    public void setEntities(Map<String, EntityInfo> entities) {
        this.entities = entities;
    }

    public Double getCompleteness() {
        return completeness;
    }

    public void setCompleteness(Double completeness) {
        this.completeness = completeness;
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

    public static class EntityInfo {
        private String value;
        private Boolean confirmed;
        private Double confidence;

        public EntityInfo() {
        }

        public EntityInfo(String value, Boolean confirmed, Double confidence) {
            this.value = value;
            this.confirmed = confirmed;
            this.confidence = confidence;
        }

        public String getValue() {
            return value;
        }

        public void setValue(String value) {
            this.value = value;
        }

        public Boolean getConfirmed() {
            return confirmed;
        }

        public void setConfirmed(Boolean confirmed) {
            this.confirmed = confirmed;
        }

        public Double getConfidence() {
            return confidence;
        }

        public void setConfidence(Double confidence) {
            this.confidence = confidence;
        }
    }
}
