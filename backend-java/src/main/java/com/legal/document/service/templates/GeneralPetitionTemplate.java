package com.legal.document.service.templates;

import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Font;
import com.lowagie.text.Element;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class GeneralPetitionTemplate implements DocumentTemplate {

    @Override
    public boolean supports(String documentType) {
        // Fallback for generic types
        return "General Consultation".equalsIgnoreCase(documentType)
                || "File FIR / Complaint".equalsIgnoreCase(documentType);
    }

    @Override
    public void buildDocument(Document document, Map<String, String> data) throws DocumentException {
        Font titleFont = new Font(Font.HELVETICA, 18, Font.BOLD);
        Font normalFont = new Font(Font.HELVETICA, 12, Font.NORMAL);

        Paragraph title = new Paragraph("FORMAL COMPLAINT / PETITION", titleFont);
        title.setAlignment(Element.ALIGN_CENTER);
        document.add(title);

        document.add(new Paragraph("\n"));
        document.add(new Paragraph("To The Competent Authority,", new Font(Font.HELVETICA, 12, Font.BOLD)));
        document.add(new Paragraph("Subject: Generic Complaint regarding " + data.getOrDefault("issue_type", "Issue"),
                normalFont));
        document.add(new Paragraph("\n"));

        document.add(new Paragraph("Respected Sir/Madam,", normalFont));
        document.add(new Paragraph(
                "I, " + data.getOrDefault("name", "The Undersigned") + ", wish to report an incident.", normalFont));
        document.add(new Paragraph("\n"));
        document.add(new Paragraph("Incident Details: " + data.getOrDefault("description", ""), normalFont));
        document.add(new Paragraph("\n"));
        document.add(new Paragraph("Detailed Facts:", new Font(Font.HELVETICA, 12, Font.BOLD)));

        data.forEach((k, v) -> {
            if (!k.equals("description") && v != null) {
                document.add(new Paragraph(k + ": " + v, normalFont));
            }
        });

        document.add(new Paragraph("\n\nPlease take appropriate action.", normalFont));
        document.add(new Paragraph("\n\nSignature", normalFont));
    }
}
