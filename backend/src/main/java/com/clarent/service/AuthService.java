package com.clarent.service;

import com.clarent.domain.team.Team;
import com.clarent.domain.user.AppUser;
import com.clarent.domain.user.Role;
import com.clarent.dto.auth.AuthResponse;
import com.clarent.dto.auth.LoginRequest;
import com.clarent.dto.auth.MeResponse;
import com.clarent.dto.auth.RegisterRequest;
import com.clarent.repository.TeamRepository;
import com.clarent.repository.UserRepository;
import com.clarent.security.JwtService;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;
    private final TeamRepository teamRepository;

    public AuthService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            JwtService jwtService,
            AuthenticationManager authenticationManager,
            TeamRepository teamRepository
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.authenticationManager = authenticationManager;
        this.teamRepository = teamRepository;
    }

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        String email = request.email().trim().toLowerCase();
        if (userRepository.existsByEmailIgnoreCase(email)) {
            throw new IllegalArgumentException("Email is already registered");
        }

        AppUser user = new AppUser(
                request.fullName().trim(),
                email,
                passwordEncoder.encode(request.password()),
                request.role()
        );
        userRepository.save(user);
        if (user.getRole() == Role.MANAGER) {
            Team team = teamRepository.save(new Team(user.getFullName() + "'s Team", user));
            user.setTeam(team);
            userRepository.save(user);
        }
        return response(user);
    }

    @Transactional(readOnly = true)
    public AuthResponse login(LoginRequest request) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.email(), request.password())
        );
        AppUser user = userRepository.findByEmailIgnoreCase(request.email())
                .orElseThrow(() -> new IllegalArgumentException("Invalid credentials"));
        return response(user);
    }

    @Transactional(readOnly = true)
    public MeResponse me(AppUser principal) {
        AppUser user = userRepository.findById(principal.getId())
                .orElseThrow(() -> new IllegalArgumentException("User not found"));
        return MeResponse.from(user);
    }

    private AuthResponse response(AppUser user) {
        return new AuthResponse(
                jwtService.generateToken(user),
                user.getId(),
                user.getFullName(),
                user.getEmail(),
                user.getRole(),
                user.getTeam() == null ? null : user.getTeam().getId(),
                user.getTeam() == null ? null : user.getTeam().getName()
        );
    }
}
