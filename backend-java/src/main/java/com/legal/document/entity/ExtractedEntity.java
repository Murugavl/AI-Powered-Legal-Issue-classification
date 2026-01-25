package com.legal.document.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "extracted_entities")
public class ExtractedEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id", nullable = false)
    private CaseSession session;

    @Column(name = "entity_key", nullable = false)
    private String entityKey; // e.g. "date_of_incident", "accused_name"

    @Column(name = "entity_value", columnDefinition = "TEXT")
    private String entityValue;

    @Column(name = "confidence_score")
    private Double confidenceScore;

    @Column(name = "extracted_at")
    private LocalDateTime extractedAt;

    public ExtractedEntity() {
    }

    @PrePersist
    protected void onCreate() {
        extractedAt = LocalDateTime.now();
    }

    // Getters and Setters

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public CaseSession getSession() {
        return session;
    }

    public void setSession(CaseSession session) {
        this.session = session;
    }

    public String getEntityKey() {
        return entityKey;
    }

    public void setEntityKey(String entityKey) {
        this.entityKey = entityKey;
    }

    public String getEntityValue() {
        return entityValue;
    }

    public void setEntityValue(String entityValue) {
        this.entityValue = entityValue;
    }

    public Double getConfidenceScore() {
        return confidenceScore;
    }

    public void setConfidenceScore(Double confidenceScore) {
        this.confidenceScore = confidenceScore;
    }

    public LocalDateTime getExtractedAt() {
        return extractedAt;
    }
}
