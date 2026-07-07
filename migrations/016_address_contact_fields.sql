-- Migration 016: address contact/label metadata (Module 2.3)
--
-- Adds title / recipient_name / phone to saved addresses. The delivery branch
-- is still resolved from post_office (post_office_branch_mapping), so these are
-- purely descriptive and nullable.
--
-- Schema is created by SQLAlchemy Base.metadata.create_all() on fresh DBs; run
-- this against pre-existing databases. Safe to re-run.

ALTER TABLE addresses
    ADD COLUMN IF NOT EXISTS title          VARCHAR(100),
    ADD COLUMN IF NOT EXISTS recipient_name VARCHAR(150),
    ADD COLUMN IF NOT EXISTS phone          VARCHAR(30);
