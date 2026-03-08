package com.legal.document.service;

import com.lowagie.text.*;
import com.lowagie.text.pdf.*;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * BilingualPdfService
 *
 * Renders the filled Indian legal letter template as a clean, well-aligned PDF.
 * Supports full Unicode (Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali,
 * Gujarati, Marathi)
 * via embedded Noto Sans fonts loaded from the classpath.
 *
 * Template structure:
 * ┌─────────────────────────────────────────────────┐
 * │ [Header bar — document type badge + version] │
 * │ [Metadata strip — date | doc type | score] │
 * ├─────────────────────────────────────────────────┤
 * │ To │
 * │ [Authority] │
 * │ [City, State] │
 * │ │
 * │ Date: DD/MM/YYYY │
 * │ │
 * │ Subject: ... │
 * │ │
 * │ Respected Sir/Madam, │
 * │ │
 * │ [Body paragraphs — justified] │
 * │ │
 * │ Relevant documents attached: │
 * │ 1. ... │
 * │ │
 * │ Thanking you. │
 * │ │
 * │ Yours faithfully, │
 * │ ___________________________ │
 * │ [Name] / [Phone] │
 * ├─────────────────────────────────────────────────┤
 * │ [Disclaimer box] │
 * ├─────────────────────────────────────────────────┤
 * │ [Footer — page number | Not Legal Advice] │
 * └─────────────────────────────────────────────────┘
 */
@Service
public class BilingualPdfService {

    // ── Colour palette ────────────────────────────────────────────────────────
    private static final Color NAVY = new Color(15, 23, 42);
    private static final Color BLUE = new Color(37, 99, 235);
    private static final Color BLUE_LITE = new Color(219, 234, 254);
    private static final Color SLATE = new Color(100, 116, 139);
    private static final Color DIVIDER = new Color(203, 213, 225);
    private static final Color RED_DARK = new Color(153, 27, 27);
    private static final Color RED_LITE = new Color(254, 242, 242);
    private static final Color INK = new Color(15, 23, 42);
    private static final Color WHITE = Color.WHITE;

    // ── Page geometry (A4) ────────────────────────────────────────────────────
    private static final float ML = 72; // left margin
    private static final float MR = 72; // right margin
    private static final float MT = 120; // top margin (header bar + metadata strip)
    private static final float MB = 55; // bottom margin

    // ── Font cache ────────────────────────────────────────────────────────────
    // Built-in Helvetica (for header / decorative elements that use ASCII only)
    private static Font hv(float sz, int style, Color c) {
        return new Font(Font.HELVETICA, sz, style, c);
    }

    private static final Font F_BRAND = hv(13, Font.BOLD, WHITE);
    private static final Font F_TAGLINE = hv(7, Font.ITALIC, new Color(148, 163, 184));
    private static final Font F_BADGE1 = hv(9, Font.BOLD, WHITE);
    private static final Font F_BADGE2 = hv(7, Font.NORMAL, new Color(191, 219, 254));
    private static final Font F_META_L = hv(7, Font.BOLD, SLATE);
    private static final Font F_META_V = hv(8, Font.NORMAL, INK);
    private static final Font F_FOOT = hv(7, Font.NORMAL, SLATE);
    private static final Font F_DISC_H = hv(8, Font.BOLD, RED_DARK);

    /**
     * Unicode-capable body fonts loaded lazily from classpath.
     * Key = ISO 639-1 language code ("en", "ta", "hi", …)
     * Falls back to NotoSans-Regular (Latin) for any unknown script.
     */
    private static final Map<String, BaseFont> UNICODE_FONTS = new LinkedHashMap<>();

    private static BaseFont loadBaseFont(String resourcePath) {
        try (InputStream is = BilingualPdfService.class.getResourceAsStream(resourcePath)) {
            if (is == null) {
                System.err.println("[PDF] Font not found on classpath: " + resourcePath);
                return null;
            }
            byte[] bytes = is.readAllBytes();
            return BaseFont.createFont(resourcePath, BaseFont.IDENTITY_H, BaseFont.EMBEDDED, true, bytes, null);
        } catch (Exception e) {
            System.err.println("[PDF] Could not load font " + resourcePath + ": " + e.getMessage());
            return null;
        }
    }

    /**
     * Returns the best BaseFont for the given language code. Never null — falls
     * back to Helvetica.
     */
    private static BaseFont unicodeFontFor(String lang) {
        if (lang == null)
            lang = "en";
        String key = lang.toLowerCase();

        if (!UNICODE_FONTS.containsKey(key)) {
            // Load fonts lazily
            synchronized (UNICODE_FONTS) {
                if (!UNICODE_FONTS.containsKey(key)) {
                    String path = switch (key) {
                        case "ta" -> "/fonts/NotoSansTamil-Regular.ttf";
                        case "hi", "mr" -> "/fonts/NotoSansDevanagari-Regular.ttf";
                        case "te" -> "/fonts/NotoSansTelugu-Regular.ttf";
                        case "kn" -> "/fonts/NotoSansKannada-Regular.ttf";
                        case "ml" -> "/fonts/NotoSansMalayalam-Regular.ttf";
                        default -> "/fonts/NotoSans-Regular.ttf";
                    };
                    BaseFont bf = loadBaseFont(path);
                    if (bf == null) {
                        // Last fallback: built-in Helvetica (ASCII only)
                        try {
                            bf = BaseFont.createFont(BaseFont.HELVETICA, BaseFont.CP1252, false);
                        } catch (Exception ex) {
                            throw new RuntimeException("Cannot create fallback font", ex);
                        }
                    }
                    UNICODE_FONTS.put(key, bf);
                }
            }
        }
        return UNICODE_FONTS.get(key);
    }

    /** Build a body Font object for the given lang, size, and style. */
    private static Font bodyFont(String lang, float size, int style, Color color) {
        BaseFont bf = unicodeFontFor(lang);
        return new Font(bf, size, style, color);
    }

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
        Document doc = new Document(PageSize.A4, ML, MR, MT, MB);

        try {
            PdfWriter writer = PdfWriter.getInstance(doc, out);
            boolean englishOnly = "en".equalsIgnoreCase(userLanguage);

            PageDecorator decorator = new PageDecorator(metadata, userLanguage, englishOnly);
            writer.setPageEvent(decorator);
            doc.open();

            if (englishOnly) {
                renderDocument(doc, englishContent, disclaimerEn, "en");
            } else {
                // Page 1 — user's regional language
                decorator.setMode(userLanguage, false);
                renderDocument(doc, userLanguageContent, disclaimerUserLang, userLanguage);

                // Page 2+ — English (official copy)
                doc.newPage();
                decorator.setMode("en", true);
                renderDocument(doc, englishContent, disclaimerEn, "en");
            }

        } finally {
            doc.close();
        }
        return out.toByteArray();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RENDER ONE SIDE (letter body + disclaimer)
    // ─────────────────────────────────────────────────────────────────────────
    private void renderDocument(Document doc, String content, String disclaimer, String lang)
            throws DocumentException {
        renderLetterBody(doc, content, lang);
        addDisclaimer(doc, disclaimer, lang);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // LETTER BODY RENDERER
    //
    // Template lines are detected by their content and formatted appropriately.
    // Body paragraphs are accumulated and flushed as justified text.
    // Unicode font is used throughout so Tamil/Hindi/Telugu etc. render correctly.
    // ─────────────────────────────────────────────────────────────────────────
    private void renderLetterBody(Document doc, String content, String lang) throws DocumentException {
        if (content == null || content.isBlank()) {
            doc.add(new Paragraph("[Document content unavailable]", bodyFont(lang, 9, Font.NORMAL, SLATE)));
            return;
        }

        // Build lang-specific fonts (reused throughout this letter)
        Font fBody = bodyFont(lang, 10, Font.NORMAL, INK);
        Font fBold = bodyFont(lang, 10, Font.BOLD, INK);

        String[] lines = content.split("\n");
        boolean inBody = false; // true after "Respected Sir/Madam,"
        boolean inDocsList = false; // true after "Relevant documents attached:"
        StringBuilder bodyBuf = new StringBuilder();

        for (String raw : lines) {
            String line = raw.trim();

            // ── Blank line ────────────────────────────────────────────────
            if (line.isEmpty()) {
                if (inBody && !inDocsList) {
                    flushBody(doc, bodyBuf, fBody);
                } else if (!inBody) {
                    doc.add(spacer(5));
                }
                continue;
            }

            // ── "To" — letter opener ──────────────────────────────────────
            if (line.equals("To")) {
                doc.add(spacer(4));
                Paragraph p = new Paragraph("To", fBold);
                p.setSpacingAfter(0);
                doc.add(p);
                continue;
            }

            // ── "Date:" ───────────────────────────────────────────────────
            if (line.startsWith("Date:")) {
                doc.add(spacer(2));
                doc.add(new Paragraph(line, fBody));
                doc.add(spacer(2));
                continue;
            }

            // ── "Subject:" ────────────────────────────────────────────────
            if (line.startsWith("Subject:")) {
                String subjectText = line.substring("Subject:".length()).trim();
                Paragraph p = new Paragraph();
                p.add(new Chunk("Subject: ", fBold));
                p.add(new Chunk(subjectText, fBody));
                p.setSpacingAfter(4);
                doc.add(p);
                continue;
            }

            // ── Salutation — marks start of body ─────────────────────────
            if (line.startsWith("Respected Sir/Madam") || line.startsWith("Respected Sir")
                    || line.startsWith("Respected Madam")
                    || line.contains("Respected Sir/Madam")) {
                doc.add(spacer(2));
                doc.add(new Paragraph(line, fBody));
                doc.add(spacer(4));
                inBody = true;
                continue;
            }

            // ── "Relevant documents attached:" ────────────────────────────
            // Only recognised when we're already in the body AND the line is
            // a short header; avoids false-bolding body sentences ending in ":"
            if (inBody && isDocumentsHeader(line)) {
                flushBody(doc, bodyBuf, fBody);
                inDocsList = true;
                doc.add(spacer(2));
                doc.add(new Paragraph(line, fBold));
                continue;
            }

            // ── Numbered list items under the documents section ───────────
            if (inDocsList && line.matches("^\\d+\\.\\s+.+")) {
                Paragraph p = new Paragraph(line, fBody);
                p.setIndentationLeft(20);
                p.setSpacingAfter(3);
                p.setLeading(14);
                doc.add(p);
                continue;
            }

            // ── "Thanking you." ───────────────────────────────────────────
            if (line.startsWith("Thanking you") || line.startsWith("நன்றி") /* Tamil */
                    || line.startsWith("धन्यवाद")) {
                flushBody(doc, bodyBuf, fBody);
                inDocsList = false;
                doc.add(spacer(4));
                doc.add(new Paragraph(line, fBody));
                continue;
            }

            // ── "Yours faithfully," ───────────────────────────────────────
            if (line.startsWith("Yours faithfully") || line.startsWith("Yours sincerely")
                    || line.startsWith("உங்கள் உண்மையுள்ள") // Tamil
                    || line.startsWith("भवदीय")) { // Hindi
                flushBody(doc, bodyBuf, fBody);
                doc.add(spacer(6));
                doc.add(new Paragraph(line, fBody));
                doc.add(spacer(14)); // signature gap
                continue;
            }

            // ── Signature underscores ─────────────────────────────────────
            if (line.startsWith("___")) {
                doc.add(new Paragraph(line, fBody));
                doc.add(spacer(2));
                continue;
            }

            // ── Everything else ───────────────────────────────────────────
            if (inBody) {
                // If we're past the docs list, accumulate as body paragraph
                if (!inDocsList) {
                    bodyBuf.append(raw).append(" ");
                }
                // Lines inside the docs list that don't match numbered pattern
                // (e.g. Tamil numbered items with different format) — render directly
                else {
                    Paragraph p = new Paragraph(line, fBody);
                    p.setIndentationLeft(20);
                    p.setSpacingAfter(3);
                    doc.add(p);
                }
            } else {
                // Pre-salutation: authority name, city, etc.
                Paragraph p = new Paragraph(line, fBody);
                p.setSpacingAfter(0);
                doc.add(p);
            }
        }

        flushBody(doc, bodyBuf, fBody);
        doc.add(spacer(8));
    }

    /**
     * Determines whether a line is the "Relevant documents attached:" header.
     * Must: (a) be inside the body (caller checks this)
     * (b) end with a colon
     * (c) be short (< 80 chars) — a real header, not a mid-paragraph sentence
     * (d) NOT start with "Date" or "Subject" (already handled above)
     * (e) NOT look like a body sentence (body sentences are long)
     */
    private static boolean isDocumentsHeader(String line) {
        if (!line.endsWith(":"))
            return false;
        if (line.length() >= 80)
            return false;
        if (line.startsWith("Date"))
            return false;
        if (line.startsWith("Subject"))
            return false;
        // Must be a short header — fewer than 7 words
        String[] words = line.split("\\s+");
        return words.length <= 7;
    }

    private void flushBody(Document doc, StringBuilder buf, Font fBody) throws DocumentException {
        String text = buf.toString().trim();
        if (!text.isEmpty()) {
            Paragraph p = new Paragraph(text, fBody);
            p.setAlignment(Element.ALIGN_JUSTIFIED);
            p.setLeading(17);
            p.setSpacingAfter(8);
            doc.add(p);
        }
        buf.setLength(0);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // DISCLAIMER BOX
    // ─────────────────────────────────────────────────────────────────────────
    private void addDisclaimer(Document doc, String text, String lang) throws DocumentException {
        // Divider rule
        PdfPTable rule = new PdfPTable(1);
        rule.setWidthPercentage(100);
        rule.setSpacingBefore(8);
        rule.setSpacingAfter(6);
        PdfPCell rc = new PdfPCell(new Phrase(" "));
        rc.setBorder(Rectangle.BOTTOM);
        rc.setBorderColorBottom(DIVIDER);
        rc.setBorderWidthBottom(0.5f);
        rc.setPaddingBottom(0);
        rule.addCell(rc);
        doc.add(rule);

        // Clean the text — remove any accidental "Disclaimer:" prefix duplicates
        String clean = (text != null ? text : "")
                .replaceFirst("(?i)^disclaimer[:\\s]+", "").trim();
        if (clean.isEmpty()) {
            clean = "This document does not constitute legal advice. "
                    + "Please consult a qualified legal professional before official submission.";
        }

        Font fDiscBody = bodyFont(lang, 8, Font.NORMAL, RED_DARK);

        PdfPTable box = new PdfPTable(1);
        box.setWidthPercentage(100);
        PdfPCell cell = new PdfPCell();
        cell.setBackgroundColor(RED_LITE);
        cell.setBorderColor(new Color(252, 165, 165));
        cell.setBorderWidth(0.8f);
        cell.setPadding(10);

        Paragraph hdr = new Paragraph("DISCLAIMER — NOT LEGAL ADVICE", F_DISC_H);
        hdr.setSpacingAfter(4);
        cell.addElement(hdr);

        Paragraph body = new Paragraph(clean, fDiscBody);
        body.setLeading(12);
        cell.addElement(body);
        box.addCell(cell);
        doc.add(box);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // HELPERS
    // ─────────────────────────────────────────────────────────────────────────
    private Paragraph spacer(float pts) {
        Paragraph p = new Paragraph(" ");
        p.setSpacingAfter(pts);
        return p;
    }

    private String langName(String code) {
        if (code == null)
            return "English";
        return switch (code.toLowerCase()) {
            case "ta" -> "Tamil";
            case "hi" -> "Hindi";
            case "te" -> "Telugu";
            case "kn" -> "Kannada";
            case "ml" -> "Malayalam";
            case "mr" -> "Marathi";
            case "bn" -> "Bengali";
            case "gu" -> "Gujarati";
            default -> "English";
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PAGE DECORATOR — header bar + metadata strip via PdfPageEventHelper
    // Drawn with PdfContentByte so it's always at the physical top,
    // completely independent of document text flow.
    // ─────────────────────────────────────────────────────────────────────────
    private class PageDecorator extends PdfPageEventHelper {

        private final Map<String, Object> metadata;
        private String lang;
        private boolean isEnglish;

        PageDecorator(Map<String, Object> metadata, String lang, boolean isEnglish) {
            this.metadata = metadata;
            this.lang = lang;
            this.isEnglish = isEnglish;
        }

        void setMode(String lang, boolean isEnglish) {
            this.lang = lang;
            this.isEnglish = isEnglish;
        }

        @Override
        public void onStartPage(PdfWriter writer, Document document) {
            try {
                Rectangle page = document.getPageSize();
                float pageW = page.getWidth();
                float top = page.getTop();

                float barH = 44f;
                float metaH = 32f;

                PdfContentByte cb = writer.getDirectContent();

                // ── Navy header bar ───────────────────────────────────────
                cb.setColorFill(NAVY);
                cb.rectangle(0, top - barH, pageW, barH);
                cb.fill();

                // Blue badge on the right
                float badgeW = 100f;
                cb.setColorFill(BLUE);
                cb.rectangle(pageW - badgeW, top - barH, badgeW, barH);
                cb.fill();

                // Header text
                ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                        new Phrase("AI-Powered Legal Document Assistant  |  India", F_BRAND),
                        ML, top - 19, 0);
                ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                        new Phrase(
                                "Automatically generated — Review with a qualified legal professional before submission",
                                F_TAGLINE),
                        ML, top - 33, 0);

                // Badge text
                String b1 = isEnglish ? "ENGLISH" : langName(lang).toUpperCase();
                String b2 = isEnglish ? "OFFICIAL COPY" : "USER COPY";
                float cx = pageW - badgeW / 2f;
                ColumnText.showTextAligned(cb, Element.ALIGN_CENTER, new Phrase(b1, F_BADGE1), cx, top - 17, 0);
                ColumnText.showTextAligned(cb, Element.ALIGN_CENTER, new Phrase(b2, F_BADGE2), cx, top - 30, 0);

                // ── Metadata strip (blue-tinted) ──────────────────────────
                Map<String, Object> cells = new LinkedHashMap<>();
                if (metadata != null)
                    cells.putAll(metadata);
                cells.put("GENERATED", LocalDate.now().format(DateTimeFormatter.ofPattern("dd MMM yyyy")));

                float stripTop = top - barH;
                int n = cells.size();
                if (n > 0) {
                    float cellW = pageW / n;

                    cb.setColorFill(BLUE_LITE);
                    cb.rectangle(0, stripTop - metaH, pageW, metaH);
                    cb.fill();

                    // Vertical dividers
                    cb.setColorStroke(new Color(147, 197, 253));
                    cb.setLineWidth(0.4f);
                    for (int i = 1; i < n; i++) {
                        cb.moveTo(cellW * i, stripTop - 3);
                        cb.lineTo(cellW * i, stripTop - metaH + 3);
                    }
                    cb.stroke();

                    // Cell labels and values
                    int idx = 0;
                    for (Map.Entry<String, Object> e : cells.entrySet()) {
                        float cx2 = cellW * idx + 10;
                        String lbl = e.getKey().toUpperCase();
                        String val = truncate(e.getValue() != null ? e.getValue().toString() : "—", 30);
                        ColumnText.showTextAligned(cb, Element.ALIGN_LEFT, new Phrase(lbl, F_META_L), cx2,
                                stripTop - 11, 0);
                        ColumnText.showTextAligned(cb, Element.ALIGN_LEFT, new Phrase(val, F_META_V), cx2,
                                stripTop - 24, 0);
                        idx++;
                    }
                }

                // Bottom separator
                cb.setColorStroke(DIVIDER);
                cb.setLineWidth(0.5f);
                cb.moveTo(0, stripTop - metaH - 2);
                cb.lineTo(pageW, stripTop - metaH - 2);
                cb.stroke();

            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @Override
        public void onEndPage(PdfWriter writer, Document document) {
            PdfContentByte cb = writer.getDirectContent();
            float pageW = document.getPageSize().getWidth();
            float y = MB - 18;

            cb.setColorStroke(DIVIDER);
            cb.setLineWidth(0.3f);
            cb.moveTo(ML, MB - 5);
            cb.lineTo(pageW - MR, MB - 5);
            cb.stroke();

            ColumnText.showTextAligned(cb, Element.ALIGN_LEFT,
                    new Phrase("AI Legal Document Assistant", F_FOOT), ML, y, 0);
            ColumnText.showTextAligned(cb, Element.ALIGN_RIGHT,
                    new Phrase("Page " + writer.getPageNumber() + "  |  Not Legal Advice", F_FOOT),
                    pageW - MR, y, 0);
        }

        private String truncate(String s, int maxLen) {
            return s.length() > maxLen ? s.substring(0, maxLen - 1) + "…" : s;
        }
    }
}
