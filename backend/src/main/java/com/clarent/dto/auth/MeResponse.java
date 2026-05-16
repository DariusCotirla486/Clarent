package com.clarent.dto.auth;

import com.clarent.domain.user.AppUser;
import com.clarent.domain.user.Role;
import java.util.UUID;

public record MeResponse(
        UUID userId,
        String fullName,
        String email,
        Role role
) {
    public static MeResponse from(AppUser user) {
        return new MeResponse(user.getId(), user.getFullName(), user.getEmail(), user.getRole());
    }
}
