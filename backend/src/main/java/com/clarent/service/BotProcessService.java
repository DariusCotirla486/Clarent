package com.clarent.service;

import com.clarent.domain.meeting.MeetingPlatform;
import com.clarent.domain.meeting.MeetingSession;
import com.clarent.domain.meeting.MeetingStatus;
import com.clarent.dto.meeting.MeetingStatusMessage;
import com.clarent.repository.MeetingSessionRepository;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class BotProcessService {
    private final MeetingSessionRepository meetingSessionRepository;
    private final SimpMessagingTemplate messagingTemplate;
    private final boolean autoStart;
    private final String workdir;
    private final String python;
    private final String script;
    private final String botToken;
    private final String audioBackend;
    private final String audioDevice;
    private final String modelSize;
    private final String asrDevice;
    private final String computeType;
    private final String task;
    private final boolean showBrowser;

    public BotProcessService(
            MeetingSessionRepository meetingSessionRepository,
            SimpMessagingTemplate messagingTemplate,
            @Value("${clarent.bot.auto-start:true}") boolean autoStart,
            @Value("${clarent.bot.workdir:..}") String workdir,
            @Value("${clarent.bot.python:python}") String python,
            @Value("${clarent.bot.script:clarent_meeting_listener_bot.py}") String script,
            @Value("${clarent.bot.token:dev-bot-token}") String botToken,
            @Value("${clarent.bot.audio-backend:soundcard-loopback}") String audioBackend,
            @Value("${clarent.bot.audio-device:}") String audioDevice,
            @Value("${clarent.bot.model-size:small}") String modelSize,
            @Value("${clarent.bot.asr-device:auto}") String asrDevice,
            @Value("${clarent.bot.compute-type:int8_float16}") String computeType,
            @Value("${clarent.bot.task:translate}") String task,
            @Value("${clarent.bot.show-browser:false}") boolean showBrowser
    ) {
        this.meetingSessionRepository = meetingSessionRepository;
        this.messagingTemplate = messagingTemplate;
        this.autoStart = autoStart;
        this.workdir = workdir;
        this.python = python;
        this.script = script;
        this.botToken = botToken;
        this.audioBackend = audioBackend;
        this.audioDevice = audioDevice;
        this.modelSize = modelSize;
        this.asrDevice = asrDevice;
        this.computeType = computeType;
        this.task = task;
        this.showBrowser = showBrowser;
    }

    public boolean isAutoStart() {
        return autoStart;
    }

    public String start(MeetingSession session) {
        if (!autoStart) {
            String message = "Bot auto-start is disabled. Enable CLARENT_BOT_AUTO_START or run the Python listener manually.";
            publishStatus(session.getId(), session.getStatus(), message);
            return message;
        }

        session.setStatus(MeetingStatus.BOT_STARTING);
        meetingSessionRepository.save(session);
        publishStatus(session.getId(), session.getStatus(), "Starting Clarent meeting bot.");

        try {
            Path workingDirectory = Path.of(workdir).toAbsolutePath().normalize();
            Path logsDirectory = workingDirectory.resolve("logs");
            Files.createDirectories(logsDirectory);
            Path logFile = logsDirectory.resolve("bot-" + session.getId() + ".log");

            List<String> command = commandFor(session);
            ProcessBuilder processBuilder = new ProcessBuilder(command);
            processBuilder.directory(workingDirectory.toFile());
            processBuilder.redirectErrorStream(true);
            processBuilder.redirectOutput(ProcessBuilder.Redirect.appendTo(logFile.toFile()));
            Process process = processBuilder.start();

            session.setStatus(MeetingStatus.BOT_JOINING);
            meetingSessionRepository.save(session);
            publishStatus(
                    session.getId(),
                    session.getStatus(),
                    "Clarent bot launched. If the meeting has a lobby, admit it from the host app."
            );
            watchProcess(session.getId(), process);
            return "Clarent bot launched. Logs: " + logFile;
        } catch (IOException exception) {
            session.setStatus(MeetingStatus.FAILED);
            meetingSessionRepository.save(session);
            publishStatus(session.getId(), session.getStatus(), "Could not start Clarent bot: " + exception.getMessage());
            throw new IllegalStateException("Could not start Clarent bot: " + exception.getMessage(), exception);
        }
    }

    private List<String> commandFor(MeetingSession session) {
        List<String> command = new ArrayList<>();
        command.add(python);
        command.add(script);
        command.add("--meeting-url");
        command.add(session.getInviteLink());
        command.add("--platform");
        command.add(toBotPlatform(session.getPlatform()));
        command.add("--display-name");
        command.add("Clarent Bot");
        command.add("--start-minimized");
        if (showBrowser) {
            command.add("--show-browser");
        }
        command.add("--audio-backend");
        command.add(audioBackend);
        if (StringUtils.hasText(audioDevice)) {
            command.add("--audio-device");
            command.add(audioDevice);
        }
        command.add("--chunk-seconds");
        command.add("6");
        command.add("--model-size");
        command.add(modelSize);
        command.add("--asr-device");
        command.add(asrDevice);
        command.add("--compute-type");
        command.add(computeType);
        command.add("--task");
        command.add(task);
        command.add("--meeting-id");
        command.add(session.getId().toString());
        command.add("--api-url");
        command.add("http://localhost:8080/api/bot/meetings/" + session.getId() + "/transcript");
        command.add("--api-token");
        command.add(botToken);
        return command;
    }

    private String toBotPlatform(MeetingPlatform platform) {
        return switch (platform) {
            case GOOGLE_MEET -> "google-meet";
            case TEAMS -> "teams";
            case ZOOM -> "zoom";
        };
    }

    private void watchProcess(UUID meetingId, Process process) {
        CompletableFuture.runAsync(() -> {
            try {
                int exitCode = process.waitFor();
                meetingSessionRepository.findById(meetingId).ifPresent(session -> {
                    if (session.getStatus() == MeetingStatus.LIVE || session.getStatus() == MeetingStatus.BOT_JOINING) {
                        MeetingStatus nextStatus = exitCode == 0 ? MeetingStatus.ENDED : MeetingStatus.FAILED;
                        session.setStatus(nextStatus);
                        meetingSessionRepository.save(session);
                        publishStatus(
                                meetingId,
                                nextStatus,
                                exitCode == 0 ? "Meeting bot stopped." : "Meeting bot stopped with exit code " + exitCode + "."
                        );
                    }
                });
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
                meetingSessionRepository.findById(meetingId).ifPresent(session -> {
                    session.setStatus(MeetingStatus.FAILED);
                    meetingSessionRepository.save(session);
                    publishStatus(meetingId, MeetingStatus.FAILED, "Meeting bot watcher was interrupted.");
                });
            }
        });
    }

    private void publishStatus(UUID meetingId, MeetingStatus status, String message) {
        messagingTemplate.convertAndSend(
                "/topic/meetings/" + meetingId + "/status",
                MeetingStatusMessage.now(meetingId, status, message)
        );
    }
}
