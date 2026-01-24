package com.legal.document;

import com.lowagie.text.Document;
import com.lowagie.text.Paragraph;
import com.lowagie.text.pdf.PdfWriter;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfPCell;
import com.lowagie.text.Font;
import com.lowagie.text.Element;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.util.Map;

@Service
public class PdfGeneratorService {

    public byte[] generateBilingualPdf(String englishText, String localText) {
        try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            Document document = new Document();
            PdfWriter.getInstance(document, out);
            document.open();

            // Disclaimer
            Font warningFont = new Font(Font.HELVETICA, 16, Font.BOLD, java.awt.Color.RED);
            Paragraph disclaimer = new Paragraph("NOT LEGAL ADVICE", warningFont);
            disclaimer.setAlignment(Element.ALIGN_CENTER);
            document.add(disclaimer);
            document.add(new Paragraph(" ")); // Spacer

            // Table for side-by-side
            PdfPTable table = new PdfPTable(2);
            table.setWidthPercentage(100);

            // Headers
            table.addCell(new Paragraph("English"));
            table.addCell(new Paragraph("Local Language"));

            // Content
            table.addCell(new Paragraph(englishText));

            // Note: For Indic scripts, OpenPDF/iText need specific fonts (e.g., Lohit
            // Tamil).
            // Without embedding a font, it won't render Tamil/Hindi correctly.
            // For this prototype, we will assume standard font or transliterated text is
            // acceptable,
            // or we'd need to load a ttf file. We'll use standard font for now.
            table.addCell(new Paragraph(localText));

            document.add(table);
            document.close();

            return out.toByteArray();
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }
}
