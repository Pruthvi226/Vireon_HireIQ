package com.aicoach.domain;

import jakarta.persistence.*;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "feedbacks", indexes = {
        @Index(name = "idx_feedbacks_interview", columnList = "interview_id")
})
public class FeedbackEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "interview_id", nullable = false, unique = true)
    private InterviewEntity interview;

    @Column(name = "overall_score", nullable = false, precision = 5, scale = 2)
    private BigDecimal overallScore;

    @Column(name = "communication_score", nullable = false, precision = 5, scale = 2)
    private BigDecimal communicationScore;

    @Column(name = "technical_score", nullable = false, precision = 5, scale = 2)
    private BigDecimal technicalScore;

    @Column(name = "confidence_score", nullable = false, precision = 5, scale = 2)
    private BigDecimal confidenceScore;

    @Lob
    private String strengths;

    @Lob
    private String weaknesses;

    @Lob
    private String suggestions;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    public Long getId() {
        return id;
    }

    public InterviewEntity getInterview() {
        return interview;
    }

    public void setInterview(InterviewEntity interview) {
        this.interview = interview;
    }

    public BigDecimal getOverallScore() {
        return overallScore;
    }

    public void setOverallScore(BigDecimal overallScore) {
        this.overallScore = overallScore;
    }

    public BigDecimal getCommunicationScore() {
        return communicationScore;
    }

    public void setCommunicationScore(BigDecimal communicationScore) {
        this.communicationScore = communicationScore;
    }

    public BigDecimal getTechnicalScore() {
        return technicalScore;
    }

    public void setTechnicalScore(BigDecimal technicalScore) {
        this.technicalScore = technicalScore;
    }

    public BigDecimal getConfidenceScore() {
        return confidenceScore;
    }

    public void setConfidenceScore(BigDecimal confidenceScore) {
        this.confidenceScore = confidenceScore;
    }

    public String getStrengths() {
        return strengths;
    }

    public void setStrengths(String strengths) {
        this.strengths = strengths;
    }

    public String getWeaknesses() {
        return weaknesses;
    }

    public void setWeaknesses(String weaknesses) {
        this.weaknesses = weaknesses;
    }

    public String getSuggestions() {
        return suggestions;
    }

    public void setSuggestions(String suggestions) {
        this.suggestions = suggestions;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}

