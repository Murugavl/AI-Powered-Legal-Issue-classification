package com.legal.document.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Map<String, Object>> handleRuntimeException(RuntimeException ex) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now().toString());
        body.put("error",     ex.getMessage());

        HttpStatus status = HttpStatus.INTERNAL_SERVER_ERROR;
        String msg = ex.getMessage() != null ? ex.getMessage().toLowerCase() : "";
        if (msg.contains("not found"))       status = HttpStatus.NOT_FOUND;
        if (msg.contains("unauthorized"))    status = HttpStatus.FORBIDDEN;
        if (msg.contains("invalid credentials") || msg.contains("inactive")) status = HttpStatus.UNAUTHORIZED;
        if (msg.contains("already registered")) status = HttpStatus.CONFLICT;

        body.put("status", status.value());
        return ResponseEntity.status(status).body(body);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGenericException(Exception ex) {
        ex.printStackTrace();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", LocalDateTime.now().toString());
        body.put("status",    500);
        body.put("error",     "An unexpected error occurred. Please try again.");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(body);
    }
}
