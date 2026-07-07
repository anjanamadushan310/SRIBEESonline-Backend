-- ============================================================================
-- Migration 014: Create app_settings table
--
-- Key-value store for runtime application configuration.
-- Initial seed: splash_video_url placeholder.
-- ============================================================================

BEGIN;

-- 1. Create app_settings table
CREATE TABLE IF NOT EXISTS app_settings (
    setting_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key          VARCHAR(100) NOT NULL UNIQUE,
    value        TEXT,
    description  VARCHAR(500),
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  app_settings            IS 'Runtime application settings (key/value)';
COMMENT ON COLUMN app_settings.key        IS 'Unique setting identifier (e.g. splash_video_url)';
COMMENT ON COLUMN app_settings.value      IS 'Setting value (URL, JSON, plain text, etc.)';
COMMENT ON COLUMN app_settings.is_active  IS 'Whether this setting is currently active';

-- 2. Index on key for fast lookups
CREATE INDEX IF NOT EXISTS idx_app_settings_key ON app_settings (key);

-- 3. Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_app_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_app_settings_updated_at ON app_settings;
CREATE TRIGGER trg_app_settings_updated_at
    BEFORE UPDATE ON app_settings
    FOR EACH ROW EXECUTE FUNCTION update_app_settings_updated_at();

-- 4. Seed default splash video entry (placeholder URL — will be updated via Admin API)
-- setting_id is supplied explicitly: when the table is created by SQLAlchemy
-- create_all() the PK default is Python-side (uuid.uuid4), so the DB column has
-- NO default and an INSERT that omits it would violate the NOT NULL constraint.
INSERT INTO app_settings (setting_id, key, value, description, is_active)
VALUES (
    gen_random_uuid(),
    'splash_video_url',
    NULL,
    'URL of the splash-screen animation video shown when the Flutter app opens',
    TRUE
)
ON CONFLICT (key) DO NOTHING;

COMMIT;
