package com.aicoach.web;

import com.aicoach.service.InterviewService;
import com.aicoach.web.dto.InterviewDtos;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/interview")
public class InterviewController {
    private final InterviewService interviewService;

    public InterviewController(InterviewService interviewService) {
        this.interviewService = interviewService;
    }

    @PostMapping("/start")
    public InterviewDtos.StartInterviewResponse start(@Valid @RequestBody InterviewDtos.StartInterviewRequest request) {
        return interviewService.start(request);
    }

    @PostMapping("/{id}/question")
    public InterviewDtos.QuestionResponse nextQuestion(@PathVariable long id) {
        return interviewService.generateQuestion(id);
    }

    @PostMapping("/{id}/answer")
    public InterviewDtos.SubmitAnswerResponse answer(
            @PathVariable long id,
            @Valid @RequestBody InterviewDtos.SubmitAnswerRequest request
    ) {
        return interviewService.answer(id, request);
    }

    @GetMapping("/{id}/feedback")
    public InterviewDtos.InterviewFeedbackResponse feedback(@PathVariable long id) {
        return interviewService.getFeedback(id);
    }

    @PostMapping("/{id}/finish")
    public InterviewDtos.FinishInterviewResponse finish(@PathVariable long id) {
        return interviewService.finish(id);
    }
}
