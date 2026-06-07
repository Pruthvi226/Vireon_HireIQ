package com.aicoach.web.dto;

import com.aicoach.domain.InterviewType;
import com.aicoach.domain.InterviewerMode;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public class InterviewDtos {
    public record StartInterviewRequest(
            @NotBlank @Size(max = 100) String role,
            @NotNull InterviewType interviewType,
            @NotNull InterviewerMode interviewerMode
    ) {
    }

    public record StartInterviewResponse(
            Long interviewId,
            Long questionId,
            String questionText
    ) {
    }

    public record QuestionResponse(
            Long questionId,
            String questionText
    ) {
    }

    public record SubmitAnswerRequest(
            @NotNull Long questionId,
            @Size(max = 20000) String answerText,
            @Size(max = 500) String audioUrl
    ) {
    }

    public record SubmitAnswerResponse(
            Long answerId,
            BigDecimal aiScore,
            String feedbackText,
            QuestionResponse nextQuestion
    ) {
    }

    public record InterviewFeedbackResponse(
            BigDecimal overallScore,
            BigDecimal communicationScore,
            BigDecimal technicalScore,
            BigDecimal confidenceScore,
            String strengths,
            String weaknesses,
            String suggestions
    ) {
    }

    public record FinishInterviewResponse(
            InterviewFeedbackResponse feedback
    ) {
    }

    public record InterviewHistoryItem(
            Long id,
            String role,
            InterviewType interviewType,
            InterviewerMode interviewerMode,
            BigDecimal score,
            Instant createdAt
    ) {
    }

    public record InterviewHistoryPage(
            List<InterviewHistoryItem> content,
            int page,
            int size,
            long totalElements,
            int totalPages
    ) {
    }
}
