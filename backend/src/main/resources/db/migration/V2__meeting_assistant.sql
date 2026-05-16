CREATE TABLE meeting_sessions (
    id UUID PRIMARY KEY,
    platform VARCHAR(40) NOT NULL,
    invite_link VARCHAR(1600) NOT NULL,
    status VARCHAR(40) NOT NULL,
    created_by_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_meeting_sessions_created_by ON meeting_sessions (created_by_id);
CREATE INDEX idx_meeting_sessions_status ON meeting_sessions (status);

CREATE TABLE transcript_segments (
    id UUID PRIMARY KEY,
    meeting_id UUID NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    language VARCHAR(40),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transcript_segments_meeting_received
    ON transcript_segments (meeting_id, received_at);
