package com.clarent.domain.team;

import com.clarent.domain.user.AppUser;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "teams")
public class Team {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 160)
    private String name;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "manager_id", nullable = false, unique = true)
    private AppUser manager;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    protected Team() {
    }

    public Team(String name, AppUser manager) {
        this.name = name;
        this.manager = manager;
    }

    public UUID getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public AppUser getManager() {
        return manager;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
