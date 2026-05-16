package com.clarent.service;

import com.clarent.domain.meeting.MeetingSession;
import com.clarent.domain.meeting.MeetingStatus;
import com.clarent.domain.meeting.TranscriptSegment;
import com.clarent.domain.user.AppUser;
import com.clarent.dto.meeting.BotTranscriptSegmentRequest;
import com.clarent.dto.meeting.ConnectMeetingRequest;
import com.clarent.dto.meeting.ConnectMeetingResponse;
import com.clarent.dto.meeting.MeetingStatusMessage;
import com.clarent.dto.meeting.TranscriptMessage;
import com.clarent.repository.MeetingSessionRepository;
import com.clarent.repository.TranscriptSegmentRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ResponseStatusException;

@Service
public class MeetingAssistantService {
    private final MeetingSessionRepository meetingSessionRepository;
    private final TranscriptSegmentRepository transcriptSegmentRepository;
    private final BotProcessService botProcessService;
    private final SimpMessagingTemplate messagingTemplate;
    private final String botToken;

    public MeetingAssistantService(
            MeetingSessionRepository meetingSessionRepository,
            TranscriptSegmentRepository transcriptSegmentRepository,
            BotProcessService botProcessService,
            SimpMessagingTemplate messagingTemplate,
            @Value("${clarent.bot.token:dev-bot-token}") String botToken
    ) {
        this.meetingSessionRepository = meetingSessionRepository;
        this.transcriptSegmentRepository = transcriptSegmentRepository;
        this.botProcessService = botProcessService;
        this.messagingTemplate = messagingTemplate;
        this.botToken = botToken;
    }

    public ConnectMeetingResponse connect(ConnectMeetingRequest request, AppUser user) {
        MeetingSession session = new MeetingSession(
                request.platform(),
                request.inviteLink().trim(),
                user
        );
        MeetingSession saved = meetingSessionRepository.save(session);
        String message = botProcessService.start(saved);
        return ConnectMeetingResponse.from(saved, botProcessService.isAutoStart(), message);
    }

    @Transactional(readOnly = true)
    public List<TranscriptMessage> transcript(UUID meetingId, AppUser user) {
        MeetingSession session = meetingSessionRepository.findByIdAndCreatedById(meetingId, user.getId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Meeting session not found"));
        return transcriptSegmentRepository.findByMeetingIdOrderByReceivedAtAsc(session.getId())
                .stream()
                .map(TranscriptMessage::from)
                .toList();
    }

    @Transactional
    public TranscriptMessage receiveTranscriptSegment(
            UUID meetingId,
            BotTranscriptSegmentRequest request,
            String authorizationHeader
    ) {
        if (!matchesBotToken(authorizationHeader)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid bot token");
        }

        MeetingSession session = meetingSessionRepository.findById(meetingId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Meeting session not found"));

        if (session.getStatus() == MeetingStatus.CREATED
                || session.getStatus() == MeetingStatus.BOT_STARTING
                || session.getStatus() == MeetingStatus.BOT_JOINING) {
            session.setStatus(MeetingStatus.LIVE);
            meetingSessionRepository.save(session);
            messagingTemplate.convertAndSend(
                    "/topic/meetings/" + meetingId + "/status",
                    MeetingStatusMessage.now(meetingId, MeetingStatus.LIVE, "Clarent is live and streaming transcript.")
            );
        }

        TranscriptSegment segment = transcriptSegmentRepository.save(new TranscriptSegment(
                session,
                request.text().trim(),
                request.language(),
                request.startedAt(),
                request.endedAt()
        ));
        TranscriptMessage message = TranscriptMessage.from(segment);
        messagingTemplate.convertAndSend("/topic/meetings/" + meetingId + "/transcript", message);
        return message;
    }

    private boolean matchesBotToken(String authorizationHeader) {
        if (!StringUtils.hasText(authorizationHeader) || !authorizationHeader.startsWith("Bearer ")) {
            return false;
        }
        String receivedToken = authorizationHeader.substring(7);
        return botToken.equals(receivedToken);
    }
}
