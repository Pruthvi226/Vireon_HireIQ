package com.aicoach.web.dto;

import java.math.BigDecimal;
import java.util.List;

public class DashboardDtos {
    public record ProgressResponse(
            BigDecimal rollingAverageScore,
            List<TrendPoint> trend
    ) {
    }

    public record TrendPoint(
            long interviewId,
            BigDecimal score
    ) {
    }
}
