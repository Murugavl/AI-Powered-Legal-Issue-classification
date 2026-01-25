package com.legal.document.service;

import com.legal.document.dto.CaseResponse;
import com.legal.document.dto.CreateCaseRequest;
import com.legal.document.entity.CaseEntity;
import com.legal.document.entity.LegalCase;
import com.legal.document.entity.User;
import com.legal.document.repository.CaseEntityRepository;
import com.legal.document.repository.LegalCaseRepository;
import com.legal.document.repository.UserRepository;
import com.legal.document.util.ReferenceNumberGenerator;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.Optional;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class CaseService {

    @Autowired
    private LegalCaseRepository legalCaseRepository;

    @Autowired
    private CaseEntityRepository caseEntityRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private ReferenceNumberGenerator referenceNumberGenerator;

    @Transactional
    public CaseResponse createCase(CreateCaseRequest request, String phoneNumber) {
        // Find user
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        // Create legal case
        LegalCase legalCase = new LegalCase();
        legalCase.setUser(user);
        legalCase.setReferenceNumber(referenceNumberGenerator.generate());
        legalCase.setIssueType(request.getIssueType());
        legalCase.setSubCategory(request.getSubCategory());
        legalCase.setStatus("draft");

        LegalCase savedCase = legalCaseRepository.save(legalCase);

        // Save entities
        if (request.getEntities() != null) {
            for (Map.Entry<String, Object> entry : request.getEntities().entrySet()) {
                CaseEntity entity = new CaseEntity();
                entity.setLegalCase(savedCase);
                entity.setFieldName(entry.getKey());
                entity.setFieldValue(entry.getValue() != null ? entry.getValue().toString() : null);
                entity.setIsConfirmed(false);
                entity.setExtractedBy("nlp");
                caseEntityRepository.save(entity);
            }
        }

        return buildCaseResponse(savedCase);
    }

    public CaseResponse getCaseById(Long caseId, String phoneNumber) {
        LegalCase legalCase = legalCaseRepository.findById(caseId)
                .orElseThrow(() -> new RuntimeException("Case not found"));

        // Verify user owns this case
        if (!legalCase.getUser().getPhoneNumber().equals(phoneNumber)) {
            throw new RuntimeException("Unauthorized access");
        }

        return buildCaseResponse(legalCase);
    }

    public List<CaseResponse> getUserCases(String phoneNumber) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new RuntimeException("User not found"));

        List<LegalCase> cases = legalCaseRepository.findByUserOrderByCreatedAtDesc(user);
        return cases.stream().map(this::buildCaseResponse).toList();
    }

    @Transactional
    public void confirmEntity(Long caseId, String fieldName, String phoneNumber) {
        LegalCase legalCase = legalCaseRepository.findById(caseId)
                .orElseThrow(() -> new RuntimeException("Case not found"));

        if (!legalCase.getUser().getPhoneNumber().equals(phoneNumber)) {
            throw new RuntimeException("Unauthorized access");
        }

        CaseEntity entity = caseEntityRepository.findByLegalCaseAndFieldName(legalCase, fieldName)
                .orElseThrow(() -> new RuntimeException("Entity not found"));

        entity.setIsConfirmed(true);
        caseEntityRepository.save(entity);
    }

    private CaseResponse buildCaseResponse(LegalCase legalCase) {
        List<CaseEntity> entities = caseEntityRepository.findByLegalCase(legalCase);

        Map<String, CaseResponse.EntityInfo> entityMap = new HashMap<>();
        for (CaseEntity entity : entities) {
            entityMap.put(entity.getFieldName(), new CaseResponse.EntityInfo(
                    entity.getFieldValue(),
                    entity.getIsConfirmed(),
                    entity.getConfidenceScore() != null ? entity.getConfidenceScore().doubleValue() : null));
        }

        long totalEntities = entities.size();
        long confirmedEntities = caseEntityRepository.countByLegalCaseAndIsConfirmed(legalCase, true);
        double completeness = totalEntities > 0 ? (double) confirmedEntities / totalEntities : 0.0;

        CaseResponse response = new CaseResponse();
        response.setCaseId(legalCase.getCaseId());
        response.setReferenceNumber(legalCase.getReferenceNumber());
        response.setIssueType(legalCase.getIssueType());
        response.setSubCategory(legalCase.getSubCategory());
        response.setStatus(legalCase.getStatus());
        response.setSuggestedAuthority(legalCase.getSuggestedAuthority());
        response.setEntities(entityMap);
        response.setCompleteness(completeness);
        response.setCreatedAt(legalCase.getCreatedAt());
        response.setUpdatedAt(legalCase.getUpdatedAt());

        return response;
    }
}
