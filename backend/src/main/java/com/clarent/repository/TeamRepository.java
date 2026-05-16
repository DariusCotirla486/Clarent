package com.clarent.repository;

import com.clarent.domain.team.Team;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TeamRepository extends JpaRepository<Team, UUID> {
    Optional<Team> findByManager_Id(UUID managerId);
}
