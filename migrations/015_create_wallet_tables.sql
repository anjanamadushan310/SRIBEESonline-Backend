-- ============================================================================
-- Migration 015: Create wallet & cashback tables
--
--   wallets              - one row per user holding the cashback balance (LKR)
--   wallet_transactions  - append-only ledger of earned/spent/refund movements
-- ============================================================================

BEGIN;

-- 1. Wallets (one per user) -------------------------------------------------
CREATE TABLE IF NOT EXISTS wallets (
    wallet_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL UNIQUE REFERENCES users (user_id) ON DELETE CASCADE,
    balance     NUMERIC(10, 2) NOT NULL DEFAULT 0,
    currency    VARCHAR(3) NOT NULL DEFAULT 'LKR',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallets (user_id);

COMMENT ON TABLE  wallets         IS 'Per-user cashback wallet';
COMMENT ON COLUMN wallets.balance IS 'Current cashback balance';

-- 2. Wallet transactions (ledger) -------------------------------------------
CREATE TABLE IF NOT EXISTS wallet_transactions (
    transaction_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id       UUID NOT NULL REFERENCES wallets (wallet_id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    order_id        UUID REFERENCES orders (order_id) ON DELETE SET NULL,
    type            VARCHAR(20) NOT NULL,          -- 'earned' | 'spent' | 'refund'
    title           VARCHAR(255) NOT NULL,
    amount          NUMERIC(10, 2) NOT NULL,       -- always positive; type = direction
    balance_after   NUMERIC(10, 2),
    order_number    VARCHAR(50),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wallet_tx_user_id ON wallet_transactions (user_id);
CREATE INDEX IF NOT EXISTS idx_wallet_tx_wallet_id ON wallet_transactions (wallet_id);
CREATE INDEX IF NOT EXISTS idx_wallet_tx_created_at ON wallet_transactions (created_at DESC);

COMMENT ON TABLE  wallet_transactions        IS 'Append-only wallet movement ledger';
COMMENT ON COLUMN wallet_transactions.type   IS 'earned | spent | refund';
COMMENT ON COLUMN wallet_transactions.amount IS 'Positive magnitude; direction implied by type';

-- 3. Auto-update updated_at on wallets --------------------------------------
CREATE OR REPLACE FUNCTION update_wallets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_wallets_updated_at ON wallets;
CREATE TRIGGER trg_wallets_updated_at
    BEFORE UPDATE ON wallets
    FOR EACH ROW
    EXECUTE FUNCTION update_wallets_updated_at();

-- 4. Wallet/cashback columns on orders --------------------------------------
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS wallet_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS cashback_earned  NUMERIC(10, 2) NOT NULL DEFAULT 0;

COMMIT;
