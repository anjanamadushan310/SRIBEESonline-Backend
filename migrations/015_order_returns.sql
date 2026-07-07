-- Migration 015: order returns & refunds (Module 5.5)
--
-- Adds return-request fields to orders. Order status is a VARCHAR column, so the
-- new 'return_requested' / 'return_approved' enum values need no DB change.
--
-- Schema is created by SQLAlchemy Base.metadata.create_all() on fresh DBs; run
-- this against pre-existing databases. Safe to re-run.

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS return_reason        VARCHAR(255),
    ADD COLUMN IF NOT EXISTS return_comments      TEXT,
    ADD COLUMN IF NOT EXISTS return_items         JSONB,
    ADD COLUMN IF NOT EXISTS return_requested_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS refund_amount        NUMERIC(10,2);
