package com.legal.document.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

public class AuthResponse {
    private String token;
    private String phoneNumber;
    private String fullName;
    private String preferredLanguage;

    public AuthResponse() {
    }

    public AuthResponse(String token, String phoneNumber, String fullName, String preferredLanguage) {
        this.token = token;
        this.phoneNumber = phoneNumber;
        this.fullName = fullName;
        this.preferredLanguage = preferredLanguage;
    }

    public String getToken() {
        return token;
    }

    public void setToken(String token) {
        this.token = token;
    }

    public String getPhoneNumber() {
        return phoneNumber;
    }

    public void setPhoneNumber(String phoneNumber) {
        this.phoneNumber = phoneNumber;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getPreferredLanguage() {
        return preferredLanguage;
    }

    public void setPreferredLanguage(String preferredLanguage) {
        this.preferredLanguage = preferredLanguage;
    }
}
