-- Migration 001: Initial schema for nut_Meals Infra Service
-- Run with: psql $DATABASE_URL -f migrations/001_initial.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE backup_status AS ENUM ('pending', 'running', 'success', 'failed', 'deleted');
CREATE TYPE backup_type   AS ENUM ('full', 'incremental');

CREATE TABLE IF NOT EXISTS backup_jobs (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    db_alias          VARCHAR(64)  NOT NULL,
    backup_type       backup_type  NOT NULL DEFAULT 'full',
    status            backup_status NOT NULL DEFAULT 'pending',

    -- Storage
    s3_key            VARCHAR(512),
    s3_bucket         VARCHAR(128),
    size_bytes        BIGINT,

    -- Integrity
    checksum_sha256   VARCHAR(64),
    encrypted         BOOLEAN NOT NULL DEFAULT TRUE,
    error_message     TEXT,

    -- Timestamps
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at        TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    expires_at        TIMESTAMPTZ,

    -- Celery reference
    celery_task_id    VARCHAR(128)
);

CREATE INDEX idx_backup_jobs_db_alias   ON backup_jobs (db_alias);
CREATE INDEX idx_backup_jobs_status     ON backup_jobs (status);
CREATE INDEX idx_backup_jobs_expires_at ON backup_jobs (expires_at);
CREATE INDEX idx_backup_jobs_created_at ON backup_jobs (created_at DESC);

COMMENT ON TABLE backup_jobs IS 'Tracks every pg_dump backup job executed by the infra service.';

COMMIT;
