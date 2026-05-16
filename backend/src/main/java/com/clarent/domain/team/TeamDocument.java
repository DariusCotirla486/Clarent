package com.clarent.domain.team;

import com.clarent.domain.user.AppUser;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "team_documents")
public class TeamDocument {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "team_id", nullable = false, unique = true)
    private Team team;

    @Column(nullable = false, length = 255)
    private String fileName;

    @Column(nullable = false, length = 120)
    private String contentType;

    @Column(nullable = false)
    private long sizeBytes;

    @Column(nullable = false, columnDefinition = "BYTEA")
    private byte[] data;

    @Column(nullable = false)
    private Instant updatedAt = Instant.now();

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "updated_by_id")
    private AppUser updatedBy;

    protected TeamDocument() {
    }

    public TeamDocument(Team team) {
        this.team = team;
    }

    public UUID getId() {
        return id;
    }

    public Team getTeam() {
        return team;
    }

    public String getFileName() {
        return fileName;
    }

    public String getContentType() {
        return contentType;
    }

    public long getSizeBytes() {
        return sizeBytes;
    }

    public byte[] getData() {
        return data;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public AppUser getUpdatedBy() {
        return updatedBy;
    }

    public void replace(String fileName, String contentType, long sizeBytes, byte[] data, AppUser updatedBy) {
        this.fileName = fileName;
        this.contentType = contentType;
        this.sizeBytes = sizeBytes;
        this.data = data;
        this.updatedBy = updatedBy;
        this.updatedAt = Instant.now();
    }
}
