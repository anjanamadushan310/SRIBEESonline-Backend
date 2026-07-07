-- Migration 012: attribute orders to a fulfilling branch
--
-- Adds orders.branch_id and backfills existing orders by resolving the branch
-- from the delivery address's post office (post_office_branch_mapping).
--
-- The app creates schema via SQLAlchemy Base.metadata.create_all(), which does
-- NOT alter existing tables — run this against any pre-existing database.
-- Safe to re-run.

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(branch_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_orders_branch_id ON orders (branch_id);

-- Backfill: order -> delivery address -> post office -> serving branch.
UPDATE orders o
SET branch_id = m.branch_id
FROM addresses a
JOIN post_office_branch_mapping m ON m.post_office = a.post_office
WHERE o.delivery_address_id = a.address_id
  AND o.branch_id IS NULL;
