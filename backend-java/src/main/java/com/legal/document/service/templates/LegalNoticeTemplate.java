package com.legal.document.service.templates;

import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Font;
import com.lowagie.text.Element;
import java.util.Map;
import org.springframework.stereotype.Component;
import java.time.LocalDate;

@Component
public class LegalNoticeTemplate implements DocumentTemplate {

    @Override
    public boolean supports(String documentType) {
        return "Legal Notice".equalsIgnoreCase(documentType) || "Send Legal Notice".equalsIgnoreCase(documentType);
    }

    @Override
    public void buildDocument(Document document, Map<String, String> data) throws DocumentException {
        Font titleFont = new Font(Font.HELVETICA, 18, Font.BOLD | Font.UNDERLINE);
        Font boldFont = new Font(Font.HELVETICA, 12, Font.BOLD);
        Font normalFont = new Font(Font.HELVETICA, 12, Font.NORMAL);

        // Title
        Paragraph title = new Paragraph("LEGAL NOTICE", titleFont);
        title.setAlignment(Element.ALIGN_CENTER);
        document.add(title);
        document.add(new Paragraph("\n"));

        // Date
        document.add(new Paragraph("Date: " + LocalDate.now(), boldFont));
        document.add(new Paragraph("\n"));

        // To
        document.add(new Paragraph("TO,", boldFont));
        document.add(new Paragraph(data.getOrDefault("accused", "[Recipient Name]"), normalFont));
        document.add(new Paragraph(data.getOrDefault("location", "[Address]"), normalFont));
        document.add(new Paragraph("\n"));

        // Subject
        document.add(new Paragraph("SUB: NOTICE UNDER RELEVANT SECTIONS OF LAW FOR " +
                data.getOrDefault("issue_type", "ILLEGAL ACTS"), boldFont));
        document.add(new Paragraph("Ref: Incident dated " + data.getOrDefault("date", "Unknown"), normalFont));
        document.add(new Paragraph("\n"));

        // Body
        document.add(new Paragraph("Dear Sir/Madam,", normalFont));
        document.add(new Paragraph("\n"));

        String clientName = data.getOrDefault("name", "My Client");
        String body = "Under instruction from my client, " + clientName +
                ", residing at " + data.getOrDefault("location", "[Client Address]") +
                ", I hereby serve you with the following notice:";

        document.add(new Paragraph(body, normalFont));
        document.add(new Paragraph("\n"));

        document.add(new Paragraph("1. That on " + data.getOrDefault("date", "the stated date") +
                ", you " + (data.get("relationship") != null ? "(" + data.get("relationship") + ") " : "") +
                "committed acts causing grievance to my client.", normalFont));

        if (data.containsKey("amount")) {
            document.add(new Paragraph("2. That this matter involves an outstanding due/financial loss of " +
                    data.get("amount") + ".", normalFont));
        }

        document.add(new Paragraph("\n"));
        document.add(new Paragraph("I hereby call upon you to comply with my client's demands within 15 days, " +
                "failing which civil and criminal proceedings will be initiated against you.", boldFont));

        document.add(new Paragraph("\n\n"));
        document.add(new Paragraph("Yours Faithfully,", normalFont));
        document.add(new Paragraph("\n"));
        document.add(new Paragraph("____________________", normalFont));
        document.add(new Paragraph("Advocate for " + clientName, boldFont));
    }
}
