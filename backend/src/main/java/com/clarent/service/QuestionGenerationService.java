package com.clarent.service;

import com.clarent.domain.meeting.MeetingSession;
import com.clarent.domain.meeting.QuestionItem;
import com.clarent.domain.meeting.QuestionSuggestion;
import com.clarent.domain.meeting.TranscriptSegment;
import com.clarent.domain.team.Team;
import com.clarent.domain.team.TeamDocument;
import com.clarent.domain.user.AppUser;
import com.clarent.dto.meeting.QuestionItemResponse;
import com.clarent.dto.meeting.QuestionSuggestionResponse;
import com.clarent.repository.MeetingSessionRepository;
import com.clarent.repository.QuestionItemRepository;
import com.clarent.repository.QuestionSuggestionRepository;
import com.clarent.repository.TeamDocumentRepository;
import com.clarent.repository.TeamRepository;
import com.clarent.repository.TranscriptSegmentRepository;
import com.clarent.repository.UserRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ResponseStatusException;

@Service
public class QuestionGenerationService {
    private final MeetingSessionRepository meetingSessionRepository;
    private final TranscriptSegmentRepository transcriptSegmentRepository;
    private final QuestionSuggestionRepository questionSuggestionRepository;
    private final QuestionItemRepository questionItemRepository;
    private final TeamRepository teamRepository;
    private final TeamDocumentRepository teamDocumentRepository;
    private final UserRepository userRepository;
    private final TeamDocumentTextExtractor documentTextExtractor;
    private final OllamaQuestionClient ollamaQuestionClient;
    private final int contextCharacterLimit;
    private final int transcriptCharacterLimit;

    public QuestionGenerationService(
            MeetingSessionRepository meetingSessionRepository,
            TranscriptSegmentRepository transcriptSegmentRepository,
            QuestionSuggestionRepository questionSuggestionRepository,
            QuestionItemRepository questionItemRepository,
            TeamRepository teamRepository,
            TeamDocumentRepository teamDocumentRepository,
            UserRepository userRepository,
            TeamDocumentTextExtractor documentTextExtractor,
            OllamaQuestionClient ollamaQuestionClient,
            @Value("${clarent.questions.context-character-limit:8000}") int contextCharacterLimit,
            @Value("${clarent.questions.transcript-character-limit:1800}") int transcriptCharacterLimit
    ) {
        this.meetingSessionRepository = meetingSessionRepository;
        this.transcriptSegmentRepository = transcriptSegmentRepository;
        this.questionSuggestionRepository = questionSuggestionRepository;
        this.questionItemRepository = questionItemRepository;
        this.teamRepository = teamRepository;
        this.teamDocumentRepository = teamDocumentRepository;
        this.userRepository = userRepository;
        this.documentTextExtractor = documentTextExtractor;
        this.ollamaQuestionClient = ollamaQuestionClient;
        this.contextCharacterLimit = contextCharacterLimit;
        this.transcriptCharacterLimit = transcriptCharacterLimit;
    }

    @Transactional(readOnly = true)
    public List<QuestionSuggestionResponse> suggestions(UUID meetingId, AppUser principal) {
        MeetingSession session = ownedMeeting(meetingId, principal);
        return questionSuggestionRepository.findByMeetingIdOrderByCreatedAtDesc(session.getId())
                .stream()
                .map(QuestionSuggestionResponse::from)
                .toList();
    }

    @Transactional
    public QuestionSuggestionResponse generate(UUID meetingId, UUID transcriptSegmentId, AppUser principal) {
        MeetingSession session = ownedMeeting(meetingId, principal);
        TranscriptSegment transcript = transcriptSegmentRepository.findByIdAndMeetingId(
                        transcriptSegmentId,
                        session.getId()
                )
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "Transcript segment not found for this meeting"
                ));

        String context = teamContext(principal);
        String selectedTranscript = limit(clean(transcript.getText()), transcriptCharacterLimit);
        List<String> askedQuestions = questionItemRepository
                .findBySuggestion_Meeting_IdAndAskedTrueOrderByAskedAtAsc(session.getId())
                .stream()
                .map(QuestionItem::getQuestionText)
                .toList();

        String prompt = prompt(context, selectedTranscript, askedQuestions);
        List<String> generatedQuestions = ollamaQuestionClient.generateQuestions(prompt);

        QuestionSuggestion suggestion = new QuestionSuggestion(
                session,
                transcript,
                selectedTranscript,
                ollamaQuestionClient.modelName()
        );
        for (int index = 0; index < generatedQuestions.size(); index++) {
            suggestion.addQuestion(generatedQuestions.get(index), index + 1);
        }

        return QuestionSuggestionResponse.from(questionSuggestionRepository.save(suggestion));
    }

    @Transactional
    public QuestionItemResponse markAsked(UUID meetingId, UUID questionId, AppUser principal) {
        ownedMeeting(meetingId, principal);
        QuestionItem question = questionItemRepository.findByIdAndSuggestion_Meeting_Id(questionId, meetingId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Question not found"));
        question.markAsked();
        return QuestionItemResponse.from(questionItemRepository.save(question));
    }

    private MeetingSession ownedMeeting(UUID meetingId, AppUser principal) {
        return meetingSessionRepository.findByIdAndCreatedById(meetingId, principal.getId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Meeting session not found"));
    }

    private String teamContext(AppUser principal) {
        AppUser manager = userRepository.findById(principal.getId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
        Team team = teamRepository.findByManager_Id(manager.getId())
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "Create your team and upload a product context document first"
                ));
        TeamDocument document = teamDocumentRepository.findByTeam_Id(team.getId())
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "Upload a product context document before generating questions"
                ));
        String context = limit(clean(documentTextExtractor.extract(document)), contextCharacterLimit);
        if (!StringUtils.hasText(context)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "The uploaded team context document does not contain readable text"
            );
        }
        return context;
    }

    private String prompt(String context, String selectedTranscript, List<String> askedQuestions) {
        String alreadyAsked = askedQuestions.isEmpty()
                ? "None."
                : "- " + String.join("\n- ", askedQuestions);

        return """
                You are helping a product manager during a client discovery meeting.

                Project context:
                %s

                Selected client transcript:
                %s

                Questions already asked in this meeting:
                %s

                Generate the 3 most useful clarifying questions the manager should ask next.
                Rules:
                - Ask questions that reduce implementation ambiguity.
                - Prefer concrete product, workflow, data, permission, integration, edge-case, and acceptance-criteria details.
                - Do not repeat or closely paraphrase questions already asked.
                - Do not ask generic sales questions.
                - Keep each question short enough to ask naturally in the meeting.
                - Do not explain your reasoning.

                Return only valid JSON in this exact shape:
                {"questions":["question one?","question two?","question three?"]}
                The first character of your response must be {.
                """.formatted(context, selectedTranscript, alreadyAsked);
    }

    private String clean(String value) {
        if (value == null) {
            return "";
        }
        return value.replaceAll("\\s+", " ").trim();
    }

    private String limit(String value, int maxCharacters) {
        if (value.length() <= maxCharacters) {
            return value;
        }
        return value.substring(0, Math.max(0, maxCharacters)).trim();
    }
}
