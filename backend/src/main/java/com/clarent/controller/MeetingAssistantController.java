package com.clarent.controller;

import com.clarent.domain.user.AppUser;
import com.clarent.dto.meeting.ConnectMeetingRequest;
import com.clarent.dto.meeting.ConnectMeetingResponse;
import com.clarent.dto.meeting.TranscriptMessage;
import com.clarent.service.MeetingAssistantService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/manager/meeting-assistant")
public class MeetingAssistantController {
    private final MeetingAssistantService meetingAssistantService;

    public MeetingAssistantController(MeetingAssistantService meetingAssistantService) {
        this.meetingAssistantService = meetingAssistantService;
    }

    @PostMapping("/connect")
    public ConnectMeetingResponse connect(
            @Valid @RequestBody ConnectMeetingRequest request,
            @AuthenticationPrincipal AppUser user
    ) {
        return meetingAssistantService.connect(request, user);
    }

    @GetMapping("/{meetingId}/transcript")
    public List<TranscriptMessage> transcript(
            @PathVariable UUID meetingId,
            @AuthenticationPrincipal AppUser user
    ) {
        return meetingAssistantService.transcript(meetingId, user);
    }
}
