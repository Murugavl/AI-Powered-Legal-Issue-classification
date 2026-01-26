package com.legal.document.controller;

import com.legal.document.dto.SessionResponse;
import com.legal.document.dto.StartSessionRequest;
import com.legal.document.dto.SubmitAnswerRequest;
import com.legal.document.service.SessionService;
import com.legal.document.util.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/session")
public class SessionController {

    @Autowired
    private SessionService sessionService;

    @Autowired
    private JwtUtil jwtUtil;

    @PostMapping("/start")
    public ResponseEntity<SessionResponse> startSession(
            @RequestHeader("Authorization") String token,
            @RequestBody StartSessionRequest request) {

        String phoneNumber = getPhoneNumberFromToken(token);
        return ResponseEntity.ok(sessionService.startSession(request, phoneNumber));
    }

    @PostMapping("/{sessionId}/answer")
    public ResponseEntity<SessionResponse> submitAnswer(
            @PathVariable String sessionId,
            @RequestBody SubmitAnswerRequest request,
            @RequestParam String phoneNumber) {
        return ResponseEntity.ok(sessionService.submitAnswer(sessionId, request, phoneNumber));
    }

    @PostMapping("/{sessionId}/answer-voice")
    public ResponseEntity<SessionResponse> submitVoiceAnswer(
            @PathVariable String sessionId,
            @RequestParam("audio") MultipartFile audioFile,
            @RequestParam(value = "transcript", required = false) String transcript,
            @RequestParam(value = "language", defaultValue = "en") String language,
            @RequestParam String phoneNumber) {
        return ResponseEntity
                .ok(sessionService.submitVoiceAnswer(sessionId, audioFile, transcript, language, phoneNumber));
    }

    @PostMapping("/{sessionId}/evidence")
    public ResponseEntity<SessionResponse> uploadEvidence(
            @PathVariable String sessionId,
            @RequestParam("file") MultipartFile file,
            @RequestParam String phoneNumber) {
        return ResponseEntity.ok(sessionService.uploadEvidence(sessionId, file, phoneNumber));
    }

    @DeleteMapping("/{sessionId}")
    public ResponseEntity<Void> deleteSession(
            @PathVariable String sessionId,
            @RequestParam String phoneNumber) {
        sessionService.deleteSession(sessionId, phoneNumber);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{sessionId}")
    public ResponseEntity<SessionResponse> getSessionStatus(
            @RequestHeader("Authorization") String token,
            @PathVariable String sessionId) {

        String phoneNumber = getPhoneNumberFromToken(token);
        return ResponseEntity.ok(sessionService.getSessionStatus(sessionId, phoneNumber));
    }

    private String getPhoneNumberFromToken(String token) {
        if (token != null && token.startsWith("Bearer ")) {
            token = token.substring(7);
        }
        return jwtUtil.getPhoneNumberFromToken(token);
    }
}
