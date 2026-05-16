package com.clarent.domain.meeting;

import com.clarent.domain.user.AppUser;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
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
@Table(name = "meeting_sessions")
public class MeetingSession {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 40)
    private MeetingPlatform platform;

    @Column(nullable = false, length = 1600)
    private String inviteLink;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 40)
    private MeetingStatus status = MeetingStatus.CREATED;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "created_by_id", nullable = false)
    private AppUser createdBy;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    protected MeetingSession() {
    }

    public MeetingSession(MeetingPlatform platform, String inviteLink, AppUser createdBy) {
        this.platform = platform;
        this.inviteLink = inviteLink;
        this.createdBy = createdBy;
    }

    public UUID getId() {
        return id;
    }

    public MeetingPlatform getPlatform() {
        return platform;
    }

    public String getInviteLink() {
        return inviteLink;
    }

    public MeetingStatus getStatus() {
        return status;
    }

    public AppUser getCreatedBy() {
        return createdBy;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setStatus(MeetingStatus status) {
        this.status = status;
    }
}
