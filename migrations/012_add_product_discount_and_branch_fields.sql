-- ============================================================================
-- Migration 012: Add discount & sale fields to products table
--
-- Adds:
--   discount_percentage  FLOAT
--   discount_price       NUMERIC(10,2)
--   is_on_sale           BOOLEAN DEFAULT FALSE
--
-- Note: branch_id is NOT added here — branch isolation uses branch_inventory
--       (see migration 013).
-- ============================================================================
-- Compatible with: sribees.products (PK = id)
-- ============================================================================

-- 1. Add discount columns
ALTER TABLE sribees.products
    ADD COLUMN IF NOT EXISTS discount_percentage DOUBLE PRECISION DEFAULT NULL;

ALTER TABLE sribees.products
    ADD COLUMN IF NOT EXISTS discount_price NUMERIC(10, 2) DEFAULT NULL;

ALTER TABLE sribees.products
    ADD COLUMN IF NOT EXISTS is_on_sale BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Create indexes for fast Quick Sale queries
CREATE INDEX IF NOT EXISTS idx_product_is_on_sale
    ON sribees.products (is_on_sale);

-- 3. Add comments
COMMENT ON COLUMN sribees.products.discount_percentage IS 'Discount percentage set by Marketing Manager (0-100)';
COMMENT ON COLUMN sribees.products.discount_price IS 'Effective sale price after discount applied';
COMMENT ON COLUMN sribees.products.is_on_sale IS 'Whether this product appears in the Quick Sale home feed';
