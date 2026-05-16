package com.clarent.service;

import com.clarent.domain.team.Team;
import com.clarent.domain.team.TeamDocument;
import com.clarent.domain.user.AppUser;
import com.clarent.domain.user.Role;
import com.clarent.dto.team.AddTeamMemberRequest;
import com.clarent.dto.team.TeamDocumentResponse;
import com.clarent.dto.team.TeamMemberResponse;
import com.clarent.dto.team.TeamResponse;
import com.clarent.repository.TeamDocumentRepository;
import com.clarent.repository.TeamRepository;
import com.clarent.repository.UserRepository;
import java.io.IOException;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@Service
public class TeamService {
    private static final long MAX_DOCUMENT_SIZE_BYTES = 10L * 1024L * 1024L;
    private static final Set<String> ALLOWED_DOCUMENT_EXTENSIONS = Set.of("txt", "pdf", "doc", "docx");

    private final TeamRepository teamRepository;
    private final UserRepository userRepository;
    private final TeamDocumentRepository teamDocumentRepository;

    public TeamService(
            TeamRepository teamRepository,
            UserRepository userRepository,
            TeamDocumentRepository teamDocumentRepository
    ) {
        this.teamRepository = teamRepository;
        this.userRepository = userRepository;
        this.teamDocumentRepository = teamDocumentRepository;
    }

    @Transactional
    public TeamResponse managerTeam(AppUser principal) {
        AppUser manager = loadUser(principal.getId());
        Team team = ensureManagerTeam(manager);
        return response(team);
    }

    @Transactional
    public TeamResponse addMember(AppUser principal, AddTeamMemberRequest request) {
        AppUser manager = loadUser(principal.getId());
        Team team = ensureManagerTeam(manager);
        AppUser member = userRepository.findByEmailIgnoreCase(request.email().trim().toLowerCase())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No registered user has that email"));

        if (member.getRole() != Role.TEAM_MEMBER) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Only team member accounts can be added");
        }
        if (member.getTeam() != null && !member.getTeam().getId().equals(team.getId())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "That user already belongs to another team");
        }

        member.setTeam(team);
        userRepository.save(member);
        return response(team);
    }

    @Transactional
    public TeamResponse removeMember(AppUser principal, UUID memberId) {
        AppUser manager = loadUser(principal.getId());
        Team team = ensureManagerTeam(manager);
        AppUser member = loadUser(memberId);

        if (member.getId().equals(manager.getId())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The manager cannot be removed from their own team");
        }
        if (member.getRole() != Role.TEAM_MEMBER
                || member.getTeam() == null
                || !member.getTeam().getId().equals(team.getId())) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Team member not found in this team");
        }

        member.setTeam(null);
        userRepository.save(member);
        return response(team);
    }

    @Transactional
    public TeamResponse uploadDocument(AppUser principal, MultipartFile file) {
        AppUser manager = loadUser(principal.getId());
        Team team = ensureManagerTeam(manager);
        validateDocument(file);

        try {
            TeamDocument document = teamDocumentRepository.findByTeam_Id(team.getId())
                    .orElseGet(() -> new TeamDocument(team));
            document.replace(
                    cleanFileName(file),
                    contentType(file),
                    file.getSize(),
                    file.getBytes(),
                    manager
            );
            teamDocumentRepository.save(document);
            return response(team);
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Could not read uploaded document");
        }
    }

    @Transactional(readOnly = true)
    public TeamResponse visibleTeam(AppUser principal) {
        AppUser user = loadUser(principal.getId());
        if (user.getTeam() == null) {
            return TeamResponse.empty();
        }
        return response(user.getTeam());
    }

    private AppUser loadUser(UUID userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
    }

    private Team ensureManagerTeam(AppUser manager) {
        return teamRepository.findByManager_Id(manager.getId())
                .orElseGet(() -> {
                    Team team = teamRepository.save(new Team(manager.getFullName() + "'s Team", manager));
                    manager.setTeam(team);
                    userRepository.save(manager);
                    return team;
                });
    }

    private TeamResponse response(Team team) {
        UUID managerId = team.getManager().getId();
        List<TeamMemberResponse> members = userRepository.findByTeam_IdOrderByFullNameAsc(team.getId())
                .stream()
                .map(user -> TeamMemberResponse.from(user, managerId))
                .toList();
        TeamDocumentResponse document = teamDocumentRepository.findByTeam_Id(team.getId())
                .map(TeamDocumentResponse::from)
                .orElse(null);
        return new TeamResponse(
                team.getId(),
                team.getName(),
                managerId,
                team.getManager().getFullName(),
                members,
                document
        );
    }

    private void validateDocument(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Upload a .txt, .pdf, .doc, or .docx file");
        }
        if (file.getSize() > MAX_DOCUMENT_SIZE_BYTES) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Document must be 10 MB or smaller");
        }

        String extension = extension(cleanFileName(file));
        if (!ALLOWED_DOCUMENT_EXTENSIONS.contains(extension)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Only .txt, .pdf, .doc, and .docx files are allowed");
        }
    }

    private String cleanFileName(MultipartFile file) {
        String originalName = file.getOriginalFilename();
        if (!StringUtils.hasText(originalName)) {
            return "team-context.txt";
        }
        String cleanName = StringUtils.cleanPath(originalName);
        if (cleanName.contains("..")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid file name");
        }
        return cleanName;
    }

    private String extension(String fileName) {
        int dotIndex = fileName.lastIndexOf('.');
        if (dotIndex < 0 || dotIndex == fileName.length() - 1) {
            return "";
        }
        return fileName.substring(dotIndex + 1).toLowerCase(Locale.ROOT);
    }

    private String contentType(MultipartFile file) {
        return StringUtils.hasText(file.getContentType()) ? file.getContentType() : "application/octet-stream";
    }
}
