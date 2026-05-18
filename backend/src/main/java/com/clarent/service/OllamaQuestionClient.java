package com.clarent.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

@Component
public class OllamaQuestionClient {
    private final RestClient restClient;
    private final ObjectMapper objectMapper;
    private final String baseUrl;
    private final String model;
    private final double temperature;
    private final int contextWindow;

    public OllamaQuestionClient(
            RestClient.Builder restClientBuilder,
            ObjectMapper objectMapper,
            @Value("${clarent.questions.ollama-url:http://127.0.0.1:11434}") String baseUrl,
            @Value("${clarent.questions.model:qwen3:4b}") String model,
            @Value("${clarent.questions.temperature:0.25}") double temperature,
            @Value("${clarent.questions.context-window:4096}") int contextWindow
    ) {
        this.baseUrl = baseUrl;
        this.model = model;
        this.temperature = temperature;
        this.contextWindow = contextWindow;
        this.objectMapper = objectMapper;
        this.restClient = restClientBuilder.baseUrl(baseUrl).build();
    }

    public String modelName() {
        return model;
    }

    public List<String> generateQuestions(String prompt) {
        OllamaChatRequest request = new OllamaChatRequest(
                model,
                List.of(
                        new OllamaMessage(
                                "system",
                                "You are Clarent, an assistant for product managers. "
                                        + "Output only compact valid JSON. No explanation. No markdown. "
                                        + "The first character must be {."
                        ),
                        new OllamaMessage("user", prompt)
                ),
                false,
                false,
                "json",
                Map.of(
                        "temperature", temperature,
                        "num_ctx", contextWindow,
                        "num_predict", 450
                )
        );

        try {
            OllamaChatResponse response = restClient.post()
                    .uri("/api/chat")
                    .body(request)
                    .retrieve()
                    .body(OllamaChatResponse.class);

            if (response == null || response.message() == null || response.message().content() == null) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Ollama returned an empty response");
            }
            List<String> questions = parseQuestions(response.message().content());
            if (questions.size() < 3) {
                throw new ResponseStatusException(
                        HttpStatus.BAD_GATEWAY,
                        "Ollama did not return 3 usable questions"
                );
            }
            return questions.stream().limit(3).toList();
        } catch (RestClientException exception) {
            String detail = exception.getMostSpecificCause() == null
                    ? exception.getMessage()
                    : exception.getMostSpecificCause().getMessage();
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "Could not get a response from local Ollama at " + baseUrl
                            + ". Confirm Ollama is running and the model exists: " + model
                            + ". Details: " + detail,
                    exception
            );
        }
    }

    private List<String> parseQuestions(String content) {
        String json = extractJson(content);
        try {
            JsonNode root = objectMapper.readTree(json);
            JsonNode questionsNode = root.get("questions");
            if (questionsNode == null || !questionsNode.isArray()) {
                return List.of();
            }
            List<String> questions = new ArrayList<>();
            for (JsonNode questionNode : questionsNode) {
                String question = cleanQuestion(questionNode.asText());
                if (!question.isBlank()) {
                    questions.add(question);
                }
            }
            return questions;
        } catch (Exception exception) {
            return fallbackQuestions(content);
        }
    }

    private String extractJson(String content) {
        String clean = content.replace("```json", "").replace("```", "").trim();
        int start = clean.indexOf('{');
        int end = clean.lastIndexOf('}');
        if (start >= 0 && end > start) {
            return clean.substring(start, end + 1);
        }
        return clean;
    }

    private List<String> fallbackQuestions(String content) {
        return content.lines()
                .map(this::cleanQuestion)
                .filter(line -> line.endsWith("?"))
                .limit(3)
                .toList();
    }

    private String cleanQuestion(String value) {
        return value
                .replaceFirst("^\\s*[-*]?\\s*\\d+[.)]\\s*", "")
                .replaceFirst("^\\s*[-*]\\s*", "")
                .trim();
    }

    private record OllamaChatRequest(
            String model,
            List<OllamaMessage> messages,
            boolean stream,
            boolean think,
            String format,
            Map<String, Object> options
    ) {
    }

    private record OllamaMessage(String role, String content) {
    }

    private record OllamaChatResponse(OllamaMessage message) {
    }
}
