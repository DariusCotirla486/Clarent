package com.clarent.controller;

import com.clarent.dto.meeting.BotTranscriptSegmentRequest;
import com.clarent.dto.meeting.TranscriptMessage;
import com.clarent.service.MeetingAssistantService;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/bot/meetings")
public class BotTranscriptController {
    private final MeetingAssistantService meetingAssistantService;

    public BotTranscriptController(MeetingAssistantService meetingAssistantService) {
        this.meetingAssistantService = meetingAssistantService;
    }

    @PostMapping("/{meetingId}/transcript")
    @ResponseStatus(HttpStatus.ACCEPTED)
    public TranscriptMessage transcript(
            @PathVariable UUID meetingId,
            @Valid @RequestBody BotTranscriptSegmentRequest request,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorizationHeader
    ) {
        return meetingAssistantService.receiveTranscriptSegment(meetingId, request, authorizationHeader);
    }
}
