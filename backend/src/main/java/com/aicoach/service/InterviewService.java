package com.aicoach.service;

import com.aicoach.ai.AiClient;
import com.aicoach.ai.AiDtos;
import com.aicoach.domain.*;
import com.aicoach.realtime.InterviewRealtimeService;
import com.aicoach.repo.*;
import com.aicoach.security.CurrentUser;
import com.aicoach.security.JwtService;
import com.aicoach.web.dto.InterviewDtos;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

@Service
public class InterviewService {
    private final UserRepository userRepository;
    private final InterviewRepository interviewRepository;
    private final QuestionRepository questionRepository;
    private final AnswerRepository answerRepository;
    private final FeedbackRepository feedbackRepository;
    private final AiClient aiClient;
    private final InterviewRealtimeService realtime;

    public InterviewService(
            UserRepository userRepository,
            InterviewRepository interviewRepository,
            QuestionRepository questionRepository,
            AnswerRepository answerRepository,
            FeedbackRepository feedbackRepository,
            AiClient aiClient,
            InterviewRealtimeService realtime
    ) {
        this.userRepository = userRepository;
        this.interviewRepository = interviewRepository;
        this.questionRepository = questionRepository;
        this.answerRepository = answerRepository;
        this.feedbackRepository = feedbackRepository;
        this.aiClient = aiClient;
        this.realtime = realtime;
    }

    @Transactional
    public InterviewDtos.StartInterviewResponse start(InterviewDtos.StartInterviewRequest request) {
        JwtService.AuthenticatedUser user = CurrentUser.require();
        UserEntity owner = userRepository.findById(user.id())
                .orElseThrow(() -> new IllegalStateException("User missing"));

        InterviewEntity interview = new InterviewEntity();
        interview.setUser(owner);
        interview.setRole(request.role());
        interview.setInterviewType(request.interviewType());
        interview.setInterviewerMode(request.interviewerMode());
        interview = interviewRepository.save(interview);

        QuestionEntity first = createQuestionFromAi(interview, null, null);
        InterviewDtos.QuestionResponse q = new InterviewDtos.QuestionResponse(first.getId(), first.getQuestionText());
        realtime.publish(interview.getId(), "QUESTION", q);

        return new InterviewDtos.StartInterviewResponse(interview.getId(), first.getId(), first.getQuestionText());
    }

    @Transactional
    public InterviewDtos.QuestionResponse generateQuestion(long interviewId) {
        JwtService.AuthenticatedUser user = CurrentUser.require();
        InterviewEntity interview = getOwnedInterview(interviewId, user.id());

        List<QuestionEntity> questions = questionRepository.findByInterview_IdOrderByCreatedAtAsc(interviewId);
        String prevQ = null;
        String prevA = null;
        if (!questions.isEmpty()) {
            QuestionEntity last = questions.get(questions.size() - 1);
            prevQ = last.getQuestionText();
            prevA = answerRepository.findByQuestion_Id(last.getId()).map(AnswerEntity::getAnswerText).orElse(null);
        }

        QuestionEntity next = createQuestionFromAi(interview, prevQ, prevA);
        InterviewDtos.QuestionResponse dto = new InterviewDtos.QuestionResponse(next.getId(), next.getQuestionText());
        realtime.publish(interviewId, "QUESTION", dto);
        return dto;
    }

    @Transactional
    public InterviewDtos.SubmitAnswerResponse answer(long interviewId, InterviewDtos.SubmitAnswerRequest request) {
        JwtService.AuthenticatedUser user = CurrentUser.require();
        InterviewEntity interview = getOwnedInterview(interviewId, user.id());

        QuestionEntity question = questionRepository.findById(request.questionId())
                .orElseThrow(() -> new NotFoundException("Question not found"));

        if (!Objects.equals(question.getInterview().getId(), interview.getId())) {
            throw new IllegalArgumentException("Question does not belong to this interview");
        }

        if (answerRepository.findByQuestion_Id(question.getId()).isPresent()) {
            throw new IllegalArgumentException("Answer already submitted for this question");
        }

        if ((request.answerText() == null || request.answerText().isBlank()) && (request.audioUrl() == null || request.audioUrl().isBlank())) {
            throw new IllegalArgumentException("answerText or audioUrl is required");
        }

        AiDtos.AnalyzeAnswerResponse analyzed = aiClient.analyzeAnswer(new AiDtos.AnalyzeAnswerRequest(
                interview.getRole(), interview.getInterviewType(), interview.getInterviewerMode(),
                question.getQuestionText(), request.answerText() == null ? "" : request.answerText()
        ));

        AnswerEntity answer = new AnswerEntity();
        answer.setQuestion(question);
        answer.setAnswerText(request.answerText());
        answer.setAudioUrl(request.audioUrl());
        answer.setAiScore(analyzed.score());
        answer.setFeedbackText(analyzed.feedbackText());
        answerRepository.save(answer);

        recomputeInterviewScore(interview.getId());

        realtime.publish(interview.getId(), "ANSWER_ANALYZED", new InterviewDtos.SubmitAnswerResponse(
                answer.getId(), answer.getAiScore(), answer.getFeedbackText(), null
        ));

        QuestionEntity next = createQuestionFromAi(interview, question.getQuestionText(), answer.getAnswerText());
        InterviewDtos.QuestionResponse nextDto = new InterviewDtos.QuestionResponse(next.getId(), next.getQuestionText());
        realtime.publish(interview.getId(), "QUESTION", nextDto);

        return new InterviewDtos.SubmitAnswerResponse(answer.getId(), answer.getAiScore(), answer.getFeedbackText(), nextDto);
    }

    @Transactional(readOnly = true)
    public InterviewDtos.InterviewFeedbackResponse getFeedback(long interviewId) {
        JwtService.AuthenticatedUser user = CurrentUser.require();
        getOwnedInterview(interviewId, user.id());

        FeedbackEntity feedback = feedbackRepository.findByInterview_Id(interviewId)
                .orElseThrow(() -> new NotFoundException("Feedback not ready yet"));

        return new InterviewDtos.InterviewFeedbackResponse(
                feedback.getOverallScore(), feedback.getCommunicationScore(), feedback.getTechnicalScore(),
                feedback.getConfidenceScore(), feedback.getStrengths(), feedback.getWeaknesses(), feedback.getSuggestions()
        );
    }

    @Transactional
    public InterviewDtos.FinishInterviewResponse finish(long interviewId) {
        JwtService.AuthenticatedUser user = CurrentUser.require();
        InterviewEntity interview = getOwnedInterview(interviewId, user.id());

        if (feedbackRepository.findByInterview_Id(interviewId).isPresent()) {
            throw new IllegalArgumentException("Interview already finalized");
        }

        List<QuestionEntity> questions = questionRepository.findByInterview_IdOrderByCreatedAtAsc(interviewId);
        List<AiDtos.QaItem> qa = new ArrayList<>();
        for (QuestionEntity q : questions) {
            String ans = answerRepository.findByQuestion_Id(q.getId()).map(AnswerEntity::getAnswerText).orElse(null);
            if (ans != null && !ans.isBlank()) {
                qa.add(new AiDtos.QaItem(q.getQuestionText(), ans));
            }
        }

        if (qa.isEmpty()) {
            throw new IllegalArgumentException("No answered questions to summarize");
        }

        AiDtos.GenerateFeedbackResponse fb = aiClient.generateFeedback(new AiDtos.GenerateFeedbackRequest(
                interview.getRole(), interview.getInterviewType(), interview.getInterviewerMode(), qa
        ));

        FeedbackEntity entity = new FeedbackEntity();
        entity.setInterview(interview);
        entity.setOverallScore(fb.overallScore());
        entity.setCommunicationScore(fb.communicationScore());
        entity.setTechnicalScore(fb.technicalScore());
        entity.setConfidenceScore(fb.confidenceScore());
        entity.setStrengths(fb.strengths());
        entity.setWeaknesses(fb.weaknesses());
        entity.setSuggestions(fb.suggestions());
        feedbackRepository.save(entity);

        interview.setScore(fb.overallScore());
        interviewRepository.save(interview);

        InterviewDtos.InterviewFeedbackResponse dto = new InterviewDtos.InterviewFeedbackResponse(
                entity.getOverallScore(), entity.getCommunicationScore(), entity.getTechnicalScore(),
                entity.getConfidenceScore(), entity.getStrengths(), entity.getWeaknesses(), entity.getSuggestions()
        );

        realtime.publish(interviewId, "FEEDBACK_READY", dto);
        return new InterviewDtos.FinishInterviewResponse(dto);
    }

    @Transactional(readOnly = true)
    public InterviewDtos.InterviewHistoryPage history(int page, int size) {
        JwtService.AuthenticatedUser user = CurrentUser.require();
        Page<InterviewEntity> p = interviewRepository.findByUser_IdOrderByCreatedAtDesc(
                user.id(), PageRequest.of(Math.max(page, 0), Math.max(1, Math.min(size, 50)))
        );

        List<InterviewDtos.InterviewHistoryItem> items = p.getContent().stream()
                .map(i -> new InterviewDtos.InterviewHistoryItem(
                        i.getId(), i.getRole(), i.getInterviewType(), i.getInterviewerMode(), i.getScore(), i.getCreatedAt()
                ))
                .toList();

        return new InterviewDtos.InterviewHistoryPage(items, p.getNumber(), p.getSize(), p.getTotalElements(), p.getTotalPages());
    }

    private InterviewEntity getOwnedInterview(long interviewId, long userId) {
        InterviewEntity interview = interviewRepository.findById(interviewId)
                .orElseThrow(() -> new NotFoundException("Interview not found"));

        if (!Objects.equals(interview.getUser().getId(), userId)) {
            throw new NotFoundException("Interview not found");
        }

        return interview;
    }

    private QuestionEntity createQuestionFromAi(InterviewEntity interview, String previousQuestion, String previousAnswer) {
        AiDtos.GenerateQuestionResponse resp = aiClient.generateQuestion(new AiDtos.GenerateQuestionRequest(
                interview.getRole(), interview.getInterviewType(), interview.getInterviewerMode(), previousQuestion, previousAnswer
        ));

        QuestionEntity q = new QuestionEntity();
        q.setInterview(interview);
        q.setQuestionText(resp.questionText());
        return questionRepository.save(q);
    }

    private void recomputeInterviewScore(long interviewId) {
        InterviewEntity interview = interviewRepository.findById(interviewId).orElseThrow();
        List<QuestionEntity> questions = questionRepository.findByInterview_IdOrderByCreatedAtAsc(interviewId);

        List<BigDecimal> scores = new ArrayList<>();
        for (QuestionEntity q : questions) {
            answerRepository.findByQuestion_Id(q.getId())
                    .map(AnswerEntity::getAiScore)
                    .ifPresent(scores::add);
        }

        if (scores.isEmpty()) {
            return;
        }

        BigDecimal sum = scores.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal avg = sum.divide(BigDecimal.valueOf(scores.size()), 2, RoundingMode.HALF_UP);
        interview.setScore(avg);
        interviewRepository.save(interview);
    }
}
