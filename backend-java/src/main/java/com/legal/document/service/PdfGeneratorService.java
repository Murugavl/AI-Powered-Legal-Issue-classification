package com.legal.document.service;

import com.legal.document.service.templates.DocumentTemplate;
import com.lowagie.text.Document;
import com.lowagie.text.pdf.PdfWriter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.util.List;
import java.util.Map;

@Service
public class PdfGeneratorService {

    @Autowired
    private List<DocumentTemplate> templates;

    public byte[] generatePdf(String templateType, Map<String, String> data) {
        try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            Document document = new Document();
            PdfWriter.getInstance(document, out);
            document.open();

            // Find matching template
            DocumentTemplate selectedTemplate = templates.stream()
                    .filter(t -> t.supports(templateType))
                    .findFirst()
                    .orElse(templates.stream()
                            .filter(t -> t.supports("General Consultation"))
                            .findFirst()
                            .orElse(null));

            if (selectedTemplate != null) {
                selectedTemplate.buildDocument(document, data);
            } else {
                // Formatting Fallback
                document.add(new com.lowagie.text.Paragraph("No template found for: " + templateType));
            }

            document.close();
            return out.toByteArray();
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }
}
