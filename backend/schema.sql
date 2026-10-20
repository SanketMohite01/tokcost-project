CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id TEXT NOT NULL,
    title TEXT,
    prompt_text TEXT NOT NULL,
    compressed_prompt TEXT,
    recommended_platform TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS meta JSONB;

CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    size_bytes INTEGER,
    tokens JSONB
);

CREATE TABLE IF NOT EXISTS results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    est_output_tokens INTEGER,
    est_cost_usd NUMERIC(10,6)
);

CREATE INDEX IF NOT EXISTS idx_sessions_owner_created
    ON sessions (owner_id, created_at DESC);