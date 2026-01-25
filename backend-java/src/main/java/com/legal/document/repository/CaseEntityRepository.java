package com.legal.document.repository;

import com.legal.document.entity.CaseEntity;
import com.legal.document.entity.LegalCase;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CaseEntityRepository extends JpaRepository<CaseEntity, Long> {

    List<CaseEntity> findByLegalCase(LegalCase legalCase);

    Optional<CaseEntity> findByLegalCaseAndFieldName(LegalCase legalCase, String fieldName);

    List<CaseEntity> findByLegalCaseAndIsConfirmed(LegalCase legalCase, Boolean isConfirmed);

    long countByLegalCaseAndIsConfirmed(LegalCase legalCase, Boolean isConfirmed);
}
