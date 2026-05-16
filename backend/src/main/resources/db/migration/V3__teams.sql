CREATE TABLE teams (
    id UUID PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    manager_id UUID NOT NULL UNIQUE REFERENCES app_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE app_users
    ADD COLUMN team_id UUID REFERENCES teams(id) ON DELETE SET NULL;

CREATE INDEX idx_app_users_team ON app_users (team_id);
