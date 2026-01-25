package com.legal.document.repository;

import com.legal.document.entity.CaseSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface CaseSessionRepository extends JpaRepository<CaseSession, String> {
    List<CaseSession> findByUser_UserIdOrderByUpdatedAtDesc(Long userId);

    Optional<CaseSession> findBySessionIdAndUser_UserId(String sessionId, Long userId);
}
