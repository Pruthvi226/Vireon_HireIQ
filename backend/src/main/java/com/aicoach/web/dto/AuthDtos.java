package com.aicoach.web.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class AuthDtos {
    public record RegisterRequest(
            @NotBlank @Size(max = 120) String name,
            @NotBlank @Email String email,
            @NotBlank @Size(min = 8, max = 100) String password,
            @NotBlank @Size(max = 100) String role,
            @NotBlank @Size(max = 50) String experienceLevel
    ) {
    }

    public record LoginRequest(
            @NotBlank @Email String email,
            @NotBlank String password
    ) {
    }

    public record AuthResponse(
            String accessToken,
            UserProfile user
    ) {
    }

    public record UserProfile(
            Long id,
            String name,
            String email,
            String role,
            String experienceLevel
    ) {
    }
}
