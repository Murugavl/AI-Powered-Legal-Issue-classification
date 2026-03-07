package com.legal.document.controller;

import com.legal.document.service.BilingualPdfService;
import com.lowagie.text.DocumentException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/documents")
@CrossOrigin(origins = "*")
public class DocumentController {

    @Autowired
    private BilingualPdfService bilingualPdfService;

    /**
     * Generate a bilingual PDF from the document payload produced by the Python NLP engine.
     *
     * Expected JSON body — mirrors exactly what Python puts in documentPayload:
     * {
     *   "user_language_content" : "...",
     *   "english_content"       : "...",
     *   "user_language"         : "ta",
     *   "document_type"         : "cyber_fraud_complaint",
     *   "readiness_score"       : 75,
     *   "disclaimer_en"         : "...",
     *   "disclaimer_user_lang"  : "..."
     * }
     */
    @PostMapping("/generate-bilingual")
    public ResponseEntity<byte[]> generateBilingualPdf(@RequestBody Map<String, Object> payload) {
        try {
            String userLanguageContent = (String) payload.getOrDefault("user_language_content", "");
            String englishContent      = (String) payload.getOrDefault("english_content", "");
            String userLanguage        = (String) payload.getOrDefault("user_language", "en");
            String documentType        = (String) payload.getOrDefault("document_type", "general_petition");
            String disclaimerEn        = (String) payload.getOrDefault("disclaimer_en", "");
            String disclaimerUserLang  = (String) payload.getOrDefault("disclaimer_user_lang", disclaimerEn);

            Map<String, Object> metadata = new HashMap<>();
            metadata.put("Document Type", documentType.replace("_", " ").toUpperCase());
            if (payload.containsKey("readiness_score")) {
                metadata.put("Evidence Readiness Score", payload.get("readiness_score") + " / 100");
            }

            byte[] pdf = bilingualPdfService.generateBilingualPdf(
                    userLanguageContent,
                    englishContent,
                    userLanguage,
                    disclaimerEn,
                    disclaimerUserLang,
                    metadata);

            String filename = "SattaVizhi_" + documentType + ".pdf";
            return ResponseEntity.ok()
                    .header("Content-Disposition", "attachment; filename=\"" + filename + "\"")
                    .contentType(MediaType.APPLICATION_PDF)
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
