package com.legal.document.repository;

import com.legal.document.entity.LegalCase;
import com.legal.document.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface LegalCaseRepository extends JpaRepository<LegalCase, Long> {

    List<LegalCase> findByUser(User user);

    List<LegalCase> findByUserOrderByCreatedAtDesc(User user);

    Optional<LegalCase> findByReferenceNumber(String referenceNumber);

    List<LegalCase> findByStatus(String status);

    List<LegalCase> findByIssueType(String issueType);
}
