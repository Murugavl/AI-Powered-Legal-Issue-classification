package com.legal.document.service;

import com.legal.document.dto.AuthResponse;
import com.legal.document.dto.LoginRequest;
import com.legal.document.dto.RegisterRequest;
import com.legal.document.entity.User;
import com.legal.document.repository.UserRepository;
import com.legal.document.util.JwtUtil;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtUtil jwtUtil;

    public AuthResponse register(RegisterRequest request) {
        // Check if user already exists
        if (userRepository.existsByPhoneNumber(request.getPhoneNumber())) {
            throw new RuntimeException("Phone number already registered");
        }

        if (request.getEmail() != null && userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("Email already registered");
        }

        // Create new user
        User user = new User();
        user.setPhoneNumber(request.getPhoneNumber());
        user.setEmail(request.getEmail());
        user.setFullName(request.getFullName());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setPreferredLanguage(request.getPreferredLanguage() != null ? request.getPreferredLanguage() : "en");
        user.setIsActive(true);

        User savedUser = userRepository.save(user);

        // Generate JWT token
        String token = jwtUtil.generateToken(savedUser.getPhoneNumber());

        return new AuthResponse(
                token,
                savedUser.getPhoneNumber(),
                savedUser.getFullName(),
                savedUser.getPreferredLanguage());
    }

    public AuthResponse login(LoginRequest request) {
        // Find user by phone number
        User user = userRepository.findByPhoneNumber(request.getPhoneNumber())
                .orElseThrow(() -> new RuntimeException("Invalid credentials"));

        // Verify password
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new RuntimeException("Invalid credentials");
        }

        // Check if user is active
        if (!user.getIsActive()) {
            throw new RuntimeException("Account is inactive");
        }

        // Generate JWT token
        String token = jwtUtil.generateToken(user.getPhoneNumber());

        return new AuthResponse(
                token,
                user.getPhoneNumber(),
                user.getFullName(),
                user.getPreferredLanguage());
    }
}
