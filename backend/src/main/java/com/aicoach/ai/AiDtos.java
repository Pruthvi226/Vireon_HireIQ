package com.aicoach.ai;

import com.aicoach.domain.InterviewType;
import com.aicoach.domain.InterviewerMode;

import java.math.BigDecimal;
import java.util.List;

public class AiDtos {
    public record GenerateQuestionRequest(
            String role,
            InterviewType interviewType,
            InterviewerMode interviewerMode,
            String previousQuestion,
            String previousAnswer
    ) {
    }

    public record GenerateQuestionResponse(
            String questionText
    ) {
    }

    public record AnalyzeAnswerRequest(
            String role,
            InterviewType interviewType,
            InterviewerMode interviewerMode,
            String questionText,
            String answerText
    ) {
    }

    public record AnalyzeAnswerResponse(
            BigDecimal score,
            String feedbackText
    ) {
    }

    public record QaItem(
            String question,
            String answer
    ) {
    }

    public record GenerateFeedbackRequest(
            String role,
            InterviewType interviewType,
            InterviewerMode interviewerMode,
            List<QaItem> qa
    ) {
    }

    public record GenerateFeedbackResponse(
            BigDecimal overallScore,
            BigDecimal communicationScore,
            BigDecimal technicalScore,
            BigDecimal confidenceScore,
            String strengths,
            String weaknesses,
            String suggestions
    ) {
    }

    public record ResumeAnalysisRequest(
            String filename,
            String fileBase64
    ) {
    }

    public record ResumeAnalysisResponse(
            String extractedText,
            String notes
    ) {
    }
}
