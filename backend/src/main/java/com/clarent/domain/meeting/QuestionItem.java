package com.clarent.domain.meeting;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "question_items")
public class QuestionItem {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "suggestion_id", nullable = false)
    private QuestionSuggestion suggestion;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String questionText;

    @Column(nullable = false)
    private int displayOrder;

    @Column(nullable = false)
    private boolean asked = false;

    private Instant askedAt;

    protected QuestionItem() {
    }

    public QuestionItem(QuestionSuggestion suggestion, String questionText, int displayOrder) {
        this.suggestion = suggestion;
        this.questionText = questionText;
        this.displayOrder = displayOrder;
    }

    public UUID getId() {
        return id;
    }

    public QuestionSuggestion getSuggestion() {
        return suggestion;
    }

    public String getQuestionText() {
        return questionText;
    }

    public int getDisplayOrder() {
        return displayOrder;
    }

    public boolean isAsked() {
        return asked;
    }

    public Instant getAskedAt() {
        return askedAt;
    }

    public void markAsked() {
        this.asked = true;
        this.askedAt = Instant.now();
    }
}
