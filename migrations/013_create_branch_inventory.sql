-- ============================================================================
-- Migration 013: Create branch_inventory table
--
-- Implements the "Global Catalog + Branch-Specific Overrides" pattern.
-- Products live in the global sribees.products table; per-branch pricing,
-- discounts, stock, and visibility overrides live here.
-- ============================================================================
-- Compatible with: sribees.products (PK = id), sribees.branches (PK = id)
-- ============================================================================

-- 1. Create the branch_inventory table
CREATE TABLE IF NOT EXISTS sribees.branch_inventory (
    inventory_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID NOT NULL REFERENCES sribees.products(id) ON DELETE CASCADE,
    branch_id           UUID NOT NULL REFERENCES sribees.branches(id) ON DELETE CASCADE,
    branch_price        NUMERIC(10, 2)   DEFAULT NULL,
    stock_quantity      INTEGER          NOT NULL DEFAULT 0,
    discount_percentage DOUBLE PRECISION DEFAULT NULL,
    is_on_sale          BOOLEAN          NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN          NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ      NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_branch_inventory_product_branch UNIQUE (product_id, branch_id)
);

-- 2. Indexes for efficient branch-scoped queries
CREATE INDEX IF NOT EXISTS idx_branch_inv_product
    ON sribees.branch_inventory (product_id);

CREATE INDEX IF NOT EXISTS idx_branch_inv_branch
    ON sribees.branch_inventory (branch_id);

CREATE INDEX IF NOT EXISTS idx_branch_inv_branch_sale
    ON sribees.branch_inventory (branch_id, is_on_sale);

CREATE INDEX IF NOT EXISTS idx_branch_inv_branch_active
    ON sribees.branch_inventory (branch_id, is_active);

CREATE INDEX IF NOT EXISTS idx_branch_inv_branch_sale_discount
    ON sribees.branch_inventory (branch_id, is_on_sale, discount_percentage);

-- 3. Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION sribees.update_branch_inventory_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_branch_inventory_updated_at ON sribees.branch_inventory;
CREATE TRIGGER trg_branch_inventory_updated_at
    BEFORE UPDATE ON sribees.branch_inventory
    FOR EACH ROW
    EXECUTE FUNCTION sribees.update_branch_inventory_updated_at();

-- 4. Add comments
COMMENT ON TABLE  sribees.branch_inventory IS 'Branch-specific overrides for global product catalog';
COMMENT ON COLUMN sribees.branch_inventory.branch_price IS 'Override price (NULL = use products.price)';
COMMENT ON COLUMN sribees.branch_inventory.discount_percentage IS 'Override discount % (NULL = use products.discount_percentage)';
COMMENT ON COLUMN sribees.branch_inventory.is_on_sale IS 'Branch Quick Sale flag';
COMMENT ON COLUMN sribees.branch_inventory.is_active IS 'FALSE hides product for this branch';
