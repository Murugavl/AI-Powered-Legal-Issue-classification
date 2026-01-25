package com.legal.document.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.util.Map;

public class CreateCaseRequest {
    private String initialText;
    private String language;
    private Map<String, Object> entities;
    private String issueType;
    private String subCategory;

    public CreateCaseRequest() {
    }

    public CreateCaseRequest(String initialText, String language, Map<String, Object> entities, String issueType,
            String subCategory) {
        this.initialText = initialText;
        this.language = language;
        this.entities = entities;
        this.issueType = issueType;
        this.subCategory = subCategory;
    }

    public String getInitialText() {
        return initialText;
    }

    public void setInitialText(String initialText) {
        this.initialText = initialText;
    }

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }

    public Map<String, Object> getEntities() {
        return entities;
    }

    public void setEntities(Map<String, Object> entities) {
        this.entities = entities;
    }

    public String getIssueType() {
        return issueType;
    }

    public void setIssueType(String issueType) {
        this.issueType = issueType;
    }

    public String getSubCategory() {
        return subCategory;
    }

    public void setSubCategory(String subCategory) {
        this.subCategory = subCategory;
    }
}
