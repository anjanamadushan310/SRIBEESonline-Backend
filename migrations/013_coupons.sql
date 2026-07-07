-- Migration 013: promotions & coupons
--
-- Creates the coupons table backing the Marketing Coupons module.
-- The app creates schema via SQLAlchemy Base.metadata.create_all(), which
-- creates missing tables on startup — this script is for pre-existing
-- databases where create_all has already run. Safe to re-run.

CREATE TABLE IF NOT EXISTS coupons (
    coupon_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code             VARCHAR(50)  NOT NULL UNIQUE,
    description      TEXT,
    discount_type    VARCHAR(20)  NOT NULL DEFAULT 'percentage',
    discount_value   NUMERIC(10,2) NOT NULL,
    min_order_value  NUMERIC(10,2) NOT NULL DEFAULT 0,
    usage_limit      INTEGER,
    used_count       INTEGER      NOT NULL DEFAULT 0,
    valid_from       TIMESTAMPTZ  NOT NULL,
    valid_until      TIMESTAMPTZ  NOT NULL,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  DEFAULT now(),
    updated_at       TIMESTAMPTZ  DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons (code);
CREATE INDEX IF NOT EXISTS idx_coupons_active ON coupons (is_active);
