package com.legal.document.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import java.util.Map;
import java.util.HashMap;

@Service
public class LegalServiceAgent {

    private final RestTemplate restTemplate = new RestTemplate();
    private final String pythonServiceUrl = "http://localhost:8000/process";

    @SuppressWarnings("unchecked")
    public Map<String, Object> processUserMessage(String threadId, String input) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, String> requestBody = new HashMap<>();
            requestBody.put("thread_id", threadId);
            requestBody.put("message", input);

            HttpEntity<Map<String, String>> request = new HttpEntity<>(requestBody, headers);

            ResponseEntity<Map> response = restTemplate.postForEntity(pythonServiceUrl, request, Map.class);

            if (response.getBody() != null && response.getBody().containsKey("result")) {
                return (Map<String, Object>) response.getBody().get("result");
            }
            Map<String, Object> error = new HashMap<>();
            error.put("content", "Error: Empty response from AI service.");
            return error;

        } catch (Exception e) {
            e.printStackTrace();
            Map<String, Object> error = new HashMap<>();
            error.put("content", "Error connecting to AI service: " + e.getMessage());
            return error;
        }
    }
}
