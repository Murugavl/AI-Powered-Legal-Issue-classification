package com.legal.document.repository;

import com.legal.document.entity.GeneratedDocument;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface GeneratedDocumentRepository extends JpaRepository<GeneratedDocument, Long> {
    List<GeneratedDocument> findBySession_SessionId(String sessionId);

    List<GeneratedDocument> findByLegalCase_CaseId(Long caseId);
}
