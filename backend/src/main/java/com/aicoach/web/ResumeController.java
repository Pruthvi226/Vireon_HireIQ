package com.aicoach.web;

import com.aicoach.ai.AiClient;
import com.aicoach.ai.AiDtos;
import com.aicoach.domain.ResumeEntity;
import com.aicoach.domain.UserEntity;
import com.aicoach.repo.ResumeRepository;
import com.aicoach.repo.UserRepository;
import com.aicoach.security.CurrentUser;
import com.aicoach.web.dto.ResumeDtos;
import jakarta.validation.Valid;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/user")
public class ResumeController {
    private final ResumeRepository resumeRepository;
    private final UserRepository userRepository;
    private final AiClient aiClient;

    public ResumeController(ResumeRepository resumeRepository, UserRepository userRepository, AiClient aiClient) {
        this.resumeRepository = resumeRepository;
        this.userRepository = userRepository;
        this.aiClient = aiClient;
    }

    @PostMapping("/resumes")
    public ResumeDtos.ResumeResponse upload(@Valid @RequestBody ResumeDtos.UploadResumeRequest request) {
        var auth = CurrentUser.require();
        UserEntity user = userRepository.findById(auth.id()).orElseThrow();

        AiDtos.ResumeAnalysisResponse analyzed = aiClient.resumeAnalysis(new AiDtos.ResumeAnalysisRequest(
                request.filename(),
                request.fileBase64()
        ));

        ResumeEntity resume = new ResumeEntity();
        resume.setUser(user);
        resume.setFileUrl(request.fileUrl());
        resume.setExtractedText(analyzed.extractedText());
        resume = resumeRepository.save(resume);

        String preview = analyzed.extractedText() == null ? "" : analyzed.extractedText().substring(0, Math.min(300, analyzed.extractedText().length()));
        return new ResumeDtos.ResumeResponse(resume.getId(), resume.getFileUrl(), preview, resume.getCreatedAt());
    }

    @GetMapping("/resumes")
    public List<ResumeDtos.ResumeResponse> list() {
        var auth = CurrentUser.require();
        var page = resumeRepository.findByUser_IdOrderByCreatedAtDesc(auth.id(), PageRequest.of(0, 20));

        return page.getContent().stream().map(r -> {
            String text = r.getExtractedText() == null ? "" : r.getExtractedText();
            String preview = text.substring(0, Math.min(300, text.length()));
            return new ResumeDtos.ResumeResponse(r.getId(), r.getFileUrl(), preview, r.getCreatedAt());
        }).toList();
    }
}
