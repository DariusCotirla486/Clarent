package com.clarent.repository;

import com.clarent.domain.meeting.QuestionItem;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuestionItemRepository extends JpaRepository<QuestionItem, UUID> {
    List<QuestionItem> findBySuggestion_Meeting_IdAndAskedTrueOrderByAskedAtAsc(UUID meetingId);

    Optional<QuestionItem> findByIdAndSuggestion_Meeting_Id(UUID id, UUID meetingId);
}
