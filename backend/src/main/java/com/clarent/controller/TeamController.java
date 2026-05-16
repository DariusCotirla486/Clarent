package com.clarent.controller;

import com.clarent.domain.user.AppUser;
import com.clarent.dto.team.AddTeamMemberRequest;
import com.clarent.dto.team.TeamResponse;
import com.clarent.service.TeamService;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api")
public class TeamController {
    private final TeamService teamService;

    public TeamController(TeamService teamService) {
        this.teamService = teamService;
    }

    @GetMapping("/manager/team")
    public TeamResponse managerTeam(@AuthenticationPrincipal AppUser user) {
        return teamService.managerTeam(user);
    }

    @PostMapping("/manager/team/members")
    public TeamResponse addMember(
            @AuthenticationPrincipal AppUser user,
            @Valid @RequestBody AddTeamMemberRequest request
    ) {
        return teamService.addMember(user, request);
    }

    @DeleteMapping("/manager/team/members/{memberId}")
    public TeamResponse removeMember(
            @AuthenticationPrincipal AppUser user,
            @PathVariable UUID memberId
    ) {
        return teamService.removeMember(user, memberId);
    }

    @PostMapping(value = "/manager/team/document", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public TeamResponse uploadDocument(
            @AuthenticationPrincipal AppUser user,
            @RequestParam("file") MultipartFile file
    ) {
        return teamService.uploadDocument(user, file);
    }

    @GetMapping("/member/team")
    public TeamResponse memberTeam(@AuthenticationPrincipal AppUser user) {
        return teamService.visibleTeam(user);
    }
}
