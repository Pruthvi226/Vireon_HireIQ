package com.aicoach.web.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.time.Instant;

public class ResumeDtos {
    public record UploadResumeRequest(
            @NotBlank @Size(max = 500) String fileUrl,
            @NotBlank String fileBase64,
            @NotBlank String filename
    ) {
    }

    public record ResumeResponse(
            Long id,
            String fileUrl,
            String extractedTextPreview,
            Instant createdAt
    ) {
    }
}
