package com.clarent.dto.meeting;

import com.clarent.domain.meeting.MeetingPlatform;
import com.clarent.domain.meeting.MeetingSession;
import com.clarent.domain.meeting.MeetingStatus;
import java.util.UUID;

public record ConnectMeetingResponse(
        UUID meetingId,
        MeetingPlatform platform,
        MeetingStatus status,
        String transcriptTopic,
        String statusTopic,
        boolean botAutoStart,
        String message
) {
    public static ConnectMeetingResponse from(MeetingSession session, boolean botAutoStart, String message) {
        UUID meetingId = session.getId();
        return new ConnectMeetingResponse(
                meetingId,
                session.getPlatform(),
                session.getStatus(),
                "/topic/meetings/" + meetingId + "/transcript",
                "/topic/meetings/" + meetingId + "/status",
                botAutoStart,
                message
        );
    }
}
