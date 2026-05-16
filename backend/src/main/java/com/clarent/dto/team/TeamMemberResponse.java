package com.clarent.dto.team;

import com.clarent.domain.user.AppUser;
import com.clarent.domain.user.Role;
import java.util.UUID;

public record TeamMemberResponse(
        UUID userId,
        String fullName,
        String email,
        Role role,
        boolean manager
) {
    public static TeamMemberResponse from(AppUser user, UUID managerId) {
        return new TeamMemberResponse(
                user.getId(),
                user.getFullName(),
                user.getEmail(),
                user.getRole(),
                user.getId().equals(managerId)
        );
    }
}
