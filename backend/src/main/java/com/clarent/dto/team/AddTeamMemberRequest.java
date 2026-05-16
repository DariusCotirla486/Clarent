package com.clarent.dto.team;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record AddTeamMemberRequest(
        @Email @NotBlank String email
) {
}
