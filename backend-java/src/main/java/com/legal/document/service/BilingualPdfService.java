package com.legal.document.service;

import com.lowagie.text.*;
import com.lowagie.text.pdf.*;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class BilingualPdfService {

    private static final Color INK        = new Color(15,  23,  42);
    private static final Color SLATE      = new Color(100, 116, 139);
    private static final Color DIVIDER    = new Color(203, 213, 225);
    private static final Color BLUE_BOLD  = new Color(30,  64,  175);
    private static final Color RED_DARK   = new Color(153, 27,  27);
    private static final Color RED_LITE   = new Color(254, 242, 242);
    private static final Color NAVY       = new Color(15,  23,  42);
    private static final Color BADGE_BLUE = new Color(37,  99,  235);

    private static final float ML = 72;
    private static final float MR = 72;
    private static final float MT = 72;
    private static final float MB = 72;

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
            PdfWriter writer = PdfWriter.getInstance(doc, out);
            boolean engOnly  = "en".equalsIgnoreCase(userLanguage);
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
    // RENDER ONE LETTER
    // ─────────────────────────────────────────────────────────────────────────
    private void renderLetter(Document doc, String content, String lang)
            throws DocumentException {
        if (content == null || content.isBlank()) {
            doc.add(new Paragraph("[No content]", f(lang, 9, Font.NORMAL, SLATE)));
            return;
        }

        Font fBody  = f(lang, 10, Font.NORMAL, INK);
        Font fBold  = f(lang, 10, Font.BOLD,   INK);
        Font fSubj  = f(lang, 10, Font.BOLD,   BLUE_BOLD);
        Font fMeta  = f(lang,  9, Font.NORMAL, SLATE);
        Font fLabel = f(lang, 10, Font.BOLD,   INK);

        String[]      lines            = content.split("\\n", -1);
        boolean       pastSalutation   = false;
        boolean       inSignatureBlock = false;
        boolean       inDisclaimer     = false;
        StringBuilder proseBuf         = new StringBuilder();

        for (String raw : lines) {
            String line = raw.trim();

            if (isOldFormatHeading(line)) continue;

            // Blank lines
            if (line.isEmpty()) {
                if (!pastSalutation) {
                    doc.add(gap(4));
                } else {
                    flushProse(doc, proseBuf, fBody);
                }
                continue;
            }

            // Ref No:
            if (line.startsWith("Ref No:")) {
                flushProse(doc, proseBuf, fBody);
                Paragraph p = new Paragraph();
                p.add(new Chunk("Ref No: ", fLabel));
                p.add(new Chunk(line.substring("Ref No:".length()).trim(), fMeta));
                p.setSpacingAfter(1);
                doc.add(p);
                continue;
            }

            // Date:
            if (line.startsWith("Date:")) {
                flushProse(doc, proseBuf, fBody);
                Paragraph p = new Paragraph();
                p.add(new Chunk("Date: ", fLabel));
                p.add(new Chunk(line.substring("Date:".length()).trim(),
                        inSignatureBlock ? fBody : fMeta));
                p.setSpacingAfter(inSignatureBlock ? 2 : 1);
                doc.add(p);
                continue;
            }

            // From / From:
            if (line.equals("From") || line.equals("From:")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(gap(2));
                Paragraph p = new Paragraph("From", fBold);
                p.setSpacingAfter(1);
                doc.add(p);
                continue;
            }

            // To / To:
            if (line.equals("To") || line.equals("To:")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(gap(4));
                Paragraph p = new Paragraph("To", fBold);
                p.setSpacingAfter(1);
                doc.add(p);
                continue;
            }

            // Sub:
            if (line.startsWith("Sub:")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(gap(4));
                String subText = line.substring("Sub:".length()).trim();
                Paragraph p = new Paragraph();
                p.add(new Chunk("Sub: ", fSubj));
                p.add(new Chunk(subText, fBold));
                p.setSpacingAfter(4);
                doc.add(p);
                continue;
            }

            // Salutation — rendered BOLD for emphasis
            if (isSalutation(line)) {
                flushProse(doc, proseBuf, fBody);
                doc.add(gap(2));
                Paragraph p = new Paragraph(line, fBold);
                p.setSpacingAfter(6);
                doc.add(p);
                pastSalutation   = true;
                inSignatureBlock = false;
                continue;
            }

            // Section headings: evidence list, enclosures, legal provisions
            if (line.startsWith("Relevant documents attached")
                    || line.startsWith("Enclosures:")
                    || line.startsWith("Applicable Legal Provisions")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(gap(6));
                Paragraph p = new Paragraph(line, fBold);
                p.setSpacingAfter(3);
                doc.add(p);
                continue;
            }

            // Bullet point lines (• text) — clean indented items
            if (line.startsWith("\u2022") || line.startsWith("  \u2022")) {
                flushProse(doc, proseBuf, fBody);
                String itemText = line.replaceFirst("^\\s*\\u2022\\s*", "").trim();
                Paragraph p = new Paragraph();
                p.add(new Chunk("\u2022  ", fLabel));   // bullet in bold label font
                p.add(new Chunk(itemText, fBody));
                p.setIndentationLeft(14);
                p.setFirstLineIndent(-8);
                p.setSpacingAfter(1);
                doc.add(p);
                continue;
            }

            // Legacy numbered list items (fallback)
            if (line.matches("^\\d+\\.\\s+.+")) {
                flushProse(doc, proseBuf, fBody);
                String itemText = line.replaceFirst("^\\d+\\.\\s*", "").trim();
                Paragraph p = new Paragraph();
                p.add(new Chunk("\u2022  ", fLabel));
                p.add(new Chunk(itemText, fBody));
                p.setIndentationLeft(14);
                p.setFirstLineIndent(-8);
                p.setSpacingAfter(1);
                doc.add(p);
                continue;
            }

            // Closing: "Thank You," or "Yours faithfully,"
            if (line.startsWith("Thank You") || line.startsWith("Thanking you")
                    || line.startsWith("Yours faithfully") || line.startsWith("Yours sincerely")
                    || line.startsWith("\u0ba8\u0ba9\u0bcd\u0bb1\u0bbf") || line.startsWith("\u0927\u0928\u094d\u092f\u0935\u093e\u0926")
                    || line.startsWith("\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b89\u0ba3\u0bcd\u0bae\u0bc8\u0baf\u0bc1\u0bb3\u0bcd\u0bb3")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(gap(6));
                Paragraph p = new Paragraph(line, fBody);
                p.setSpacingAfter(2);
                doc.add(p);
                inSignatureBlock = true;
                continue;
            }

            // Signature:
            if (line.startsWith("Signature:")) {
                flushProse(doc, proseBuf, fBody);
                doc.add(gap(6));
                doc.add(new Paragraph(line, fBody));
                inSignatureBlock = true;
                continue;
            }

            // Underline / (Signature) marker
            if (line.startsWith("___") || line.equals("(Signature)")) {
                Paragraph p = new Paragraph(line, fBody);
                p.setSpacingAfter(2);
                doc.add(p);
                continue;
            }

            // Labelled signature fields: Name:, Contact:, Place:
            if (inSignatureBlock && (line.startsWith("Name:")
                    || line.startsWith("Contact:") || line.startsWith("Place:"))) {
                String[] kv = line.split(":", 2);
                Paragraph p = new Paragraph();
                p.add(new Chunk(kv[0] + ": ", fLabel));
                p.add(new Chunk(kv.length > 1 ? kv[1].trim() : "", fBody));
                p.setSpacingAfter(2);
                doc.add(p);
                continue;
            }

            // DISCLAIMER heading — adds a clear visual separator before the box
            if (line.toUpperCase().startsWith("DISCLAIMER")) {
                flushProse(doc, proseBuf, fBody);
                inDisclaimer = true;
                beginDisclaimerBox(doc);
                continue;
            }

            // Disclaimer body text
            if (inDisclaimer) {
                finaliseDisclaimerBox(doc, line, lang);
                inDisclaimer = false;
                continue;
            }

            // Everything else
            if (!pastSalutation) {
                Paragraph p = new Paragraph(line, fBody);
                p.setSpacingAfter(1);
                doc.add(p);
            } else if (inSignatureBlock) {
                Paragraph p = new Paragraph(line, fBody);
                p.setSpacingAfter(2);
                doc.add(p);
            } else {
                if (proseBuf.length() > 0) proseBuf.append(" ");
                proseBuf.append(raw.trim());
            }
        }

        flushProse(doc, proseBuf, fBody);
        doc.add(gap(4));
    }

    // Prose flusher
    private void flushProse(Document doc, StringBuilder buf, Font font)
            throws DocumentException {
        String text = buf.toString().trim();
        if (!text.isEmpty()) {
            Paragraph p = new Paragraph(text, font);
            p.setAlignment(Element.ALIGN_JUSTIFIED);
            p.setLeading(15);
            p.setSpacingAfter(8);
            doc.add(p);
        }
        buf.setLength(0);
    }

    // Disclaimer — single red box with clear gap above
    private PdfPTable pendingDisclaimerTable = null;
    private PdfPCell  pendingDisclaimerCell  = null;

    private void beginDisclaimerBox(Document doc) throws DocumentException {
        // Horizontal rule separator
        PdfPTable rule = new PdfPTable(1);
        rule.setWidthPercentage(100);
        rule.setSpacingBefore(18);   // <— clear gap above disclaimer
        rule.setSpacingAfter(6);
        PdfPCell rc = new PdfPCell(new Phrase(" "));
        rc.setBorder(Rectangle.BOTTOM);
        rc.setBorderColorBottom(DIVIDER);
        rc.setBorderWidthBottom(0.5f);
        rc.setPaddingBottom(0);
        rule.addCell(rc);
        doc.add(rule);

        pendingDisclaimerTable = new PdfPTable(1);
        pendingDisclaimerTable.setWidthPercentage(100);
        pendingDisclaimerCell = new PdfPCell();
        pendingDisclaimerCell.setBackgroundColor(RED_LITE);
        pendingDisclaimerCell.setBorderColor(new Color(252, 165, 165));
        pendingDisclaimerCell.setBorderWidth(0.8f);
        pendingDisclaimerCell.setPadding(10);

        Font fHdr = new Font(Font.HELVETICA, 8, Font.BOLD, RED_DARK);
        Paragraph hdr = new Paragraph("DISCLAIMER — NOT LEGAL ADVICE", fHdr);
        hdr.setSpacingAfter(4);
        pendingDisclaimerCell.addElement(hdr);
    }

    private void finaliseDisclaimerBox(Document doc, String text, String lang)
            throws DocumentException {
        if (pendingDisclaimerCell == null) return;
        Font fBody = new Font(unicodeFontFor(lang), 8, Font.NORMAL, RED_DARK);
        Paragraph body = new Paragraph(text, fBody);
        body.setLeading(12);
        pendingDisclaimerCell.addElement(body);
        pendingDisclaimerTable.addCell(pendingDisclaimerCell);
        doc.add(pendingDisclaimerTable);
        pendingDisclaimerTable = null;
        pendingDisclaimerCell  = null;
    }

    // Helpers
    private static boolean isOldFormatHeading(String line) {
        if (line.length() < 3 || line.length() > 60) return false;
        if (line.matches("[-=]{4,}.*")) return true;
        if (line.equals(line.toUpperCase()) && line.matches("[A-Z][A-Z /\\-]{5,}")) {
            if (line.startsWith("DISCLAIMER")) return false;
            return true;
        }
        return false;
    }

    private static boolean isSalutation(String line) {
        return line.startsWith("Respected Sir/Madam")
            || line.startsWith("Respected Sir")
            || line.startsWith("Respected Madam")
            || line.startsWith("Dear ")
            || line.startsWith("\u0bae\u0ba4\u0bbf\u0baa\u0bcd\u0baa\u0bbf\u0bb1\u0bcd\u0b95\u0bc1\u0bb0\u0bbf\u0baf")
            || line.startsWith("\u0b85\u0ba9\u0bcd\u0baa\u0bc1\u0bb3\u0bcd\u0bb3")
            || line.startsWith("\u0906\u0926\u0930\u0923\u0940\u092f")
            || line.startsWith("\u092a\u094d\u0930\u093f\u092f ");
    }

    private Paragraph gap(float pts) {
        Paragraph p = new Paragraph(" ");
        p.setLeading(pts);
        p.setSpacingAfter(0);
        return p;
    }

    // Page decorator (no header/footer — kept minimal)
    private static class PageDecorator extends PdfPageEventHelper {
        private final PdfWriter           writer;
        private final Map<String, Object> metadata;
        private       String              currentLang;
        private       boolean             isEnglishCopy;

        PageDecorator(PdfWriter w, Map<String, Object> meta, String lang, boolean engOnly) {
            this.writer        = w;
            this.metadata      = meta;
            this.currentLang   = lang;
            this.isEnglishCopy = engOnly;
        }

        void setMode(String lang, boolean englishCopy) {
            this.currentLang   = lang;
            this.isEnglishCopy = englishCopy;
        }

        @Override public void onStartPage(PdfWriter w, Document doc) {}
        @Override public void onEndPage(PdfWriter w, Document doc) {}
    }
}
