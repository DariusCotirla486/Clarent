package com.clarent.dto.team;

import com.clarent.domain.team.TeamDocument;
import java.time.Instant;
import java.util.UUID;

public record TeamDocumentResponse(
        UUID documentId,
        String fileName,
        String contentType,
        long sizeBytes,
        Instant updatedAt,
        String updatedByName
) {
    public static TeamDocumentResponse from(TeamDocument document) {
        return new TeamDocumentResponse(
                document.getId(),
                document.getFileName(),
                document.getContentType(),
                document.getSizeBytes(),
                document.getUpdatedAt(),
                document.getUpdatedBy() == null ? null : document.getUpdatedBy().getFullName()
        );
    }
}
