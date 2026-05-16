package com.clarent.repository;

import com.clarent.domain.meeting.MeetingSession;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MeetingSessionRepository extends JpaRepository<MeetingSession, UUID> {
    Optional<MeetingSession> findByIdAndCreatedById(UUID id, UUID createdById);
}
