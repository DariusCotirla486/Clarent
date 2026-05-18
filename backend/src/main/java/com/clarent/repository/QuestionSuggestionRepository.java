package com.clarent.repository;

import com.clarent.domain.meeting.QuestionSuggestion;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuestionSuggestionRepository extends JpaRepository<QuestionSuggestion, UUID> {
    List<QuestionSuggestion> findByMeetingIdOrderByCreatedAtDesc(UUID meetingId);
}
