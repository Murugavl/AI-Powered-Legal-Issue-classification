package com.legal.document.repository;

import com.legal.document.entity.DBFile;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DBFileRepository extends JpaRepository<DBFile, Long> {
    List<DBFile> findBySession_SessionId(String sessionId);
}
