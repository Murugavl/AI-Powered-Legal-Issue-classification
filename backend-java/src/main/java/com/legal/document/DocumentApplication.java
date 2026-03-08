package com.legal.document;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DocumentApplication {

    public static void main(String[] args) {
        System.out.println("Starting Legal Document Backend...");
        SpringApplication.run(DocumentApplication.class, args);
    }

}
