package com.legal.document.repository;

import com.legal.document.entity.CaseAnswer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface CaseAnswerRepository extends JpaRepository<CaseAnswer, Long> {
    List<CaseAnswer> findBySession_SessionIdOrderByCreatedAtAsc(String sessionId);
}
