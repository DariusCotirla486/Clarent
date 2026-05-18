package com.clarent.dto.meeting;

import com.clarent.domain.meeting.QuestionItem;
import java.time.Instant;
import java.util.UUID;

public record QuestionItemResponse(
        UUID id,
        String text,
        int displayOrder,
        boolean asked,
        Instant askedAt
) {
    public static QuestionItemResponse from(QuestionItem question) {
        return new QuestionItemResponse(
                question.getId(),
                question.getQuestionText(),
                question.getDisplayOrder(),
                question.isAsked(),
                question.getAskedAt()
        );
    }
}
