-- Migration 011: Branch inventory stock-tracking fields
--
-- Adds per-branch reserved stock and low-stock threshold to branch_inventory.
-- The app creates schema via SQLAlchemy Base.metadata.create_all(), which does
-- NOT alter existing tables — run this against any pre-existing database.
--
-- Safe to re-run: uses IF NOT EXISTS.

ALTER TABLE branch_inventory
    ADD COLUMN IF NOT EXISTS reserved_quantity   INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS low_stock_threshold INTEGER NOT NULL DEFAULT 10;

-- Partial index to speed up "low stock" reporting per branch.
CREATE INDEX IF NOT EXISTS idx_branch_inv_low_stock
    ON branch_inventory (branch_id)
    WHERE stock_quantity <= low_stock_threshold;
