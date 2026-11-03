CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS sessions (
  id varchar(36) PRIMARY KEY,
  user_id varchar(128) NOT NULL,
  battery_id varchar(32) NOT NULL,
  objective varchar(500) NOT NULL,
  created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_battery_id ON sessions(battery_id);
CREATE TABLE IF NOT EXISTS assessments (
  id varchar(36) PRIMARY KEY,
  session_id varchar(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  user_id varchar(128) NOT NULL,
  battery_id varchar(32) NOT NULL,
  cutoff_cycle integer NOT NULL,
  decision varchar(64) NOT NULL,
  explanation text NOT NULL,
  evidence_json text NOT NULL,
  policy_version varchar(64) NOT NULL,
  model_version varchar(128),
  idempotency_key varchar(128) NOT NULL,
  validity varchar(32) NOT NULL DEFAULT 'valid',
  supersedes_id varchar(36),
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL,
  UNIQUE(user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_assessments_session_id ON assessments(session_id);
CREATE INDEX IF NOT EXISTS ix_assessments_user_id ON assessments(user_id);
CREATE INDEX IF NOT EXISTS ix_assessments_battery_id ON assessments(battery_id);
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE assessments FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sessions_owner ON sessions;
DROP POLICY IF EXISTS assessments_owner ON assessments;
CREATE POLICY sessions_owner ON sessions USING (user_id = current_setting('app.user_id', true));
CREATE POLICY assessments_owner ON assessments USING (user_id = current_setting('app.user_id', true));
CREATE TABLE IF NOT EXISTS memory_embeddings (
  assessment_id varchar(36) PRIMARY KEY REFERENCES assessments(id) ON DELETE CASCADE,
  user_id varchar(128) NOT NULL,
  embedding vector(1024) NOT NULL,
  model_id text NOT NULL
);
ALTER TABLE memory_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_embeddings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS embeddings_owner ON memory_embeddings;
CREATE POLICY embeddings_owner ON memory_embeddings USING (user_id = current_setting('app.user_id', true));

