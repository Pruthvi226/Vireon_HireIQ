package com.aicoach.domain;

import jakarta.persistence.*;

import java.time.Instant;

@Entity
@Table(name = "questions", indexes = {
        @Index(name = "idx_questions_interview", columnList = "interview_id")
})
public class QuestionEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "interview_id", nullable = false)
    private InterviewEntity interview;

    @Lob
    @Column(name = "question_text", nullable = false)
    private String questionText;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    @OneToOne(mappedBy = "question", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private AnswerEntity answer;

    public Long getId() {
        return id;
    }

    public InterviewEntity getInterview() {
        return interview;
    }

    public void setInterview(InterviewEntity interview) {
        this.interview = interview;
    }

    public String getQuestionText() {
        return questionText;
    }

    public void setQuestionText(String questionText) {
        this.questionText = questionText;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public AnswerEntity getAnswer() {
        return answer;
    }

    public void setAnswer(AnswerEntity answer) {
        this.answer = answer;
    }
}

