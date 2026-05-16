package com.clarent.domain.meeting;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "transcript_segments")
public class TranscriptSegment {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "meeting_id", nullable = false)
    private MeetingSession meeting;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String text;

    @Column(length = 40)
    private String language;

    @Column(length = 80)
    private String speaker;

    private Instant startedAt;

    private Instant endedAt;

    @Column(nullable = false)
    private Instant receivedAt = Instant.now();

    protected TranscriptSegment() {
    }

    public TranscriptSegment(
            MeetingSession meeting,
            String text,
            String language,
            String speaker,
            Instant startedAt,
            Instant endedAt
    ) {
        this.meeting = meeting;
        this.text = text;
        this.language = language;
        this.speaker = speaker;
        this.startedAt = startedAt;
        this.endedAt = endedAt;
    }

    public UUID getId() {
        return id;
    }

    public MeetingSession getMeeting() {
        return meeting;
    }

    public String getText() {
        return text;
    }

    public String getLanguage() {
        return language;
    }

    public String getSpeaker() {
        return speaker;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public Instant getEndedAt() {
        return endedAt;
    }

    public Instant getReceivedAt() {
        return receivedAt;
    }
}
