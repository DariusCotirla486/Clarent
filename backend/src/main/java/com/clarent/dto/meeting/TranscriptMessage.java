package com.clarent.dto.meeting;

import com.clarent.domain.meeting.TranscriptSegment;
import java.time.Instant;
import java.util.UUID;

public record TranscriptMessage(
        UUID id,
        UUID meetingId,
        String text,
        String language,
        String speaker,
        Instant startedAt,
        Instant endedAt,
        Instant receivedAt
) {
    public static TranscriptMessage from(TranscriptSegment segment) {
        return new TranscriptMessage(
                segment.getId(),
                segment.getMeeting().getId(),
                segment.getText(),
                segment.getLanguage(),
                segment.getSpeaker(),
                segment.getStartedAt(),
                segment.getEndedAt(),
                segment.getReceivedAt()
        );
    }
}
