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
 * Consumer Complaint Template
 * Based on Consumer Protection Act, 2019.
 * For filing before District Consumer Disputes Redressal Commission (CDRC).
 */
@Component
public class ConsumerComplaintTemplate implements DocumentTemplate {

    @Override
    public boolean supports(String documentType) {
        String lower = documentType.toLowerCase();
        return lower.contains("consumer") || lower.contains("cdrc") || lower.contains("refund")
                || lower.contains("product") || lower.contains("defective") || lower.contains("service deficiency");
    }

    @Override
    public void buildDocument(Document document, Map<String, String> data) throws DocumentException {
        Font titleFont = new Font(Font.HELVETICA, 15, Font.BOLD | Font.UNDERLINE);
        Font boldFont = new Font(Font.HELVETICA, 12, Font.BOLD);
        Font headerFont = new Font(Font.HELVETICA, 12, Font.BOLD);
        Font normalFont = new Font(Font.HELVETICA, 11, Font.NORMAL);
        Font smallFont = new Font(Font.HELVETICA, 9, Font.ITALIC);

        String today = LocalDate.now().format(DateTimeFormatter.ofPattern("dd-MM-yyyy"));

        // ─── TITLE ───────────────────────────────────────────────────────────
        Paragraph title = new Paragraph(
                "COMPLAINT BEFORE THE DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION", titleFont);
        title.setAlignment(Element.ALIGN_CENTER);
        document.add(title);
        document.add(new Paragraph("(Under Consumer Protection Act, 2019 – Section 35)", boldFont));
        document.add(new Paragraph(" "));

        // ─── COMMISSION ──────────────────────────────────────────────────────
        document.add(new Paragraph(
                "Before the District Consumer Disputes Redressal Commission, " +
                        data.getOrDefault("district", "[District]") + ", " +
                        data.getOrDefault("state", "[State]"),
                boldFont));
        document.add(new Paragraph(" "));

        // ─── COMPLAINANT ─────────────────────────────────────────────────────
        document.add(new Paragraph("COMPLAINANT:", headerFont));
        String complainantName = data.getOrDefault("user_full_name", data.getOrDefault("name", "[Complainant Name]"));
        String complainantAddr = data.getOrDefault("user_address",
                data.getOrDefault("location", "[Complainant Address]"));
        String complainantPhone = data.getOrDefault("user_phone", "[Phone Number]");

        document.add(new Paragraph(complainantName + ",", normalFont));
        document.add(new Paragraph("Residing at: " + complainantAddr, normalFont));
        document.add(new Paragraph("Phone: " + complainantPhone, normalFont));
        document.add(
                new Paragraph("                                                         ... Complainant", boldFont));
        document.add(new Paragraph(" "));
        document.add(new Paragraph("VERSUS", boldFont));
        document.add(new Paragraph(" "));

        // ─── OPPOSITE PARTY ──────────────────────────────────────────────────
        document.add(new Paragraph("OPPOSITE PARTY (Seller / Service Provider):", headerFont));
        String opParty = data.getOrDefault("counterparty_name",
                data.getOrDefault("accused", "[Company / Seller Name]"));
        String opAddr = data.getOrDefault("counterparty_address", "[Company Address]");
        String opRole = data.getOrDefault("counterparty_role", "Seller / Service Provider");

        document.add(new Paragraph(opParty, normalFont));
        document.add(new Paragraph("Address: " + opAddr, normalFont));
        document.add(new Paragraph("Role: " + opRole, normalFont));
        document.add(
                new Paragraph("                                                         ... Opposite Party", boldFont));
        document.add(new Paragraph(" "));

        // ─── SUBJECT ─────────────────────────────────────────────────────────
        String productName = data.getOrDefault("product_name", "[Product / Service Name]");
        document.add(new Paragraph(
                "COMPLAINT FOR: Deficiency in goods/service, Unfair trade practice, and/or Compensation", boldFont));
        document.add(new Paragraph("REGARDING: " + productName, boldFont));
        document.add(new Paragraph(" "));

        // ─── FACTS ───────────────────────────────────────────────────────────
        document.add(new Paragraph("I. BRIEF FACTS OF THE COMPLAINT", headerFont));
        document.add(new Paragraph(" "));

        String incidentDate = data.getOrDefault("incident_date",
                data.getOrDefault("purchase_date", "[Purchase / Service Date]"));
        String description = data.getOrDefault("incident_description",
                data.getOrDefault("description", "[Description of defect/issue]"));
        String defect = data.getOrDefault("defect_description", "[Defect Description]");

        document.add(new Paragraph(
                "1. That the Complainant purchased/availed " + productName +
                        " from the Opposite Party on " + incidentDate + ".",
                normalFont));
        document.add(new Paragraph(" "));
        document.add(new Paragraph(
                "2. That after availing the said goods/service, the following issues were observed:", normalFont));
        document.add(new Paragraph("   " + defect, normalFont));
        document.add(new Paragraph(" "));
        document.add(new Paragraph("3. Full particulars of the complaint:", normalFont));
        document.add(new Paragraph("   " + description, normalFont));
        document.add(new Paragraph(" "));

        // ─── CAUSE OF ACTION ─────────────────────────────────────────────────
        document.add(new Paragraph("II. CAUSE OF ACTION", headerFont));
        document.add(new Paragraph(
                "The cause of action arose on " + incidentDate + " when the Opposite Party " +
                        "delivered defective goods/provided deficient service. The cause of action is continuing " +
                        "as the Opposite Party has refused/failed to rectify the same.",
                normalFont));
        document.add(new Paragraph(" "));

        // ─── FINANCIAL DETAILS ───────────────────────────────────────────────
        document.add(new Paragraph("III. FINANCIAL DETAILS", headerFont));
        String amount = data.getOrDefault("financial_loss_value", "[Amount]");
        String payment = data.getOrDefault("payment_details", "[Payment Mode]");
        document.add(new Paragraph("Amount Paid: ₹" + amount, normalFont));
        document.add(new Paragraph("Mode of Payment: " + payment, normalFont));
        document.add(new Paragraph(" "));

        // ─── JURISDICTION ────────────────────────────────────────────────────
        document.add(new Paragraph("IV. JURISDICTION", headerFont));
        document.add(new Paragraph(
                "This Hon'ble Commission has jurisdiction to entertain the present complaint " +
                        "as the Opposite Party is located/the cause of action arose within the jurisdiction of " +
                        data.getOrDefault("district", "[District]") + ", " + data.getOrDefault("state", "[State]") +
                        ". The value of goods/services does not exceed the pecuniary jurisdiction of this Commission.",
                normalFont));
        document.add(new Paragraph(" "));

        // ─── PRIOR COMPLAINTS ────────────────────────────────────────────────
        String priorComplaints = data.getOrDefault("prior_complaints", null);
        if (priorComplaints != null && !priorComplaints.isEmpty() && !priorComplaints.equals("EXPLICITLY_DENIED")) {
            document.add(new Paragraph("V. PRIOR COMPLAINTS / NOTICES SENT", headerFont));
            document.add(new Paragraph(priorComplaints, normalFont));
            document.add(new Paragraph(" "));
        }

        // ─── PRAYER ──────────────────────────────────────────────────────────
        document.add(new Paragraph("VI. PRAYER", headerFont));
        document.add(new Paragraph(
                "In view of the above facts, the Complainant most humbly prays that this Hon'ble Commission may be pleased to:",
                normalFont));
        document.add(new Paragraph(
                "a) Direct the Opposite Party to refund the amount of ₹" + amount + " with interest.", normalFont));
        document.add(new Paragraph(
                "b) Award compensation of ₹[amount] for mental agony and harassment caused.", normalFont));
        document.add(new Paragraph(
                "c) Award litigation costs.", normalFont));
        document.add(new Paragraph(
                "d) Pass any other order(s) as deemed fit and proper in the interest of justice.", normalFont));
        document.add(new Paragraph(" "));

        // ─── EVIDENCE ────────────────────────────────────────────────────────
        document.add(new Paragraph("VII. LIST OF DOCUMENTS (ANNEXURES)", headerFont));
        String evidence = data.getOrDefault("evidence_available", "Bills, receipts, and communication records");
        document.add(new Paragraph(evidence, normalFont));
        document.add(new Paragraph(" "));

        // ─── VERIFICATION ───────────────────────────────────────────────────
        document.add(new Paragraph("VIII. VERIFICATION", headerFont));
        document.add(new Paragraph(
                "I, " + complainantName + ", the Complainant above named, do hereby verify " +
                        "that the contents of this complaint are true and correct to the best of my knowledge " +
                        "and belief. No part of it is false and nothing material has been concealed.",
                normalFont));
        document.add(new Paragraph(" "));

        // ─── SIGNATURE ───────────────────────────────────────────────────────
        document.add(new Paragraph("Verified at " + data.getOrDefault("district", "[Place]") +
                " on " + today + ".", normalFont));
        document.add(new Paragraph(" "));
        document.add(new Paragraph("____________________", normalFont));
        document.add(new Paragraph("Name:    " + complainantName, boldFont));
        document.add(new Paragraph("Phone:   " + complainantPhone, normalFont));
        document.add(new Paragraph("Address: " + complainantAddr, normalFont));
        document.add(new Paragraph("Date:    " + today, normalFont));
        document.add(new Paragraph(" "));

        // ─── DISCLAIMER ─────────────────────────────────────────────────────
        document.add(new Paragraph(
                "DISCLAIMER: This document has been auto-generated by Satta Vizhi (AI Legal Assistant) " +
                        "based solely on user-provided information. It does not constitute legal advice. " +
                        "Please review with a qualified legal professional before official submission.",
                smallFont));
    }
}
