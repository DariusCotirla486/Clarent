package com.clarent.dto.auth;

import com.clarent.domain.user.Role;
import java.util.UUID;

public record AuthResponse(
        String token,
        UUID userId,
        String fullName,
        String email,
        Role role
) {
}
