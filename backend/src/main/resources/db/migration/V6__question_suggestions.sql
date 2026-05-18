CREATE TABLE question_suggestions (
    id UUID PRIMARY KEY,
    meeting_id UUID NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
    transcript_segment_id UUID NOT NULL REFERENCES transcript_segments(id) ON DELETE CASCADE,
    transcript_text TEXT NOT NULL,
    model_name VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_question_suggestions_meeting_created
    ON question_suggestions (meeting_id, created_at DESC);

CREATE INDEX idx_question_suggestions_transcript
    ON question_suggestions (transcript_segment_id);

CREATE TABLE question_items (
    id UUID PRIMARY KEY,
    suggestion_id UUID NOT NULL REFERENCES question_suggestions(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    display_order INT NOT NULL,
    asked BOOLEAN NOT NULL DEFAULT false,
    asked_at TIMESTAMPTZ
);

CREATE INDEX idx_question_items_suggestion
    ON question_items (suggestion_id, display_order);

CREATE INDEX idx_question_items_asked
    ON question_items (asked, asked_at);
