package com.aicoach.service;

import com.aicoach.domain.UserEntity;
import com.aicoach.repo.UserRepository;
import com.aicoach.security.JwtService;
import com.aicoach.web.dto.AuthDtos;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;

    public AuthService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            JwtService jwtService,
            AuthenticationManager authenticationManager
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.authenticationManager = authenticationManager;
    }

    @Transactional
    public AuthDtos.AuthResponse register(AuthDtos.RegisterRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new IllegalArgumentException("Email already registered");
        }

        UserEntity user = new UserEntity();
        user.setName(request.name());
        user.setEmail(request.email());
        user.setPasswordHash(passwordEncoder.encode(request.password()));
        user.setRole(request.role());
        user.setExperienceLevel(request.experienceLevel());

        userRepository.save(user);

        String token = jwtService.createAccessToken(user.getId(), user.getEmail(), user.getRole());
        return new AuthDtos.AuthResponse(token, toProfile(user));
    }

    public AuthDtos.AuthResponse login(AuthDtos.LoginRequest request) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.email(), request.password())
        );

        UserEntity user = userRepository.findByEmail(request.email())
                .orElseThrow(() -> new IllegalArgumentException("Invalid credentials"));

        String token = jwtService.createAccessToken(user.getId(), user.getEmail(), user.getRole());
        return new AuthDtos.AuthResponse(token, toProfile(user));
    }

    private static AuthDtos.UserProfile toProfile(UserEntity user) {
        return new AuthDtos.UserProfile(
                user.getId(),
                user.getName(),
                user.getEmail(),
                user.getRole(),
                user.getExperienceLevel()
        );
    }
}
