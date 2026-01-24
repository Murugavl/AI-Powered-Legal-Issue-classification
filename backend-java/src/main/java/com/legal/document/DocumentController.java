package com.legal.document;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;
import java.util.HashMap;

@RestController
@RequestMapping("/api/documents")
@CrossOrigin(origins = "*")
public class DocumentController {

    @PostMapping("/verify")
    public ResponseEntity<Map<String, Object>> verifyDocument(@RequestBody DocumentRequest request) {
        // Mocking the call to NLP service for now, or we can use RestTemplate to call
        // localhost:8000
        // For prototype, we'll assume we receive the text and mock the extraction if
        // the Python service isn't reachable yet
        // In full integration, verifyDocument implies calling Python to get entities.

        // Let's stub the response assuming we will integrate with Python later
        Map<String, Object> response = new HashMap<>();
        response.put("status", "pending_verification");
        response.put("originalText", request.getText());

        // Check for high-risk keywords (redundant buffer, usually done in frontend or
        // NLP)
        if (request.getText() != null && (request.getText().toLowerCase().contains("kill")
                || request.getText().toLowerCase().contains("suicide"))) {
            response.put("alert", "HIGH_RISK_DETECTED");
        }

        return ResponseEntity.ok(response);
    }

    @org.springframework.beans.factory.annotation.Autowired
    private PdfGeneratorService pdfGeneratorService;

    @PostMapping("/generate")
    public ResponseEntity<byte[]> generatePdf(@RequestBody Map<String, String> data) {
        String englishText = data.getOrDefault("englishText", "");
        String localText = data.getOrDefault("localText", "");

        byte[] pdf = pdfGeneratorService.generateBilingualPdf(englishText, localText);

        if (pdf == null) {
            return ResponseEntity.internalServerError().build();
        }

        return ResponseEntity.ok()
                .header("Content-Disposition", "attachment; filename=document.pdf")
                .contentType(org.springframework.http.MediaType.APPLICATION_PDF)
                .body(pdf);
    }
}
