package com.clarent.repository;

import com.clarent.domain.meeting.TranscriptSegment;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TranscriptSegmentRepository extends JpaRepository<TranscriptSegment, UUID> {
    List<TranscriptSegment> findByMeetingIdOrderByReceivedAtAsc(UUID meetingId);
}
