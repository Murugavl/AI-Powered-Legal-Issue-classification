package com.legal.document.service.templates;

import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import java.util.Map;

public interface DocumentTemplate {
    boolean supports(String documentType);

    void buildDocument(Document document, Map<String, String> data) throws DocumentException;
}
