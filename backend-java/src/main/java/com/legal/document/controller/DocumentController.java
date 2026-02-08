package com.legal.document.controller;

import com.legal.document.service.PdfGeneratorService;
import com.legal.document.service.BilingualPdfService;
import com.lowagie.text.DocumentException;
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

    @Autowired
    private BilingualPdfService bilingualPdfService;

    /**
     * Generate bilingual PDF (user language + English)
     * Expected payload:
     * {
     * "user_language_content": "...",
     * "english_content": "...",
     * "user_language": "ta",
     * "reference_number": "LDA-2026-000001",
     * "document_type": "police_complaint",
     * "metadata": {...}
     * }
     */
    @PostMapping("/generate-bilingual")
    public ResponseEntity<byte[]> generateBilingualPdf(@RequestBody Map<String, Object> payload) {
        try {
            String userLanguageContent = (String) payload.get("user_language_content");
            String englishContent = (String) payload.get("english_content");
            String userLanguage = (String) payload.getOrDefault("user_language", "en");
            String referenceNumber = (String) payload.get("reference_number");

            @SuppressWarnings("unchecked")
            Map<String, Object> metadata = (Map<String, Object>) payload.getOrDefault("metadata", new HashMap<>());

            // Add document type to metadata
            if (payload.containsKey("document_type")) {
                metadata.put("Document Type", payload.get("document_type"));
            }
            if (payload.containsKey("readiness_score")) {
                metadata.put("Readiness Score", payload.get("readiness_score") + "/100");
            }

            byte[] pdf = bilingualPdfService.generateBilingualPdf(
                    userLanguageContent,
                    englishContent,
                    userLanguage,
                    referenceNumber,
                    metadata);

            String filename = "legal_document_" +
                    (referenceNumber != null ? referenceNumber : "draft") + ".pdf";

            return ResponseEntity.ok()
                    .header("Content-Disposition", "attachment; filename=" + filename)
                    .contentType(org.springframework.http.MediaType.APPLICATION_PDF)
                    .body(pdf);

        } catch (DocumentException e) {
            e.printStackTrace();
            return ResponseEntity.internalServerError().build();
        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.badRequest().build();
        }
    }
}
