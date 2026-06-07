package com.aicoach.web;

import com.aicoach.repo.InterviewRepository;
import com.aicoach.security.CurrentUser;
import com.aicoach.web.dto.DashboardDtos;
import com.aicoach.web.dto.InterviewDtos;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

@RestController
@RequestMapping("/api/user")
public class DashboardController {
    private final InterviewRepository interviewRepository;

    public DashboardController(InterviewRepository interviewRepository) {
        this.interviewRepository = interviewRepository;
    }

    @GetMapping("/interviews")
    public InterviewDtos.InterviewHistoryPage interviews(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size
    ) {
        var auth = CurrentUser.require();
        var p = interviewRepository.findByUser_IdOrderByCreatedAtDesc(
                auth.id(),
                PageRequest.of(Math.max(0, page), Math.max(1, Math.min(50, size)))
        );

        var content = p.getContent().stream()
                .map(i -> new InterviewDtos.InterviewHistoryItem(
                        i.getId(), i.getRole(), i.getInterviewType(), i.getInterviewerMode(), i.getScore(), i.getCreatedAt()
                ))
                .toList();

        return new InterviewDtos.InterviewHistoryPage(content, p.getNumber(), p.getSize(), p.getTotalElements(), p.getTotalPages());
    }

    @GetMapping("/progress")
    public DashboardDtos.ProgressResponse progress() {
        var auth = CurrentUser.require();
        var rows = interviewRepository.findByUser_IdOrderByCreatedAtDesc(auth.id(), PageRequest.of(0, 50)).getContent();

        List<DashboardDtos.TrendPoint> trend = rows.stream()
                .filter(i -> i.getScore() != null)
                .map(i -> new DashboardDtos.TrendPoint(i.getId(), i.getScore()))
                .toList();

        BigDecimal avg = BigDecimal.ZERO;
        if (!trend.isEmpty()) {
            BigDecimal sum = trend.stream().map(DashboardDtos.TrendPoint::score).reduce(BigDecimal.ZERO, BigDecimal::add);
            avg = sum.divide(BigDecimal.valueOf(trend.size()), 2, RoundingMode.HALF_UP);
        }

        return new DashboardDtos.ProgressResponse(avg, trend);
    }
}
