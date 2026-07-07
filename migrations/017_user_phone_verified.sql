-- Migration 017: phone verification flag (Module 1.7 — OTP)
--
-- Adds users.is_phone_verified, set True after a successful OTP verification.
--
-- Schema is created by SQLAlchemy Base.metadata.create_all() on fresh DBs; run
-- this against pre-existing databases. Safe to re-run.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_phone_verified BOOLEAN NOT NULL DEFAULT FALSE;
