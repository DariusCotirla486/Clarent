package com.clarent.controller;

import java.util.Map;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class RoleDemoController {
    @GetMapping("/manager/dashboard")
    @PreAuthorize("hasRole('MANAGER')")
    public Map<String, String> managerDashboard() {
        return Map.of("message", "Manager access granted");
    }

    @GetMapping("/member/dashboard")
    @PreAuthorize("hasAnyRole('MANAGER', 'TEAM_MEMBER')")
    public Map<String, String> memberDashboard() {
        return Map.of("message", "Team workspace access granted");
    }
}
