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
}
