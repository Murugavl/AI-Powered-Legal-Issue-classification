package com.legal.document.dto;

public class SubmitAnswerRequest {
    private String answerText;

    public SubmitAnswerRequest() {
    }

    public SubmitAnswerRequest(String answerText) {
        this.answerText = answerText;
    }

    public String getAnswerText() {
        return answerText;
    }

    public void setAnswerText(String answerText) {
        this.answerText = answerText;
    }
}
