package com.legal.document.dto;

public class StartSessionRequest {
    private String initialText;
    private String language; // "en", "ta", etc.

    public StartSessionRequest() {
    }

    public StartSessionRequest(String initialText, String language) {
        this.initialText = initialText;
        this.language = language;
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
}
