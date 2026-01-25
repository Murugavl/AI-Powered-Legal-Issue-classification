package com.legal.document.repository;

import com.legal.document.entity.ExtractedEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface ExtractedEntityRepository extends JpaRepository<ExtractedEntity, Long> {
    List<ExtractedEntity> findBySession_SessionId(String sessionId);

    Optional<ExtractedEntity> findBySession_SessionIdAndEntityKey(String sessionId, String entityKey);
}
