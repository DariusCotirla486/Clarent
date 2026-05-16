package com.clarent.dto.meeting;

import com.clarent.domain.meeting.MeetingStatus;
import java.time.Instant;
import java.util.UUID;

public record MeetingStatusMessage(
        UUID meetingId,
        MeetingStatus status,
        String message,
        Instant changedAt
) {
    public static MeetingStatusMessage now(UUID meetingId, MeetingStatus status, String message) {
        return new MeetingStatusMessage(meetingId, status, message, Instant.now());
    }
}
