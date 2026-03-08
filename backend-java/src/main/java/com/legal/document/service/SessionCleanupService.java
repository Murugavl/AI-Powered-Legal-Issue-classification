package com.legal.document.service;

import com.legal.document.entity.CaseSession;
import com.legal.document.repository.CaseAnswerRepository;
import com.legal.document.repository.CaseSessionRepository;
import com.legal.document.repository.DBFileRepository;
import com.legal.document.repository.ExtractedEntityRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * SessionCleanupService
 *
 * Per the Satta Vizhi operating specification:
 * "Session data may be retained securely for up to seven days only..."
 *
 * This scheduler runs daily at 02:00 AM and permanently deletes all case
 * sessions (along with all related answers, entities, and files) that were
 * created more than 7 days ago.
 */
@Service
public class SessionCleanupService {

    private static final Logger log = LoggerFactory.getLogger(SessionCleanupService.class);

    @Autowired
    private CaseSessionRepository sessionRepository;
    @Autowired
    private CaseAnswerRepository answerRepository;
    @Autowired
    private ExtractedEntityRepository entityRepository;
    @Autowired
    private DBFileRepository dbFileRepository;

    /**
     * Runs every day at 02:00 AM (server local time).
     * Cron: second minute hour day month weekday
     */
    @Scheduled(cron = "0 0 2 * * *")
    @Transactional
    public void purgeExpiredSessions() {
        LocalDateTime cutoff = LocalDateTime.now().minusDays(7);
        List<CaseSession> expired = sessionRepository.findByCreatedAtBefore(cutoff);

        if (expired.isEmpty()) {
            log.info("[SessionCleanup] No expired sessions to purge.");
            return;
        }

        log.info("[SessionCleanup] Purging {} session(s) older than 7 days...", expired.size());

        for (CaseSession session : expired) {
            String sid = session.getSessionId();
            try {
                // Delete child records first (FK constraints)
                entityRepository.deleteAll(entityRepository.findBySession_SessionId(sid));
                answerRepository.deleteAll(answerRepository.findBySession_SessionIdOrderByCreatedAtAsc(sid));
                dbFileRepository.deleteAll(dbFileRepository.findBySession_SessionId(sid));
                sessionRepository.delete(session);
                log.info("[SessionCleanup] Deleted session {} (created {})", sid, session.getCreatedAt());
            } catch (Exception e) {
                log.error("[SessionCleanup] Failed to delete session {}: {}", sid, e.getMessage());
            }
        }

        log.info("[SessionCleanup] Purge complete — {} session(s) deleted.", expired.size());
    }
}
