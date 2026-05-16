CREATE TABLE team_documents (
    id UUID PRIMARY KEY,
    team_id UUID NOT NULL UNIQUE REFERENCES teams(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    content_type VARCHAR(120) NOT NULL,
    size_bytes BIGINT NOT NULL,
    data BYTEA NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by_id UUID REFERENCES app_users(id) ON DELETE SET NULL
);

CREATE INDEX idx_team_documents_team ON team_documents (team_id);
