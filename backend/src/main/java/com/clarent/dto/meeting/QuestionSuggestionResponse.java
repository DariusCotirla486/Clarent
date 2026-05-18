package com.clarent.dto.meeting;

import com.clarent.domain.meeting.QuestionSuggestion;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;

public record QuestionSuggestionResponse(
        UUID id,
        UUID meetingId,
        UUID transcriptSegmentId,
        String transcriptText,
        String modelName,
        Instant createdAt,
        List<QuestionItemResponse> questions
) {
    public static QuestionSuggestionResponse from(QuestionSuggestion suggestion) {
        return new QuestionSuggestionResponse(
                suggestion.getId(),
                suggestion.getMeeting().getId(),
                suggestion.getTranscriptSegment().getId(),
                suggestion.getTranscriptText(),
                suggestion.getModelName(),
                suggestion.getCreatedAt(),
                suggestion.getQuestions()
                        .stream()
                        .sorted(Comparator.comparingInt(question -> question.getDisplayOrder()))
                        .map(QuestionItemResponse::from)
                        .toList()
        );
    }
}
