package com.legal.document.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.*;

import java.util.HashMap;
import java.util.Map;

@Service
public class LegalServiceAgent {

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${legal.python-service-url:http://localhost:8000/process}")
    private String pythonServiceUrl;

    @SuppressWarnings("unchecked")
    public Map<String, Object> processUserMessage(String threadId, String input) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, String> body = new HashMap<>();
            body.put("thread_id", threadId);
            body.put("message",   input);

            ResponseEntity<Map> response = restTemplate.postForEntity(
                    pythonServiceUrl,
                    new HttpEntity<>(body, headers),
                    Map.class);

            if (response.getBody() != null && response.getBody().containsKey("result")) {
                return (Map<String, Object>) response.getBody().get("result");
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

        // Fallback — return a safe error message so the frontend never gets a blank response
        Map<String, Object> error = new HashMap<>();
        error.put("content",        "I'm having trouble connecting to the AI engine. Please try again in a moment.");
        error.put("is_document",    false);
        error.put("is_confirmation",false);
        error.put("readiness_score",0);
        error.put("intent",         "");
        error.put("entities",       new HashMap<>());
        return error;
    }
}

