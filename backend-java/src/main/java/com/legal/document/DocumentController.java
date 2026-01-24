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
    public ResponseEntity<Map<String, Object>> verifyDocument(@RequestBody Map<String, Object> payload) {
        String text = (String) payload.get("text");
        Map<String, Object> entities = (Map<String, Object>) payload.get("entities");

        Map<String, Object> response = new HashMap<>();
        response.put("originalText", text);

        // Strict Verification Logic
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
        // Accused might be optional in some complaints (e.g. unknown suspect), but
        // let's warn
        if (entities.get("accused") == null || entities.get("accused").toString().isEmpty())
            missingFields.put("accused", "Accused details missing (optional)");

        if (!missingFields.isEmpty()) {
            response.put("status", "INCOMPLETE");
            response.put("missingFields", missingFields);
        } else {
            response.put("status", "READY");
        }

        // High Risk Check
        if (text != null && (text.toLowerCase().contains("kill") || text.toLowerCase().contains("suicide"))) {
            response.put("alert", "HIGH_RISK_DETECTED");
            response.put("status", "BLOCKED");
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
