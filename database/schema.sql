-- Reference schema generated from the SQLite runtime initializer.
-- Existing installations use startup compatibility upgrades; this is not a migration.

CREATE TABLE audit_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              actor_user_id INTEGER,
              actor_role TEXT,
              action TEXT NOT NULL,
              resource_type TEXT NOT NULL,
              resource_id TEXT,
              metadata_json TEXT NOT NULL,
              request_id TEXT,
              created_at TEXT NOT NULL
            );

CREATE TABLE candidates (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              email TEXT,
              phone TEXT,
              links_json TEXT NOT NULL,
              education_json TEXT NOT NULL,
              skills_json TEXT NOT NULL,
              projects_json TEXT NOT NULL,
              experience_json TEXT NOT NULL,
              certifications_json TEXT NOT NULL,
              resume_text TEXT NOT NULL,
              resume_file_path TEXT,
              owner_user_id INTEGER,
              created_at TEXT NOT NULL
            );

CREATE TABLE jobs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              company TEXT,
              description TEXT NOT NULL,
              required_skills_json TEXT NOT NULL,
              responsibilities_json TEXT NOT NULL,
              tools_json TEXT NOT NULL,
              skill_weightage_json TEXT NOT NULL,
              level TEXT NOT NULL,
              domain TEXT NOT NULL,
              jd_quality_score REAL NOT NULL,
              status TEXT NOT NULL DEFAULT 'open',
              created_at TEXT NOT NULL
            );

CREATE TABLE match_results (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id INTEGER NOT NULL,
              job_id INTEGER NOT NULL,
              semantic_score REAL NOT NULL,
              skill_score REAL NOT NULL,
              project_score REAL NOT NULL,
              experience_score REAL NOT NULL,
              keyword_score REAL NOT NULL,
              education_score REAL NOT NULL,
              final_score REAL NOT NULL,
              shortlist_probability REAL NOT NULL,
              status TEXT NOT NULL,
              matched_skills_json TEXT NOT NULL,
              partial_skills_json TEXT NOT NULL,
              missing_skills_json TEXT NOT NULL,
              explanation TEXT NOT NULL,
              pipeline_stage TEXT NOT NULL DEFAULT 'Applied',
              created_at TEXT NOT NULL,
              UNIQUE(candidate_id, job_id)
            );

CREATE TABLE model_experiments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              model_name TEXT NOT NULL,
              accuracy REAL NOT NULL,
              precision REAL NOT NULL,
              recall REAL NOT NULL,
              f1_score REAL NOT NULL,
              parameters_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

CREATE TABLE password_reset_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              token_hash TEXT NOT NULL UNIQUE,
              expires_at TEXT NOT NULL,
              used_at TEXT,
              created_at TEXT NOT NULL
            );

CREATE TABLE refresh_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              token_hash TEXT NOT NULL UNIQUE,
              expires_at TEXT NOT NULL,
              revoked_at TEXT,
              created_at TEXT NOT NULL
            );

CREATE TABLE users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL CHECK(role IN ('ADMIN', 'RECRUITER', 'CANDIDATE')),
              company_name TEXT,
              created_at TEXT NOT NULL
            , failed_login_attempts INTEGER NOT NULL DEFAULT 0, locked_until TEXT);

CREATE INDEX idx_audit_logs_created
              ON audit_logs(created_at DESC);

CREATE INDEX idx_audit_logs_resource
              ON audit_logs(resource_type, resource_id);

CREATE INDEX idx_candidates_owner_created ON candidates(owner_user_id, created_at DESC);

CREATE INDEX idx_jobs_created
              ON jobs(created_at DESC);

CREATE INDEX idx_match_results_candidate
              ON match_results(candidate_id);

CREATE INDEX idx_match_results_job_score
              ON match_results(job_id, final_score DESC);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id, revoked_at);

CREATE INDEX idx_reset_tokens_hash ON password_reset_tokens(token_hash, used_at);
