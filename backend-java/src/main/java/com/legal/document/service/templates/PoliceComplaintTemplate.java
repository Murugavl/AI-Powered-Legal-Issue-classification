package com.legal.document.service.templates;

import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import com.lowagie.text.Paragraph;
import com.lowagie.text.Font;
import com.lowagie.text.Element;
import org.springframework.stereotype.Component;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Map;

/**
 * Police Complaint / FIR Draft Template
 * Based on standard Indian Police Complaint format.
 * Applicable for: Theft, Cheating, Assault, Cybercrime, Harassment
 */
@Component
public class PoliceComplaintTemplate implements DocumentTemplate {

    @Override
    public boolean supports(String documentType) {
        String lower = documentType.toLowerCase();
        return lower.contains("police") || lower.contains("fir") || lower.contains("complaint")
                || lower.contains("theft") || lower.contains("assault") || lower.contains("cheating")
                || lower.contains("cybercrime") || lower.contains("robbery");
    }

    @Override
    public void buildDocument(Document document, Map<String, String> data) throws DocumentException {
        Font titleFont = new Font(Font.HELVETICA, 16, Font.BOLD | Font.UNDERLINE);
        Font boldFont = new Font(Font.HELVETICA, 12, Font.BOLD);
        Font normalFont = new Font(Font.HELVETICA, 11, Font.NORMAL);
        Font headerFont = new Font(Font.HELVETICA, 13, Font.BOLD);
        Font smallFont = new Font(Font.HELVETICA, 9, Font.ITALIC);

        String today = LocalDate.now().format(DateTimeFormatter.ofPattern("dd-MM-yyyy"));

        // ─── TITLE ───────────────────────────────────────────────────────────
        Paragraph title = new Paragraph("COMPLAINT TO THE STATION HOUSE OFFICER", titleFont);
        title.setAlignment(Element.ALIGN_CENTER);
        document.add(title);
        document.add(new Paragraph(" "));

        // ─── TO SECTION ──────────────────────────────────────────────────────
        document.add(new Paragraph("TO,", boldFont));
        document.add(new Paragraph("The Station House Officer", normalFont));
        document.add(new Paragraph(data.getOrDefault("fir_station",
                "[Police Station Name]") + " Police Station", normalFont));
        document.add(new Paragraph(
                data.getOrDefault("district", "[District]") + ", " +
                        data.getOrDefault("state", "[State]"),
                normalFont));
        document.add(new Paragraph(" "));

        // ─── DATE ────────────────────────────────────────────────────────────
        document.add(new Paragraph("Date: " + today, boldFont));
        document.add(new Paragraph(" "));

        // ─── SUBJECT ─────────────────────────────────────────────────────────
        String issueType = data.getOrDefault("issue_type", "a criminal offence");
        document.add(new Paragraph(
                "SUB: Complaint regarding " + issueType + " – Request for Registration of FIR", boldFont));
        document.add(new Paragraph(" "));

        // ─── SALUTATION ──────────────────────────────────────────────────────
        document.add(new Paragraph("Respected Sir/Madam,", normalFont));
        document.add(new Paragraph(" "));

        // ─── INTRODUCTION ────────────────────────────────────────────────────
        document.add(new Paragraph("1. Introduction", headerFont));
        String complainantName = data.getOrDefault("user_full_name", data.getOrDefault("name", "[Complainant Name]"));
        String complainantAddr = data.getOrDefault("user_address",
                data.getOrDefault("location", "[Complainant Address]"));
        String complainantPhone = data.getOrDefault("user_phone", "[Phone Number]");

        document.add(new Paragraph(
                "I, " + complainantName + ", residing at " + complainantAddr +
                        ", Phone: " + complainantPhone +
                        ", most respectfully submit this complaint and request you to take necessary legal action as detailed below:",
                normalFont));
        document.add(new Paragraph(" "));

        // ─── FACTS ───────────────────────────────────────────────────────────
        document.add(new Paragraph("2. Facts of the Case", headerFont));
        String incidentDate = data.getOrDefault("incident_date", "[Date of Incident]");
        String incidentLoc = data.getOrDefault("incident_location", data.getOrDefault("location", "[Location]"));
        String description = data.getOrDefault("incident_description",
                data.getOrDefault("description", "[Description of Incident]"));

        document.add(new Paragraph(
                "That on " + incidentDate + ", at " + incidentLoc + ", the following incident took place:",
                normalFont));
        document.add(new Paragraph(" "));
        document.add(new Paragraph(description, normalFont));
        document.add(new Paragraph(" "));

        // ─── ACCUSED DETAILS ─────────────────────────────────────────────────
        document.add(new Paragraph("3. Details of Accused / Respondent", headerFont));
        String accusedName = data.getOrDefault("counterparty_name",
                data.getOrDefault("accused", "[Name of Accused / Unknown]"));
        String accusedAddr = data.getOrDefault("counterparty_address", "[Address of Accused / Unknown]");
        String relationship = data.getOrDefault("counterparty_role", data.getOrDefault("relationship", "Unknown"));

        document.add(new Paragraph("Name: " + accusedName, normalFont));
        document.add(new Paragraph("Address: " + accusedAddr, normalFont));
        document.add(new Paragraph("Relationship to Complainant: " + relationship, normalFont));
        document.add(new Paragraph(" "));

        // ─── FINANCIAL LOSS ──────────────────────────────────────────────────
        String financialLoss = data.getOrDefault("financial_loss_value", null);
        String stolenItems = data.getOrDefault("stolen_items", null);
        if (financialLoss != null || stolenItems != null) {
            document.add(new Paragraph("4. Financial Loss / Stolen Property", headerFont));
            if (financialLoss != null)
                document.add(new Paragraph("Financial Loss / Value: ₹" + financialLoss, normalFont));
            if (stolenItems != null)
                document.add(new Paragraph("Items Stolen / Damaged: " + stolenItems, normalFont));
            document.add(new Paragraph(" "));
        }

        // ─── EVIDENCE ────────────────────────────────────────────────────────
        document.add(new Paragraph("5. Evidence Available", headerFont));
        String evidence = data.getOrDefault("evidence_available", "Evidence to be submitted separately");
        document.add(new Paragraph(evidence, normalFont));
        document.add(new Paragraph(" "));

        // ─── WITNESS ─────────────────────────────────────────────────────────
        String witness = data.getOrDefault("witness_details", null);
        if (witness != null && !witness.isEmpty() && !witness.equals("EXPLICITLY_DENIED")) {
            document.add(new Paragraph("6. Witness Details", headerFont));
            document.add(new Paragraph(witness, normalFont));
            document.add(new Paragraph(" "));
        }

        // ─── PRAYER ──────────────────────────────────────────────────────────
        document.add(new Paragraph("7. Prayer", headerFont));
        document.add(new Paragraph(
                "In view of the above facts, I most humbly request you to:", normalFont));
        document.add(new Paragraph(
                "a) Register my complaint as a First Information Report (FIR) under the relevant sections of IPC / BNSS.",
                normalFont));
        document.add(new Paragraph(
                "b) Investigate the matter thoroughly and take necessary action against the accused.", normalFont));
        document.add(new Paragraph(
                "c) Recover the stolen/damaged property and ensure justice.", normalFont));
        document.add(new Paragraph(
                "d) Provide me with a copy of the FIR receipt.", normalFont));
        document.add(new Paragraph(" "));

        // ─── DECLARATION ─────────────────────────────────────────────────────
        document.add(new Paragraph("8. Declaration", headerFont));
        document.add(new Paragraph(
                "I, " + complainantName + ", do hereby declare that the information furnished " +
                        "above is true and correct to the best of my knowledge and belief. " +
                        "I have not suppressed any material fact.",
                normalFont));
        document.add(new Paragraph(" "));

        // ─── SIGNATURE ───────────────────────────────────────────────────────
        document.add(new Paragraph("Yours faithfully,", normalFont));
        document.add(new Paragraph(" "));
        document.add(new Paragraph("____________________", normalFont));
        document.add(new Paragraph("Name:  " + complainantName, boldFont));
        document.add(new Paragraph("Phone: " + complainantPhone, normalFont));
        document.add(new Paragraph("Address: " + complainantAddr, normalFont));
        document.add(new Paragraph("Date:  " + today, normalFont));
        document.add(new Paragraph("Place: " +
                data.getOrDefault("district", "[Place]") + ", " +
                data.getOrDefault("state", "[State]"), normalFont));
        document.add(new Paragraph(" "));

        // ─── DISCLAIMER ──────────────────────────────────────────────────────
        document.add(new Paragraph(
                "DISCLAIMER: This document has been auto-generated by Satta Vizhi (AI Legal Assistant) " +
                        "based on user-provided information only. It does not constitute legal advice. " +
                        "Please review with a qualified legal professional before official submission.",
                smallFont));
    }
}
