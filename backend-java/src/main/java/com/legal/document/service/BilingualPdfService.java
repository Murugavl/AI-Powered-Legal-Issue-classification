package com.legal.document.service;

import com.lowagie.text.*;
import com.lowagie.text.pdf.*;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class BilingualPdfService {

    // ── Palette ───────────────────────────────────────────────────────────────
    private static final Color NAVY       = new Color(15,  23,  42);
    private static final Color BLUE       = new Color(37,  99,  235);
    private static final Color BLUE_LITE  = new Color(219, 234, 254);
    private static final Color SLATE      = new Color(100, 116, 139);
    private static final Color DIVIDER    = new Color(203, 213, 225);
    private static final Color RED_DARK   = new Color(153, 27,  27);
    private static final Color RED_LITE   = new Color(254, 242, 242);
    private static final Color GRAY_200   = new Color(226, 232, 240);
    private static final Color WHITE      = Color.WHITE;
    private static final Color INK        = new Color(15,  23,  42);

    // ── Fonts ─────────────────────────────────────────────────────────────────
    private static Font f(int family, float sz, int style, Color c) {
        return new Font(family, sz, style, c);
    }

    private static final Font BRAND    = f(Font.HELVETICA, 17, Font.BOLD,   WHITE);
    private static final Font TAGLINE  = f(Font.HELVETICA,  8, Font.ITALIC, new Color(148, 163, 184));
    private static final Font BADGE1   = f(Font.HELVETICA,  9, Font.BOLD,   WHITE);
    private static final Font BADGE2   = f(Font.HELVETICA,  7, Font.NORMAL, new Color(191, 219, 254));
    private static final Font META_LBL = f(Font.HELVETICA,  7, Font.BOLD,   SLATE);
    private static final Font META_VAL = f(Font.HELVETICA,  9, Font.NORMAL, INK);
    private static final Font HEADING  = f(Font.HELVETICA, 12, Font.BOLD,   BLUE);
    private static final Font BODY     = f(Font.HELVETICA, 10, Font.NORMAL, INK);
    private static final Font BODY_B   = f(Font.HELVETICA, 10, Font.BOLD,   INK);
    private static final Font SMALL    = f(Font.HELVETICA,  8, Font.NORMAL, SLATE);
    private static final Font DISC_HDR = f(Font.HELVETICA,  8, Font.BOLD,   RED_DARK);
    private static final Font DISC_TXT = f(Font.HELVETICA,  8, Font.NORMAL, RED_DARK);
    private static final Font FOOT     = f(Font.HELVETICA,  7, Font.NORMAL, SLATE);

    // ── Page geometry — enough top margin so body text starts below header ────
    private static final float MARGIN_L   = 56;
    private static final float MARGIN_R   = 56;
    private static final float MARGIN_TOP = 120;   // reserved for page-event header
    private static final float MARGIN_BOT = 55;

    // ─────────────────────────────────────────────────────────────────────────
    // PUBLIC ENTRY POINT
    // ─────────────────────────────────────────────────────────────────────────
    public byte[] generateBilingualPdf(
            String userLanguageContent,
            String englishContent,
            String userLanguage,
            String disclaimerEn,
            String disclaimerUserLang,
            Map<String, Object> metadata) throws DocumentException {

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Document doc = new Document(PageSize.A4, MARGIN_L, MARGIN_R, MARGIN_TOP, MARGIN_BOT);

        try {
            PdfWriter writer = PdfWriter.getInstance(doc, out);

            boolean englishOnly = "en".equalsIgnoreCase(userLanguage);

            // Page-event handler draws the header & footer on every page
            PageDecorator decorator = new PageDecorator(
                    metadata,
                    englishOnly ? "en" : userLanguage,
                    englishOnly);
            writer.setPageEvent(decorator);

            doc.open();

            if (englishOnly) {
                renderBody(doc, englishContent, disclaimerEn);
            } else {
                // Page 1 — user language
                decorator.setPageMode(userLanguage, false);
                renderBody(doc, userLanguageContent, disclaimerUserLang);

                // Page 2 — English
                doc.newPage();
                decorator.setPageMode("en", true);
                renderBody(doc, englishContent, disclaimerEn);
            }

        } finally {
            doc.close();
        }
        return out.toByteArray();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // BODY — disclaimer (document text + disclaimer box, no header)
    // ─────────────────────────────────────────────────────────────────────────
    private void renderBody(Document doc, String content, String disclaimer) throws DocumentException {
        addContent(doc, content);
        addDisclaimer(doc, disclaimer);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // DOCUMENT TEXT RENDERER
    // ─────────────────────────────────────────────────────────────────────────
    private void addContent(Document doc, String content) throws DocumentException {
        if (content == null || content.isBlank()) {
            doc.add(new Paragraph("[No content generated]", SMALL));
            return;
        }

        String[] lines = content.split("\n");
        StringBuilder buf = new StringBuilder();

        for (String rawLine : lines) {
            String line = rawLine.trim();

            if (line.isBlank()) {
                flushPara(doc, buf);
                continue;
            }

            // Section heading: ALL-CAPS short line, or ends with ":"
            boolean isHeading = (line.equals(line.toUpperCase())
                    && line.length() > 3 && line.length() < 70
                    && !line.matches(".*\\d{4}.*"))
                    || (line.endsWith(":") && line.length() < 90 && !line.contains(","));

            boolean isNumbered = line.matches("^\\d+[.)].+");
            boolean isBullet   = line.matches("^[-*•]\\s.+");
            boolean hasBold    = line.contains("**");

            if (isHeading) {
                flushPara(doc, buf);
                doc.add(gap(5));
                Paragraph h = new Paragraph(line.replaceAll(":$", "").trim(), HEADING);
                h.setSpacingAfter(3);
                doc.add(h);
            } else if (isNumbered) {
                flushPara(doc, buf);
                Paragraph p = new Paragraph(line, BODY);
                p.setIndentationLeft(14);
                p.setSpacingAfter(4);
                p.setLeading(15);
                doc.add(p);
            } else if (isBullet) {
                flushPara(doc, buf);
                Paragraph p = new Paragraph("•  " + line.replaceFirst("^[-*•]\\s", ""), BODY);
                p.setIndentationLeft(14);
                p.setSpacingAfter(3);
                p.setLeading(15);
                doc.add(p);
            } else if (hasBold) {
                flushPara(doc, buf);
                doc.add(buildBoldLine(line));
            } else {
                buf.append(line).append(" ");
            }
        }
        flushPara(doc, buf);
        doc.add(gap(10));
    }

    private void flushPara(Document doc, StringBuilder sb) throws DocumentException {
        String t = sb.toString().trim();
        if (!t.isEmpty()) {
            Paragraph p = new Paragraph(t, BODY);
            p.setAlignment(Element.ALIGN_JUSTIFIED);
            p.setLeading(16);
            p.setSpacingAfter(6);
            doc.add(p);
        }
        sb.setLength(0);
    }

    private Paragraph buildBoldLine(String line) {
        Paragraph p = new Paragraph();
        p.setAlignment(Element.ALIGN_JUSTIFIED);
        p.setLeading(16);
        p.setSpacingAfter(6);
        String[] parts = line.split("\\*\\*");
        for (int i = 0; i < parts.length; i++)
            if (!parts[i].isEmpty())
                p.add(new Chunk(parts[i], i % 2 == 1 ? BODY_B : BODY));
        return p;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // DISCLAIMER
    // ─────────────────────────────────────────────────────────────────────────
    private void addDisclaimer(Document doc, String text) throws DocumentException {
        // horizontal rule
        PdfPTable rule = new PdfPTable(1);
        rule.setWidthPercentage(100);
        rule.setSpacingBefore(6);
        rule.setSpacingAfter(6);
        PdfPCell rc = new PdfPCell(new Phrase(" "));
        rc.setBorder(Rectangle.BOTTOM);
        rc.setBorderColorBottom(DIVIDER);
        rc.setBorderWidthBottom(0.5f);
        rc.setPaddingBottom(0);
        rule.addCell(rc);
        doc.add(rule);

        String clean = (text != null ? text : "")
                .replaceFirst("(?i)^disclaimer:\\s*", "").trim();
        if (clean.isEmpty())
            clean = "This document does not constitute legal advice. "
                  + "Please consult a qualified legal professional before official submission.";

        PdfPTable box = new PdfPTable(1);
        box.setWidthPercentage(100);

        PdfPCell cell = new PdfPCell();
        cell.setBackgroundColor(RED_LITE);
        cell.setBorderColor(new Color(252, 165, 165));
        cell.setBorderWidth(0.8f);
        cell.setPadding(10);

        Paragraph hdr = new Paragraph("⚠  DISCLAIMER — NOT LEGAL ADVICE", DISC_HDR);
        hdr.setSpacingAfter(4);
        cell.addElement(hdr);
        cell.addElement(new Paragraph(clean, DISC_TXT));
        box.addCell(cell);
        doc.add(box);
    }

    private Paragraph gap(float pts) {
        Paragraph p = new Paragraph(" ");
        p.setSpacingAfter(pts);
        return p;
    }

    private String langName(String code) {
        if (code == null) return "English";
        return switch (code.toLowerCase()) {
            case "ta" -> "Tamil";   case "hi" -> "Hindi";
            case "te" -> "Telugu";  case "kn" -> "Kannada";
            case "ml" -> "Malayalam"; case "mr" -> "Marathi";
            case "bn" -> "Bengali"; case "gu" -> "Gujarati";
            default   -> "English";
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PAGE DECORATOR — draws header + footer via page events
    // Header is stamped at the TOP of every page using onStartPage,
    // so it is always above the body text regardless of page flow.
    // ─────────────────────────────────────────────────────────────────────────
    private class PageDecorator extends PdfPageEventHelper {

        private final Map<String, Object> metadata;
        private String  lang;
        private boolean isEnglish;

        PageDecorator(Map<String, Object> metadata, String lang, boolean isEnglish) {
            this.metadata  = metadata;
            this.lang      = lang;
            this.isEnglish = isEnglish;
        }

        /** Called by generateBilingualPdf before doc.newPage() for page 2 */
        void setPageMode(String newLang, boolean english) {
            this.lang      = newLang;
            this.isEnglish = english;
        }

        // ── onStartPage: stamp header at top of each page ─────────────────
        @Override
        public void onStartPage(PdfWriter writer, Document document) {
            try {
                Rectangle page  = document.getPageSize();
                float     pageW = page.getWidth();
                float     top   = page.getTop();   // e.g. 841.89 for A4

                // Brand bar height = 48 pt, metadata strip height = 30 pt, gap = 4
                float barH  = 48f;
                float metaH = (metadata != null && !metadata.isEmpty()) ? 32f : 0f;
                float totalH = barH + metaH + 4;

                PdfContentByte cb = writer.getDirectContent();

                // ── Navy brand bar ────────────────────────────────────────
                cb.setColorFill(NAVY);
                cb.rectangle(MARGIN_L - 10, top - barH, pageW - MARGIN_L - MARGIN_R + 20, barH);
                cb.fill();

                // Blue right badge
                float badgeW = 90f;
                cb.setColorFill(BLUE);
                cb.rectangle(pageW - MARGIN_R - badgeW + 10, top - barH, badgeW, barH);
                cb.fill();

                // Brand text
                ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                        new Phrase("Satta Vizhi", BRAND),
                        MARGIN_L, top - 22, 0);
                ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                        new Phrase("AI-Powered Legal Document Assistant  |  India", TAGLINE),
                        MARGIN_L, top - 36, 0);

                // Badge text
                String b1 = isEnglish ? "ENGLISH" : langName(lang).toUpperCase();
                String b2 = isEnglish ? "OFFICIAL COPY" : "USER COPY";
                float badgeCX = pageW - MARGIN_R - badgeW / 2 + 10;
                ColumnText.showTextAligned(cb, Element.ALIGN_CENTER,
                        new Phrase(b1, BADGE1), badgeCX, top - 20, 0);
                ColumnText.showTextAligned(cb, Element.ALIGN_CENTER,
                        new Phrase(b2, BADGE2), badgeCX, top - 32, 0);

                // ── Metadata strip (blue-tinted) ──────────────────────────
                if (metadata != null && !metadata.isEmpty()) {
                    Map<String, Object> cells = new LinkedHashMap<>();
                    cells.put("GENERATED DATE",
                            LocalDate.now().format(DateTimeFormatter.ofPattern("dd MMM yyyy")));
                    cells.putAll(metadata);

                    float stripTop = top - barH - 4;
                    float stripH   = metaH;
                    int   n        = cells.size();
                    float cellW    = (pageW - MARGIN_L - MARGIN_R + 20) / n;
                    float x0       = MARGIN_L - 10;

                    cb.setColorFill(BLUE_LITE);
                    cb.rectangle(x0, stripTop - stripH, pageW - MARGIN_L - MARGIN_R + 20, stripH);
                    cb.fill();

                    // Light border lines between cells
                    cb.setColorStroke(new Color(147, 197, 253));
                    cb.setLineWidth(0.4f);
                    for (int i = 1; i < n; i++) {
                        float lx = x0 + cellW * i;
                        cb.moveTo(lx, stripTop);
                        cb.lineTo(lx, stripTop - stripH);
                    }
                    cb.stroke();

                    // Cell text
                    int idx = 0;
                    for (Map.Entry<String, Object> e : cells.entrySet()) {
                        float cx = x0 + cellW * idx + 6;
                        String lbl = e.getKey().toUpperCase();
                        String val = e.getValue() != null ? e.getValue().toString() : "—";
                        ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                                new Phrase(lbl, META_LBL), cx, stripTop - 11, 0);
                        ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                                new Phrase(val, META_VAL), cx, stripTop - 23, 0);
                        idx++;
                    }

                    // Separator line below metadata strip
                    cb.setColorStroke(DIVIDER);
                    cb.setLineWidth(0.5f);
                    cb.moveTo(MARGIN_L - 10, stripTop - stripH - 2);
                    cb.lineTo(pageW - MARGIN_R + 10, stripTop - stripH - 2);
                    cb.stroke();
                }

            } catch (Exception e) {
                // swallow — don't crash the PDF build
                e.printStackTrace();
            }
        }

        // ── onEndPage: footer ─────────────────────────────────────────────
        @Override
        public void onEndPage(PdfWriter writer, Document document) {
            PdfContentByte cb   = writer.getDirectContent();
            Rectangle page      = document.getPageSize();
            float y             = MARGIN_BOT - 18;
            float left          = MARGIN_L;
            float right         = page.getWidth() - MARGIN_R;

            cb.setColorStroke(DIVIDER);
            cb.setLineWidth(0.3f);
            cb.moveTo(left, MARGIN_BOT - 5);
            cb.lineTo(right, MARGIN_BOT - 5);
            cb.stroke();

            ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                    new Phrase("Satta Vizhi — AI Legal Document Assistant", FOOT),
                    left, y, 0);
            ColumnText.showTextAligned(cb, Element.ALIGN_RIGHT,
                    new Phrase("Page " + writer.getPageNumber() + "  |  Not Legal Advice", FOOT),
                    right, y, 0);
        }
    }
}
