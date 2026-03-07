package com.legal.document.controller;

import com.legal.document.dto.AuthResponse;
import com.legal.document.dto.LoginRequest;
import com.legal.document.dto.RegisterRequest;
import com.legal.document.service.AuthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
@CrossOrigin(origins = "*")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/register")
    public ResponseEntity<java.util.Map<String, String>> register(@RequestBody RegisterRequest request) {
        AuthResponse response = authService.register(request);
        java.util.Map<String, String> map = new java.util.HashMap<>();
        map.put("token", response.getToken());
        map.put("phoneNumber", response.getPhoneNumber());
        map.put("fullName", response.getFullName());
        map.put("preferredLanguage", response.getPreferredLanguage());
        return ResponseEntity.ok(map);
    }

    @PostMapping("/login")
    public ResponseEntity<java.util.Map<String, String>> login(@RequestBody LoginRequest request) {
        AuthResponse response = authService.login(request);
        java.util.Map<String, String> map = new java.util.HashMap<>();
        map.put("token", response.getToken());
        map.put("phoneNumber", response.getPhoneNumber());
        map.put("fullName", response.getFullName());
        map.put("preferredLanguage", response.getPreferredLanguage());
        return ResponseEntity.ok(map);
    }

    @PostMapping("/forgot-password")
    public ResponseEntity<java.util.Map<String, String>> forgotPassword(
            @RequestBody java.util.Map<String, String> request) {
        String phoneNumber = request.get("phoneNumber");
        try {
            String otp = authService.generateAndSendOtp(phoneNumber);
            java.util.Map<String, String> response = new java.util.HashMap<>();
            // Returning the OTP in response to make it work out of the box for testing
            // purposes
            // In a real application, this should not be returned, only sent via SMS
            response.put("message", "OTP sent successfully to " + phoneNumber);
            response.put("otp", otp);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            java.util.Map<String, String> response = new java.util.HashMap<>();
            response.put("message", e.getMessage());
            return ResponseEntity.status(400).body(response);
        }
    }

    @PostMapping("/verify-otp")
    public ResponseEntity<java.util.Map<String, String>> verifyOtp(@RequestBody java.util.Map<String, String> request) {
        String phoneNumber = request.get("phoneNumber");
        String otp = request.get("otp");
        boolean isValid = authService.verifyOtp(phoneNumber, otp);

        java.util.Map<String, String> response = new java.util.HashMap<>();
        if (isValid) {
            response.put("message", "OTP verified successfully");
            return ResponseEntity.ok(response);
        } else {
            response.put("message", "Invalid OTP");
            return ResponseEntity.status(400).body(response);
        }
    }

    @PostMapping("/reset-password")
    public ResponseEntity<java.util.Map<String, String>> resetPassword(
            @RequestBody java.util.Map<String, String> request) {
        String phoneNumber = request.get("phoneNumber");
        String otp = request.get("otp");
        String newPassword = request.get("newPassword");

        try {
            authService.resetPassword(phoneNumber, otp, newPassword);
            java.util.Map<String, String> response = new java.util.HashMap<>();
            response.put("message", "Password reset successfully");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            java.util.Map<String, String> response = new java.util.HashMap<>();
            response.put("message", e.getMessage());
            return ResponseEntity.status(400).body(response);
        }
    }
}
