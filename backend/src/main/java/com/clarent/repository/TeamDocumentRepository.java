package com.clarent.repository;

import com.clarent.domain.team.TeamDocument;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TeamDocumentRepository extends JpaRepository<TeamDocument, UUID> {
    Optional<TeamDocument> findByTeam_Id(UUID teamId);
}
