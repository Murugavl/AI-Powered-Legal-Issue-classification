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

import java.util.List;

@RestController
@RequestMapping("/api/session")
@CrossOrigin(origins = "*")
public class SessionController {

    @Autowired private SessionService sessionService;
    @Autowired private JwtUtil        jwtUtil;

    /** Start a new session with the user's initial problem description */
    @PostMapping("/start")
    public ResponseEntity<SessionResponse> startSession(
            @RequestHeader("Authorization") String token,
            @RequestBody StartSessionRequest request) {
        return ResponseEntity.ok(sessionService.startSession(request, phoneFrom(token)));
    }

    /** Submit a text answer / reply during an active session */
    @PostMapping("/{sessionId}/answer")
    public ResponseEntity<SessionResponse> submitAnswer(
            @RequestHeader("Authorization") String token,
            @PathVariable String sessionId,
            @RequestBody SubmitAnswerRequest request) {
        return ResponseEntity.ok(sessionService.submitAnswer(sessionId, request, phoneFrom(token)));
    }

    /** Submit a voice transcript (audio file stored, transcript processed as text) */
    @PostMapping("/{sessionId}/answer-voice")
    public ResponseEntity<SessionResponse> submitVoiceAnswer(
            @RequestHeader("Authorization") String token,
            @PathVariable String sessionId,
            @RequestParam(value = "audio",      required = false) MultipartFile audioFile,
            @RequestParam(value = "transcript", required = false) String transcript,
            @RequestParam(value = "language",   defaultValue = "en") String language,
            @RequestParam(value = "transcriptConfirmed", defaultValue = "false") boolean transcriptConfirmed) {
        return ResponseEntity.ok(
                sessionService.submitVoiceAnswer(
                        sessionId, audioFile, transcript, language, transcriptConfirmed, phoneFrom(token)));
    }

    /** Upload an evidence file — the filename is forwarded to the NLP engine as context */
    @PostMapping("/{sessionId}/evidence")
    public ResponseEntity<SessionResponse> uploadEvidence(
            @RequestHeader("Authorization") String token,
            @PathVariable String sessionId,
            @RequestParam("file") MultipartFile file) {
        return ResponseEntity.ok(sessionService.uploadEvidence(sessionId, file, phoneFrom(token)));
    }

    /** Get current session status (intent, readiness score, status) */
    @GetMapping("/{sessionId}")
    public ResponseEntity<SessionResponse> getSessionStatus(
            @RequestHeader("Authorization") String token,
            @PathVariable String sessionId) {
        return ResponseEntity.ok(sessionService.getSessionStatus(sessionId, phoneFrom(token)));
    }

    /** List all sessions for the authenticated user */
    @GetMapping
    public ResponseEntity<List<SessionResponse>> getUserSessions(
            @RequestHeader("Authorization") String token) {
        return ResponseEntity.ok(sessionService.getUserSessions(phoneFrom(token)));
    }

    /** Delete a session and all its associated data */
    @DeleteMapping("/{sessionId}")
    public ResponseEntity<Void> deleteSession(
            @RequestHeader("Authorization") String token,
            @PathVariable String sessionId) {
        sessionService.deleteSession(sessionId, phoneFrom(token));
        return ResponseEntity.ok().build();
    }

    // ---- helper ----
    private String phoneFrom(String token) {
        if (token != null && token.startsWith("Bearer ")) token = token.substring(7);
        return jwtUtil.getPhoneNumberFromToken(token);
    }
}
