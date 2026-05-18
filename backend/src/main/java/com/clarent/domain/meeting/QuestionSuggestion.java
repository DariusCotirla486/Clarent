package com.clarent.domain.meeting;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OrderBy;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "question_suggestions")
public class QuestionSuggestion {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "meeting_id", nullable = false)
    private MeetingSession meeting;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "transcript_segment_id", nullable = false)
    private TranscriptSegment transcriptSegment;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String transcriptText;

    @Column(nullable = false, length = 120)
    private String modelName;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    @OneToMany(mappedBy = "suggestion", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("displayOrder ASC")
    private List<QuestionItem> questions = new ArrayList<>();

    protected QuestionSuggestion() {
    }

    public QuestionSuggestion(
            MeetingSession meeting,
            TranscriptSegment transcriptSegment,
            String transcriptText,
            String modelName
    ) {
        this.meeting = meeting;
        this.transcriptSegment = transcriptSegment;
        this.transcriptText = transcriptText;
        this.modelName = modelName;
    }

    public UUID getId() {
        return id;
    }

    public MeetingSession getMeeting() {
        return meeting;
    }

    public TranscriptSegment getTranscriptSegment() {
        return transcriptSegment;
    }

    public String getTranscriptText() {
        return transcriptText;
    }

    public String getModelName() {
        return modelName;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public List<QuestionItem> getQuestions() {
        return questions;
    }

    public void addQuestion(String questionText, int displayOrder) {
        questions.add(new QuestionItem(this, questionText, displayOrder));
    }
}
