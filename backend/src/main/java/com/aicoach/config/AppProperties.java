package com.aicoach.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app")
public record AppProperties(
        JwtProperties jwt,
        CorsProperties cors,
        AiServiceProperties aiService
) {
    public record JwtProperties(String issuer, String secret, long accessTokenTtlSeconds) {
    }

    public record CorsProperties(String allowedOrigins) {
    }

    public record AiServiceProperties(String baseUrl) {
    }
}
