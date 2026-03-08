package com.legal.document.service;

import com.lowagie.text.*;
import com.lowagie.text.pdf.*;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * BilingualPdfService
 *
 * Renders the Indian From/To petition template produced by bilingual_generator.py.
 *
 * Template structure:
 *
 *   From
 *   [Name],
 *   [Address],
 *   [City],
 *   [District - Pincode],
 *   [State]
 *
 *   To
 *   [Authority],
 *   [City, District]
 *
 *   Ref No: ...
 *
 *   Sub: [subject]
 *
 *   Respected Sir/Madam,
 *
 *   [Body paragraphs — first person, justified]
 *
 *   Relevant documents attached:
 *   1. ...
 *
 *   Thank You,
 *
 *   Date: DD/MM/YYYY
 *
 *   Signature: ___________________________
 *   [Name]
 *   [Phone]
 *
 *   DISCLAIMER — NOT LEGAL ADVICE
 *   [text]
 */
@Service
public class BilingualPdfService {

    // ── Colours ────────────────────────────────────────────────────────────────
    private static final Color INK        = new Color(15,  23,  42);
    private static final Color SLATE      = new Color(100, 116, 139);
    private static final Color DIVIDER    = new Color(203, 213, 225);
    private static final Color BLUE_BOLD  = new Color(30,  64,  175);
    private static final Color RED_DARK   = new Color(153, 27,  27);
    private static final Color RED_LITE   = new Color(254, 242, 242);
    private static final Color NAVY       = new Color(15,  23,  42);
    private static final Color BADGE_BLUE = new Color(37,  99,  235);

    // ── Page geometry (A4) ─────────────────────────────────────────────────────
    private static final float ML = 72;
    private static final float MR = 72;
    private static final float MT = 112;  // top margin — room for header bar
    private static final float MB = 55;

    private static final Font F_DISC_HDR = new Font(Font.HELVETICA, 8, Font.BOLD, RED_DARK);

    // ── Unicode font cache ─────────────────────────────────────────────────────
    private static final Map<String, BaseFont> FONT_CACHE = new LinkedHashMap<>();

    private static BaseFont loadBaseFont(String path) {
        try (InputStream is = BilingualPdfService.class.getResourceAsStream(path)) {
            if (is == null) { System.err.println("[PDF] Font not found: " + path); return null; }
            byte[] b = is.readAllBytes();
            return BaseFont.createFont(path, BaseFont.IDENTITY_H, BaseFont.EMBEDDED, true, b, null);
        } catch (Exception e) {
            System.err.println("[PDF] Font error " + path + ": " + e.getMessage());
            return null;
        }
    }

    private static BaseFont unicodeFontFor(String lang) {
        String key = (lang == null) ? "en" : lang.toLowerCase();
        return FONT_CACHE.computeIfAbsent(key, k -> {
            String path = switch (k) {
                case "ta"       -> "/fonts/NotoSansTamil-Regular.ttf";
                case "hi", "mr" -> "/fonts/NotoSansDevanagari-Regular.ttf";
                case "te"       -> "/fonts/NotoSansTelugu-Regular.ttf";
                case "kn"       -> "/fonts/NotoSansKannada-Regular.ttf";
                case "ml"       -> "/fonts/NotoSansMalayalam-Regular.ttf";
                default         -> "/fonts/NotoSans-Regular.ttf";
            };
            BaseFont bf = loadBaseFont(path);
            if (bf == null) {
                try { bf = BaseFont.createFont(BaseFont.HELVETICA, BaseFont.CP1252, false); }
                catch (Exception ex) { throw new RuntimeException("No fallback font", ex); }
            }
            return bf;
        });
    }

    private static Font f(String lang, float size, int style, Color color) {
        return new Font(unicodeFontFor(lang), size, style, color);
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
            PdfWriter writer   = PdfWriter.getInstance(doc, out);
            boolean engOnly    = "en".equalsIgnoreCase(userLanguage);
            PageDecorator deco = new PageDecorator(writer, metadata, userLanguage, engOnly);
            writer.setPageEvent(deco);
            doc.open();

            if (engOnly) {
                renderLetter(doc, englishContent, "en");
            } else {
                deco.setMode(userLanguage, false);
                renderLetter(doc, userLanguageContent, userLanguage);

                doc.newPage();
                deco.setMode("en", true);
                renderLetter(doc, englishContent, "en");
            }
        } finally {
            doc.close();
        }
        return out.toByteArray();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // RENDER ONE LETTER (no separate disclaimer — it's embedded in content)
    // ─────────────────────────────────────────────────────────────────────────
    private void renderLetter(Document doc, String content, String lang)
            throws DocumentException {
        if (content == null || content.isBlank()) {
            doc.add(new Paragraph("[No content]", f(lang, 9, Font.NORMAL, SLATE)));
            return;
        }

        Font fBody    = f(lang, 10, Font.NORMAL, INK);
        Font fBold    = f(lang, 10, Font.BOLD,   INK);
        Font fSubj    = f(lang, 10, Font.BOLD,   BLUE_BOLD);
        Font fLabel   = f(lang, 10, Font.BOLD,   INK);

        String[]      lines           = content.split("\\n", -1);
        boolean       pastSalutation  = false;
        boolean       inDisclaimer    = false;
        boolean       inSignatureBlock= false;
        StringBuilder proseBuf        = new StringBuilder();

        for (String raw : lines) {
            String line = raw.trim();

            // ── Skip old-format section headings ─────────────────────────
            if (isOldFormatHeading(line)) continue;

            // ── Blank line ───────────────────────────────────────────────
            if (line.isEmpty()) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(3));
                continue;
            }

            // ── "From" — start of sender block ───────────────────────────
            if (line.equals("From")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(2));
                doc.add(new Paragraph("From", fBold));
                continue;
            }

            // ── "To" — start of recipient block ──────────────────────────
            if (line.equals("To")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(6));
                doc.add(new Paragraph("To", fBold));
                continue;
            }

            // ── "Ref No:" line ────────────────────────────────────────────
            if (line.startsWith("Ref No:")) {
                flushProse(doc, proseBuf, fBody);
                Paragraph p = new Paragraph();
                p.add(new Chunk("Ref No: ", fLabel));
                p.add(new Chunk(line.substring("Ref No:".length()).trim(), fBody));
                p.setSpacingAfter(2);
                doc.add(p);
                continue;
            }

            // ── "Sub:" line ───────────────────────────────────────────────
            if (line.startsWith("Sub:")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(4));
                String subText = line.substring("Sub:".length()).trim();
                Paragraph p = new Paragraph();
                p.add(new Chunk("Sub: ", fSubj));
                p.add(new Chunk(subText, fBold));
                p.setSpacingAfter(4);
                doc.add(p);
                continue;
            }

            // ── Salutation ────────────────────────────────────────────────
            if (isSalutation(line)) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(2));
                doc.add(new Paragraph(line, fBody));
                doc.add(spacer(6));
                pastSalutation  = true;
                inSignatureBlock = false;
                continue;
            }

            // ── "Relevant documents attached:" ────────────────────────────
            if (startsWithAny(line, "Relevant documents attached",
                    "சம்பந்தப்பட்ட ஆவணங்கள்", "संलग्न दस्तावेज़")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(6));
                doc.add(new Paragraph(line, fBold));
                continue;
            }

            // ── Numbered list item ────────────────────────────────────────
            if (line.matches("^\\d+\\.\\s+.+")) {
                flushProse(doc, proseBuf, fBody);
                Paragraph p = new Paragraph(line, fBody);
                p.setIndentationLeft(20);
                p.setSpacingAfter(2);
                doc.add(p);
                continue;
            }

            // ── "Thank You," / "Thanking you." ────────────────────────────
            if (startsWithAny(line, "Thank You", "Thanking you", "நன்றி", "धन्यवाद")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(8));
                doc.add(new Paragraph(line, fBody));
                inSignatureBlock = true;
                continue;
            }

            // ── "Date:" line in signature ─────────────────────────────────
            if (line.startsWith("Date:")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(4));
                Paragraph p = new Paragraph();
                p.add(new Chunk("Date: ", fLabel));
                p.add(new Chunk(line.substring("Date:".length()).trim(), fBody));
                doc.add(p);
                continue;
            }

            // ── "Signature:" line ─────────────────────────────────────────
            if (line.startsWith("Signature:")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(spacer(6));
                doc.add(new Paragraph(line, fBody));
                inSignatureBlock = true;
                continue;
            }

            // ── Signature underline ───────────────────────────────────────
            if (line.startsWith("___")) {
                doc.add(new Paragraph(line, fBody));
                doc.add(spacer(2));
                continue;
            }

            // ── DISCLAIMER heading ────────────────────────────────────────
            if (line.toUpperCase().startsWith("DISCLAIMER")) {
                flushProse(doc, proseBuf, fBody);
                inDisclaimer = true;
                // Render disclaimer box header
                addDisclaimerHeader(doc);
                continue;
            }

            // ── Disclaimer body text ──────────────────────────────────────
            if (inDisclaimer) {
                addDisclaimerBody(doc, line, lang);
                continue;
            }

            // ── Everything else ───────────────────────────────────────────
            if (!pastSalutation) {
                // Pre-salutation: From/To address lines, sub
                // Lines ending in comma are address continuation lines
                Paragraph p = new Paragraph(line, fBody);
                p.setSpacingAfter(1);
                doc.add(p);
            } else if (inSignatureBlock) {
                Paragraph p = new Paragraph(line, fBody);
                p.setSpacingAfter(2);
                doc.add(p);
            } else {
                // Body prose — accumulate for justified paragraph rendering
                if (proseBuf.length() > 0) proseBuf.append(" ");
                proseBuf.append(raw.trim());
            }
        }

        flushProse(doc, proseBuf, fBody);
        doc.add(spacer(6));
    }

    private void flushProse(Document doc, StringBuilder buf, Font font) throws DocumentException {
        String text = buf.toString().trim();
        if (!text.isEmpty()) {
            Paragraph p = new Paragraph(text, font);
            p.setAlignment(Element.ALIGN_JUSTIFIED);
            p.setLeading(17);
            p.setSpacingAfter(8);
            doc.add(p);
        }
        buf.setLength(0);
    }

    // ── Disclaimer rendered as a single red-bordered box ──────────────────────
    private boolean disclaimerBoxStarted = false;
    private PdfPCell disclaimerCell = null;
    private PdfPTable disclaimerTable = null;

    private void addDisclaimerHeader(Document doc) throws DocumentException {
        // Divider rule
        PdfPTable rule = new PdfPTable(1);
        rule.setWidthPercentage(100);
        rule.setSpacingBefore(12);
        rule.setSpacingAfter(6);
        PdfPCell rc = new PdfPCell(new Phrase(" "));
        rc.setBorder(Rectangle.BOTTOM);
        rc.setBorderColorBottom(DIVIDER);
        rc.setBorderWidthBottom(0.5f);
        rc.setPaddingBottom(0);
        rule.addCell(rc);
        doc.add(rule);

        // Start disclaimer box
        disclaimerTable = new PdfPTable(1);
        disclaimerTable.setWidthPercentage(100);
        disclaimerCell = new PdfPCell();
        disclaimerCell.setBackgroundColor(RED_LITE);
        disclaimerCell.setBorderColor(new Color(252, 165, 165));
        disclaimerCell.setBorderWidth(0.8f);
        disclaimerCell.setPadding(10);

        Paragraph hdr = new Paragraph("DISCLAIMER — NOT LEGAL ADVICE", F_DISC_HDR);
        hdr.setSpacingAfter(4);
        disclaimerCell.addElement(hdr);
        disclaimerBoxStarted = true;
    }

    private void addDisclaimerBody(Document doc, String text, String lang) throws DocumentException {
        if (!disclaimerBoxStarted || disclaimerCell == null) return;

        Font fDiscBody = new Font(unicodeFontFor(lang), 8, Font.NORMAL, RED_DARK);
        Paragraph body = new Paragraph(text, fDiscBody);
        body.setLeading(12);
        disclaimerCell.addElement(body);

        // Finalise box
        disclaimerTable.addCell(disclaimerCell);
        doc.add(disclaimerTable);
        disclaimerBoxStarted = false;
        disclaimerCell  = null;
        disclaimerTable = null;
    }

    // ── Helpers ────────────────────────────────────────────────────────────────
    private static boolean isOldFormatHeading(String line) {
        if (line.length() < 3 || line.length() > 60) return false;
        if (line.matches("[-=]{4,}.*")) return true;
        // All-caps multi-word lines like "COMPLAINANT DETAILS", "INCIDENT DETAILS"
        if (line.equals(line.toUpperCase()) && line.matches("[A-Z][A-Z /\\-]{5,}")) {
            // Whitelist legitimate all-caps that appear in our template
            if (line.startsWith("DISCLAIMER")) return false;
            return true;
        }
        return false;
    }

    private static boolean isSalutation(String line) {
        return line.startsWith("Respected Sir/Madam")
            || line.startsWith("Respected Sir")
            || line.startsWith("Respected Madam")
            || line.startsWith("மதிப்பிற்குரிய")
            || line.startsWith("आदरणीय");
    }

    private static boolean startsWithAny(String line, String... prefixes) {
        for (String p : prefixes) if (line.startsWith(p)) return true;
        return false;
    }

    private Paragraph spacer(float pts) {
        Paragraph p = new Paragraph(" ");
        p.setSpacingAfter(pts);
        return p;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // PAGE DECORATOR — Header bar + metadata strip + footer
    // ─────────────────────────────────────────────────────────────────────────
    private static class PageDecorator extends PdfPageEventHelper {
        private final PdfWriter          writer;
        private final Map<String, Object> metadata;
        private       String             currentLang;
        private       boolean            isEnglishCopy;

        PageDecorator(PdfWriter writer, Map<String, Object> metadata,
                      String lang, boolean englishOnly) {
            this.writer        = writer;
            this.metadata      = metadata;
            this.currentLang   = lang;
            this.isEnglishCopy = englishOnly;
        }

        void setMode(String lang, boolean englishCopy) {
            this.currentLang   = lang;
            this.isEnglishCopy = englishCopy;
        }

        @Override
        public void onStartPage(PdfWriter w, Document doc) {
            PdfContentByte cb   = w.getDirectContent();
            float pageW         = doc.getPageSize().getWidth();
            float pageH         = doc.getPageSize().getHeight();

            // ── Header bar (navy, 44pt) ────────────────────────────────────
            cb.saveState();
            cb.setColorFill(NAVY);
            cb.rectangle(0, pageH - 44, pageW, 44);
            cb.fill();

            cb.setColorFill(BADGE_BLUE);
            cb.rectangle(pageW - 90, pageH - 44, 90, 44);
            cb.fill();
            cb.restoreState();

            try {
                BaseFont hf = BaseFont.createFont(BaseFont.HELVETICA_BOLD, BaseFont.CP1252, false);
                BaseFont bf = BaseFont.createFont(BaseFont.HELVETICA,      BaseFont.CP1252, false);

                cb.beginText();
                cb.setColorFill(Color.WHITE);
                cb.setFontAndSize(hf, 11);
                cb.showTextAligned(Element.ALIGN_LEFT,
                        "AI-Powered Legal Document Assistant | India",
                        doc.leftMargin(), pageH - 20, 0);

                cb.setFontAndSize(bf, 7);
                cb.showTextAligned(Element.ALIGN_LEFT,
                        "Automatically generated — Review with a legal professional before submission",
                        doc.leftMargin(), pageH - 34, 0);

                // Badge text
                cb.setFontAndSize(hf, 7);
                cb.showTextAligned(Element.ALIGN_CENTER,
                        isEnglishCopy ? "ENGLISH" : "USER COPY",
                        pageW - 45, pageH - 18, 0);
                if (isEnglishCopy) {
                    cb.showTextAligned(Element.ALIGN_CENTER, "OFFICIAL COPY",
                            pageW - 45, pageH - 30, 0);
                }
                cb.endText();

                // ── Metadata strip (light blue, 30pt) ──────────────────────
                float stripTop = pageH - 44;
                cb.saveState();
                cb.setColorFill(new Color(219, 234, 254));
                cb.rectangle(0, stripTop - 30, pageW, 30);
                cb.fill();
                cb.restoreState();

                cb.beginText();
                cb.setColorFill(NAVY);
                float textY = stripTop - 12;
                float third = pageW / 3f;

                String docType = "";
                String score   = "";
                String genDate = java.time.LocalDate.now()
                        .format(java.time.format.DateTimeFormatter.ofPattern("dd MMM yyyy"));
                if (metadata != null) {
                    docType = String.valueOf(metadata.getOrDefault("Document Type", ""));
                    score   = String.valueOf(metadata.getOrDefault("Evidence Readiness Score", ""));
                }

                cb.setFontAndSize(hf, 6.5f);
                cb.showTextAligned(Element.ALIGN_CENTER, "DOCUMENT TYPE",           third * 0.5f, textY + 8, 0);
                cb.setFontAndSize(bf, 7.5f);
                cb.showTextAligned(Element.ALIGN_CENTER, docType,                   third * 0.5f, textY - 2, 0);

                cb.setFontAndSize(hf, 6.5f);
                cb.showTextAligned(Element.ALIGN_CENTER, "EVIDENCE READINESS SCORE",third * 1.5f, textY + 8, 0);
                cb.setFontAndSize(bf, 7.5f);
                cb.showTextAligned(Element.ALIGN_CENTER, score,                     third * 1.5f, textY - 2, 0);

                cb.setFontAndSize(hf, 6.5f);
                cb.showTextAligned(Element.ALIGN_CENTER, "GENERATED DATE",          third * 2.5f, textY + 8, 0);
                cb.setFontAndSize(bf, 7.5f);
                cb.showTextAligned(Element.ALIGN_CENTER, genDate,                   third * 2.5f, textY - 2, 0);
                cb.endText();

                // Vertical dividers in strip
                cb.saveState();
                cb.setColorStroke(DIVIDER);
                cb.setLineWidth(0.5f);
                cb.moveTo(third,     stripTop);     cb.lineTo(third,     stripTop - 30);
                cb.moveTo(third * 2, stripTop);     cb.lineTo(third * 2, stripTop - 30);
                cb.stroke();
                cb.restoreState();

            } catch (Exception e) {
                // Silently skip header if font fails
            }
        }

        @Override
        public void onEndPage(PdfWriter w, Document doc) {
            PdfContentByte cb = w.getDirectContent();
            try {
                BaseFont hf = BaseFont.createFont(BaseFont.HELVETICA,      BaseFont.CP1252, false);
                BaseFont bf = BaseFont.createFont(BaseFont.HELVETICA_BOLD, BaseFont.CP1252, false);
                float pageW = doc.getPageSize().getWidth();
                float footY = doc.bottomMargin() - 20;

                cb.beginText();
                cb.setColorFill(SLATE);
                cb.setFontAndSize(hf, 7);
                cb.showTextAligned(Element.ALIGN_LEFT,  "AI Legal Document Assistant",
                        doc.leftMargin(), footY, 0);
                cb.setFontAndSize(bf, 7);
                cb.showTextAligned(Element.ALIGN_RIGHT,
                        "Page " + w.getPageNumber() + " | Not Legal Advice",
                        pageW - doc.rightMargin(), footY, 0);
                cb.endText();

                cb.saveState();
                cb.setColorStroke(DIVIDER);
                cb.setLineWidth(0.5f);
                cb.moveTo(doc.leftMargin(),        footY + 10);
                cb.lineTo(pageW - doc.rightMargin(), footY + 10);
                cb.stroke();
                cb.restoreState();
            } catch (Exception e) {
                // Silently skip footer
            }
        }
    }
}
