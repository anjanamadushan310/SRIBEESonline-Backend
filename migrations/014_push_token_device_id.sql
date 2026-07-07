-- Migration 014: per-device push token identity
--
-- Adds push_tokens.device_id so a device that rotates its FCM token updates its
-- existing row (keyed by user_id + device_id) instead of orphaning a stale one.
--
-- Schema is created by SQLAlchemy Base.metadata.create_all() on fresh DBs; run
-- this against pre-existing databases. Safe to re-run.

ALTER TABLE push_tokens
    ADD COLUMN IF NOT EXISTS device_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_push_tokens_device_id ON push_tokens (device_id);
