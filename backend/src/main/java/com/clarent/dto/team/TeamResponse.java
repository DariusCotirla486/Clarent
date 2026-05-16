package com.clarent.dto.team;

import java.util.List;
import java.util.UUID;

public record TeamResponse(
        UUID teamId,
        String teamName,
        UUID managerId,
        String managerName,
        List<TeamMemberResponse> members,
        TeamDocumentResponse document
) {
    public static TeamResponse empty() {
        return new TeamResponse(null, null, null, null, List.of(), null);
    }
}
