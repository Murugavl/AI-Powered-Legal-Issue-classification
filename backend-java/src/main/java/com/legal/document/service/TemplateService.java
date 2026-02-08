package com.legal.document.service;

import com.legal.document.entity.DocumentTemplateEntity;
import com.legal.document.repository.DocumentTemplateRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class TemplateService {

    @Autowired
    private DocumentTemplateRepository templateRepository;

    /**
     * Get template based on issue type, subcategory, and language
     */
    public Optional<DocumentTemplateEntity> getTemplate(String issueType, String subCategory, String language) {
        // Try exact match first
        Optional<DocumentTemplateEntity> template = templateRepository
                .findByIssueTypeAndSubCategoryAndLanguageAndIsActive(issueType, subCategory, language, true);

        if (template.isPresent()) {
            return template;
        }

        // Fallback to issue type and language only
        return templateRepository.findByIssueTypeAndLanguageAndIsActive(issueType, language, true);
    }

    /**
     * Fill template with actual data
     */
    public String fillTemplate(String templateContent, Map<String, Object> facts) {
        if (templateContent == null || facts == null) {
            return templateContent;
        }

        String result = templateContent;

        // Replace all {{placeholder}} with actual values
        Pattern pattern = Pattern.compile("\\{\\{([^}]+)\\}\\}");
        Matcher matcher = pattern.matcher(templateContent);

        Map<String, String> replacements = new HashMap<>();

        while (matcher.find()) {
            String placeholder = matcher.group(1).trim();
            Object value = facts.get(placeholder);

            if (value != null) {
                replacements.put("{{" + placeholder + "}}", value.toString());
            } else {
                // If value not found, keep placeholder or use default
                replacements.put("{{" + placeholder + "}}", "[" + placeholder.toUpperCase() + "]");
            }
        }

        // Apply all replacements
        for (Map.Entry<String, String> entry : replacements.entrySet()) {
            result = result.replace(entry.getKey(), entry.getValue());
        }

        return result;
    }

    /**
     * Determine document type from intent
     */
    public String determineDocumentType(String intent) {
        if (intent == null) {
            return "general_petition";
        }

        String lowerIntent = intent.toLowerCase();

        if (lowerIntent.contains("theft") || lowerIntent.contains("stolen") ||
                lowerIntent.contains("robbery") || lowerIntent.contains("assault") ||
                lowerIntent.contains("harassment") || lowerIntent.contains("crime")) {
            return "police_complaint";
        }

        if (lowerIntent.contains("consumer") || lowerIntent.contains("product") ||
                lowerIntent.contains("service") || lowerIntent.contains("refund")) {
            return "consumer_complaint";
        }

        if (lowerIntent.contains("rti") || lowerIntent.contains("information") ||
                lowerIntent.contains("government") || lowerIntent.contains("public")) {
            return "rti_application";
        }

        if (lowerIntent.contains("landlord") || lowerIntent.contains("tenant") ||
                lowerIntent.contains("rent") || lowerIntent.contains("deposit") ||
                lowerIntent.contains("eviction")) {
            return "legal_notice";
        }

        if (lowerIntent.contains("divorce") || lowerIntent.contains("maintenance") ||
                lowerIntent.contains("custody")) {
            return "family_petition";
        }

        return "general_petition";
    }
}
