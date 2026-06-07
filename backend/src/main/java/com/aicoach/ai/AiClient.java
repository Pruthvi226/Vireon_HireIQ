package com.aicoach.ai;

import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

@Component
public class AiClient {
    private final RestClient aiRestClient;

    public AiClient(RestClient aiRestClient) {
        this.aiRestClient = aiRestClient;
    }

    public AiDtos.GenerateQuestionResponse generateQuestion(AiDtos.GenerateQuestionRequest request) {
        return post("/generate-question", request, AiDtos.GenerateQuestionResponse.class);
    }

    public AiDtos.AnalyzeAnswerResponse analyzeAnswer(AiDtos.AnalyzeAnswerRequest request) {
        return post("/analyze-answer", request, AiDtos.AnalyzeAnswerResponse.class);
    }

    public AiDtos.GenerateFeedbackResponse generateFeedback(AiDtos.GenerateFeedbackRequest request) {
        return post("/generate-feedback", request, AiDtos.GenerateFeedbackResponse.class);
    }

    public AiDtos.ResumeAnalysisResponse resumeAnalysis(AiDtos.ResumeAnalysisRequest request) {
        return post("/resume-analysis", request, AiDtos.ResumeAnalysisResponse.class);
    }

    private <T> T post(String path, Object body, Class<T> responseType) {
        try {
            return aiRestClient.post()
                    .uri(path)
                    .contentType(MediaType.APPLICATION_JSON)
                    .accept(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(responseType);
        } catch (RestClientResponseException ex) {
            throw new IllegalStateException("AI service call failed: " + ex.getStatusCode() + " " + ex.getResponseBodyAsString());
        } catch (Exception ex) {
            throw new IllegalStateException("AI service unreachable: " + ex.getMessage(), ex);
        }
    }
}
