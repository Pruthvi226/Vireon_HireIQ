package com.aicoach.domain;

import jakarta.persistence.*;

import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "answers", indexes = {
        @Index(name = "idx_answers_question", columnList = "question_id")
})
public class AnswerEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "question_id", nullable = false, unique = true)
    private QuestionEntity question;

    @Lob
    @Column(name = "answer_text")
    private String answerText;

    @Column(name = "audio_url", length = 500)
    private String audioUrl;

    @Column(name = "ai_score", precision = 4, scale = 2)
    private BigDecimal aiScore;

    @Lob
    @Column(name = "feedback_text")
    private String feedbackText;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    public Long getId() {
        return id;
    }

    public QuestionEntity getQuestion() {
        return question;
    }

    public void setQuestion(QuestionEntity question) {
        this.question = question;
    }

    public String getAnswerText() {
        return answerText;
    }

    public void setAnswerText(String answerText) {
        this.answerText = answerText;
    }

    public String getAudioUrl() {
        return audioUrl;
    }

    public void setAudioUrl(String audioUrl) {
        this.audioUrl = audioUrl;
    }

    public BigDecimal getAiScore() {
        return aiScore;
    }

    public void setAiScore(BigDecimal aiScore) {
        this.aiScore = aiScore;
    }

    public String getFeedbackText() {
        return feedbackText;
    }

    public void setFeedbackText(String feedbackText) {
        this.feedbackText = feedbackText;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}

