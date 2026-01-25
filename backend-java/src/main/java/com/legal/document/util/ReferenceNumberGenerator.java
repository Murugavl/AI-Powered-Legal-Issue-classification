package com.legal.document.util;

import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class ReferenceNumberGenerator {

    private static final AtomicLong counter = new AtomicLong(1);
    private static final DateTimeFormatter YEAR_FORMATTER = DateTimeFormatter.ofPattern("yyyy");

    public String generate() {
        String year = LocalDateTime.now().format(YEAR_FORMATTER);
        long sequence = counter.getAndIncrement();
        return String.format("LDA-%s-%06d", year, sequence);
    }
}
