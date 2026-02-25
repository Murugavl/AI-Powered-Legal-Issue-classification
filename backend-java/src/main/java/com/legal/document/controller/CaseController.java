package com.legal.document.controller;

import com.legal.document.dto.CaseResponse;
import com.legal.document.dto.CreateCaseRequest;
import com.legal.document.service.CaseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/cases")
@CrossOrigin(origins = "*")
public class CaseController {

    @Autowired
    private CaseService caseService;

    @PostMapping("/create")
    public ResponseEntity<CaseResponse> createCase(@RequestBody CreateCaseRequest request) {
        try {
            String phoneNumber = getCurrentUserPhoneNumber();
            CaseResponse response = caseService.createCase(request, phoneNumber);
            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @GetMapping("/{caseId}")
    public ResponseEntity<CaseResponse> getCaseById(@PathVariable("caseId") Long caseId) {
        try {
            String phoneNumber = getCurrentUserPhoneNumber();
            CaseResponse response = caseService.getCaseById(caseId, phoneNumber);
            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @GetMapping("/my-cases")
    public ResponseEntity<List<CaseResponse>> getMyCases() {
        try {
            String phoneNumber = getCurrentUserPhoneNumber();
            List<CaseResponse> cases = caseService.getUserCases(phoneNumber);
            return ResponseEntity.ok(cases);
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @PostMapping("/{caseId}/confirm-entity")
    public ResponseEntity<Void> confirmEntity(
            @PathVariable("caseId") Long caseId,
            @RequestBody Map<String, String> payload) {
        try {
            String phoneNumber = getCurrentUserPhoneNumber();
            String fieldName = payload.get("fieldName");
            caseService.confirmEntity(caseId, fieldName, phoneNumber);
            return ResponseEntity.ok().build();
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @DeleteMapping("/{caseId}")
    public ResponseEntity<?> deleteCase(@PathVariable("caseId") Long caseId) {
        try {
            String phoneNumber = getCurrentUserPhoneNumber();
            caseService.deleteCase(caseId, phoneNumber);
            return ResponseEntity.ok().build();
        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.badRequest().body("Failed to delete case: " + e.getMessage());
        }
    }

    private String getCurrentUserPhoneNumber() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || authentication.getPrincipal() == null) {
            throw new RuntimeException("User not authenticated");
        }
        return authentication.getPrincipal().toString();
    }
}
