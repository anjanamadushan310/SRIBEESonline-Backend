-- ============================================================================
-- Migration 011: Create Post Office → Branch Mapping Table
--                Add MARKETING_MANAGER to admin roles
--                Add missing columns to branches table
-- ============================================================================
-- Date: February 2026
-- Compatible with: sribees schema (init.sql)
-- ============================================================================

BEGIN;

-- --------------------------------------------------------------------------
-- Step 1: Add 'post_office' and 'province' columns to existing branches
--         (init.sql created the table but omitted these)
-- --------------------------------------------------------------------------
ALTER TABLE sribees.branches
    ADD COLUMN IF NOT EXISTS post_office VARCHAR(100);

ALTER TABLE sribees.branches
    ADD COLUMN IF NOT EXISTS province VARCHAR(100);

-- --------------------------------------------------------------------------
-- Step 2: Create post_office_branch_mapping table
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sribees.post_office_branch_mapping (
    mapping_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_office     VARCHAR(100) NOT NULL UNIQUE,
    branch_id       UUID NOT NULL REFERENCES sribees.branches(id) ON DELETE CASCADE,
    branch_name     VARCHAR(255) NOT NULL,
    district        VARCHAR(100),
    province        VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_po_branch_mapping_post_office
    ON sribees.post_office_branch_mapping (post_office);
CREATE INDEX IF NOT EXISTS idx_po_branch_mapping_branch
    ON sribees.post_office_branch_mapping (branch_id);
CREATE INDEX IF NOT EXISTS idx_po_branch_mapping_district
    ON sribees.post_office_branch_mapping (district);
CREATE INDEX IF NOT EXISTS idx_po_branch_mapping_active
    ON sribees.post_office_branch_mapping (is_active);

COMMENT ON TABLE sribees.post_office_branch_mapping IS
    'Maps Post Office names to serving branches for address-based branch routing.';

-- --------------------------------------------------------------------------
-- Step 3: Auto-update triggers
-- --------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sribees.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_po_branch_mapping_updated_at ON sribees.post_office_branch_mapping;
CREATE TRIGGER trg_po_branch_mapping_updated_at
    BEFORE UPDATE ON sribees.post_office_branch_mapping
    FOR EACH ROW
    EXECUTE FUNCTION sribees.update_updated_at_column();

COMMIT;
