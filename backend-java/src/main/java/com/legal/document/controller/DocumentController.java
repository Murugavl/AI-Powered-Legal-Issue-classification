package com.legal.document.controller;

import com.legal.document.service.PdfGeneratorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Map;
import java.util.HashMap;

@RestController
@RequestMapping("/api/documents")
@CrossOrigin(origins = "*")
public class DocumentController {

    @Autowired
    private PdfGeneratorService pdfGeneratorService;

    @PostMapping("/verify")
    public ResponseEntity<Map<String, Object>> verifyDocument(@RequestBody Map<String, Object> payload) {
        String text = (String) payload.get("text");
        Map<String, Object> entities = (Map<String, Object>) payload.get("entities");

        Map<String, Object> response = new HashMap<>();
        response.put("originalText", text);

        Map<String, String> missingFields = new HashMap<>();
        if (entities == null) {
            response.put("status", "FAILED");
            response.put("error", "No entities provided");
            return ResponseEntity.ok(response);
        }

        if (entities.get("name") == null || entities.get("name").toString().isEmpty())
            missingFields.put("name", "Name is required");
        if (entities.get("date") == null || entities.get("date").toString().isEmpty())
            missingFields.put("date", "Incident Date is required");
        if (entities.get("location") == null || entities.get("location").toString().isEmpty())
            missingFields.put("location", "Location is required");

        if (!missingFields.isEmpty()) {
            response.put("status", "INCOMPLETE");
            response.put("missingFields", missingFields);
        } else {
            response.put("status", "READY");
        }

        if (text != null && (text.toLowerCase().contains("kill") || text.toLowerCase().contains("suicide"))) {
            response.put("alert", "HIGH_RISK_DETECTED");
            response.put("status", "BLOCKED");
        }

        return ResponseEntity.ok(response);
    }

    @PostMapping("/generate")
    public ResponseEntity<byte[]> generatePdf(@RequestBody Map<String, String> data) {
        // "issue_type" or "documentType" key from frontend determines the template
        String documentType = data.getOrDefault("issue_type", "General Consultation");

        // Pass the entire data map to the service (contains entities like name, date,
        // location)
        byte[] pdf = pdfGeneratorService.generatePdf(documentType, data);

        if (pdf == null) {
            return ResponseEntity.internalServerError().build();
        }

        return ResponseEntity.ok()
                .header("Content-Disposition", "attachment; filename=legal_document.pdf")
                .contentType(org.springframework.http.MediaType.APPLICATION_PDF)
                .body(pdf);
    }
}
