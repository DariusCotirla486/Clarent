package com.clarent.dto.meeting;

import com.clarent.domain.meeting.MeetingPlatform;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record ConnectMeetingRequest(
        @NotNull MeetingPlatform platform,
        @NotBlank String inviteLink
) {
}
