package com.legal.document.repository;

import com.legal.document.entity.DocumentTemplateEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DocumentTemplateRepository extends JpaRepository<DocumentTemplateEntity, Long> {

    List<DocumentTemplateEntity> findByIssueTypeAndIsActive(String issueType, Boolean isActive);

    Optional<DocumentTemplateEntity> findByIssueTypeAndSubCategoryAndLanguageAndIsActive(
            String issueType, String subCategory, String language, Boolean isActive);

    Optional<DocumentTemplateEntity> findByIssueTypeAndLanguageAndIsActive(
            String issueType, String language, Boolean isActive);

    List<DocumentTemplateEntity> findByLanguageAndIsActive(String language, Boolean isActive);
}
