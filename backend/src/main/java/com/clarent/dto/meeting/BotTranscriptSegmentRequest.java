package com.clarent.dto.meeting;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import java.time.Instant;

public record BotTranscriptSegmentRequest(
        @JsonProperty("started_at") Instant startedAt,
        @JsonProperty("ended_at") Instant endedAt,
        @JsonProperty("duration_seconds") Double durationSeconds,
        @NotBlank String text,
        String language,
        @JsonProperty("meeting_id") String meetingId,
        String task
) {
}
