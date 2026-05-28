-- =============================================================================
-- SRIBEESonline Database Initialization Script
-- This script runs when PostgreSQL container starts for the first time
-- =============================================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS sribees;

-- Set default search path
ALTER DATABASE sribeesonline SET search_path TO sribees, public;

-- =============================================================================
-- USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMP WITH TIME ZONE,
    fcm_token VARCHAR(500),
    device_type VARCHAR(50),
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- ADMIN USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.admin_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'admin',
    permissions JSONB DEFAULT '[]'::jsonb,
    branch_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- CATEGORIES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    name_si VARCHAR(100),
    name_ta VARCHAR(100),
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    parent_id UUID REFERENCES sribees.categories(id) ON DELETE SET NULL,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- PRODUCTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    name_si VARCHAR(255),
    name_ta VARCHAR(255),
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    description_si TEXT,
    description_ta TEXT,
    sku VARCHAR(100) UNIQUE,
    barcode VARCHAR(100),
    category_id UUID REFERENCES sribees.categories(id) ON DELETE SET NULL,
    price DECIMAL(10, 2) NOT NULL,
    compare_at_price DECIMAL(10, 2),
    cost_price DECIMAL(10, 2),
    unit VARCHAR(50) DEFAULT 'piece',
    weight DECIMAL(10, 3),
    weight_unit VARCHAR(20) DEFAULT 'kg',
    stock_quantity INTEGER DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    images JSONB DEFAULT '[]'::jsonb,
    attributes JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],
    rating_average DECIMAL(3, 2) DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    sold_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- PRODUCT REVIEWS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.product_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES sribees.products(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES sribees.users(id) ON DELETE CASCADE,
    order_id UUID,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    content TEXT,
    images JSONB DEFAULT '[]'::jsonb,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, user_id)
);

-- =============================================================================
-- ADDRESSES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.addresses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES sribees.users(id) ON DELETE CASCADE,
    label VARCHAR(50) DEFAULT 'Home',
    recipient_name VARCHAR(200) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    province VARCHAR(100),
    postal_code VARCHAR(20),
    is_default BOOLEAN DEFAULT FALSE,
    delivery_instructions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- CARTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.carts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES sribees.users(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    items JSONB DEFAULT '[]'::jsonb,
    coupon_code VARCHAR(50),
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    notes TEXT,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- ORDERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    user_id UUID REFERENCES sribees.users(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending',
    payment_status VARCHAR(50) DEFAULT 'pending',
    payment_method VARCHAR(50),
    payment_reference VARCHAR(255),
    
    -- Amounts
    subtotal DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    delivery_fee DECIMAL(10, 2) DEFAULT 0,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    
    -- Delivery info
    delivery_address JSONB NOT NULL,
    delivery_notes TEXT,
    estimated_delivery TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    
    -- Items snapshot
    items JSONB NOT NULL,
    
    -- Tracking
    branch_id UUID,
    assigned_driver_id UUID,
    tracking_updates JSONB DEFAULT '[]'::jsonb,
    
    -- Coupon
    coupon_code VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancellation_reason TEXT
);

-- =============================================================================
-- WISHLISTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.wishlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES sribees.users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES sribees.products(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

-- =============================================================================
-- NOTIFICATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES sribees.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'general',
    data JSONB DEFAULT '{}'::jsonb,
    image_url VARCHAR(500),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- AUDIT LOGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id UUID,
    actor_type VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- BRANCHES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS sribees.branches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    email VARCHAR(255),
    manager_id UUID REFERENCES sribees.admin_users(id),
    is_active BOOLEAN DEFAULT TRUE,
    operating_hours JSONB,
    delivery_zones JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON sribees.users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON sribees.users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON sribees.users(created_at);

-- Products indexes
CREATE INDEX IF NOT EXISTS idx_products_category ON sribees.products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_slug ON sribees.products(slug);
CREATE INDEX IF NOT EXISTS idx_products_sku ON sribees.products(sku);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON sribees.products(is_active);
CREATE INDEX IF NOT EXISTS idx_products_is_featured ON sribees.products(is_featured);
CREATE INDEX IF NOT EXISTS idx_products_price ON sribees.products(price);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON sribees.products(created_at);
CREATE INDEX IF NOT EXISTS idx_products_tags ON sribees.products USING GIN(tags);

-- Orders indexes
CREATE INDEX IF NOT EXISTS idx_orders_user ON sribees.orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON sribees.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON sribees.orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON sribees.orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON sribees.orders(order_number);

-- Reviews indexes
CREATE INDEX IF NOT EXISTS idx_reviews_product ON sribees.product_reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user ON sribees.product_reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON sribees.product_reviews(rating);

-- Audit logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_actor ON sribees.audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON sribees.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON sribees.audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON sribees.audit_logs(created_at);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user ON sribees.notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON sribees.notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON sribees.notifications(created_at);

-- =============================================================================
-- SEED DATA: Default Super Admin
-- =============================================================================
INSERT INTO sribees.admin_users (
    email,
    password_hash,
    first_name,
    last_name,
    role,
    permissions,
    is_active
) VALUES (
    'admin@sribees.lk',
    -- Password: Admin@123456 (bcrypt hash)
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.GZJLPxkK8K8nXK',
    'Super',
    'Admin',
    'super_admin',
    '["all"]'::jsonb,
    true
) ON CONFLICT (email) DO NOTHING;

-- =============================================================================
-- SEED DATA: Sample Categories
-- =============================================================================
INSERT INTO sribees.categories (name, name_si, name_ta, slug, description, display_order, is_active)
VALUES 
    ('Fruits & Vegetables', 'පලතුරු සහ එළවළු', 'பழங்கள் & காய்கறிகள்', 'fruits-vegetables', 'Fresh fruits and vegetables', 1, true),
    ('Dairy & Eggs', 'කිරි නිෂ්පාදන සහ බිත්තර', 'பால் & முட்டைகள்', 'dairy-eggs', 'Fresh dairy products and eggs', 2, true),
    ('Meat & Seafood', 'මස් සහ මුහුදු ආහාර', 'இறைச்சி & கடல் உணவு', 'meat-seafood', 'Fresh meat and seafood', 3, true),
    ('Bakery', 'බේකරි', 'பேக்கரி', 'bakery', 'Fresh bread and baked goods', 4, true),
    ('Beverages', 'පාන වර්ග', 'பானங்கள்', 'beverages', 'Drinks and beverages', 5, true),
    ('Snacks', 'කෙටි ආහාර', 'சிற்றுண்டி', 'snacks', 'Snacks and chips', 6, true),
    ('Grocery', 'සිල්ලර භාණ්ඩ', 'மளிகை', 'grocery', 'Grocery essentials', 7, true),
    ('Household', 'ගෘහ භාණ්ඩ', 'வீட்டு பொருட்கள்', 'household', 'Household items', 8, true)
ON CONFLICT (slug) DO NOTHING;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION sribees.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Add update triggers for all tables with updated_at
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE table_schema = 'sribees' 
        AND column_name = 'updated_at'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON sribees.%I;
            CREATE TRIGGER update_%I_updated_at
            BEFORE UPDATE ON sribees.%I
            FOR EACH ROW
            EXECUTE FUNCTION sribees.update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================
GRANT USAGE ON SCHEMA sribees TO PUBLIC;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA sribees TO PUBLIC;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA sribees TO PUBLIC;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'SRIBEESonline database initialization completed successfully!';
END;
$$;
