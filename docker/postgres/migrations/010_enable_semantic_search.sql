-- ============================================================================
-- SRIBEESonline - Semantic Search Migration
-- Enable pgvector and add embedding support to products table
-- ============================================================================

-- Migration: 010_enable_semantic_search.sql
-- Version: 1.0
-- Created: February 2026
-- Description: Enable pgvector extension and add embedding column for semantic search

-- ============================================================================
-- Step 1: Enable pgvector Extension
-- ============================================================================
-- Note: This requires superuser privileges. Run as postgres user or admin.

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Step 2: Add Embedding Column to Products Table
-- ============================================================================

-- Add the embedding column (768 dimensions for Gemini text-embedding-004)
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Add timestamp for tracking embedding updates
ALTER TABLE products
ADD COLUMN IF NOT EXISTS embedding_updated_at TIMESTAMP WITH TIME ZONE;

-- Add search_text column for combined multilingual searchable content
ALTER TABLE products
ADD COLUMN IF NOT EXISTS search_text TEXT;

-- ============================================================================
-- Step 3: Create Indexes for Vector Similarity Search
-- ============================================================================

-- IVFFlat index for cosine similarity (recommended for < 1M products)
-- The 'lists' parameter should be approximately sqrt(num_rows)
-- For 10,000 products, lists = 100 is appropriate
CREATE INDEX IF NOT EXISTS idx_products_embedding_ivfflat
ON products USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Alternative: HNSW index for higher accuracy (uncomment if needed)
-- CREATE INDEX IF NOT EXISTS idx_products_embedding_hnsw
-- ON products USING hnsw (embedding vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- Index for filtering products that have embeddings
CREATE INDEX IF NOT EXISTS idx_products_has_embedding
ON products ((embedding IS NOT NULL))
WHERE embedding IS NOT NULL;

-- ============================================================================
-- Step 4: Create Trigger for Auto-generating Search Text
-- ============================================================================

-- Function to combine product fields into searchable text
CREATE OR REPLACE FUNCTION update_product_search_text()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_text = COALESCE(NEW.name, '') || ' ' || 
                      COALESCE(NEW.short_description, '') || ' ' ||
                      COALESCE(NEW.description, '');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger (drop first if exists to make migration idempotent)
DROP TRIGGER IF EXISTS trigger_update_product_search_text ON products;

CREATE TRIGGER trigger_update_product_search_text
    BEFORE INSERT OR UPDATE OF name, short_description, description
    ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_product_search_text();

-- ============================================================================
-- Step 5: Create Optional Product Translations Table for Multilingual Support
-- ============================================================================

CREATE TABLE IF NOT EXISTS product_translations (
    translation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    language_code VARCHAR(10) NOT NULL, -- 'en', 'si', 'ta', 'si-LK-singlish'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    short_description VARCHAR(500),
    keywords TEXT[], -- Additional search keywords
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_product_translation UNIQUE(product_id, language_code)
);

-- Indexes for translations table
CREATE INDEX IF NOT EXISTS idx_product_translations_product 
ON product_translations(product_id);

CREATE INDEX IF NOT EXISTS idx_product_translations_language 
ON product_translations(language_code);

-- ============================================================================
-- Step 6: Create Search Analytics Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS search_analytics (
    search_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    query_normalized TEXT NOT NULL,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    results_count INTEGER NOT NULL DEFAULT 0,
    clicked_product_id UUID REFERENCES products(product_id) ON DELETE SET NULL,
    click_position INTEGER,
    search_type VARCHAR(20) NOT NULL DEFAULT 'semantic', -- 'semantic', 'keyword', 'hybrid'
    response_time_ms INTEGER NOT NULL,
    language_detected VARCHAR(10),
    filters_used JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for search analytics
CREATE INDEX IF NOT EXISTS idx_search_analytics_query 
ON search_analytics(query_normalized);

CREATE INDEX IF NOT EXISTS idx_search_analytics_created 
ON search_analytics(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_analytics_user 
ON search_analytics(user_id) WHERE user_id IS NOT NULL;

-- ============================================================================
-- Step 7: Create Stored Procedure for Semantic Search
-- ============================================================================

CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(768),
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 20,
    category_filter UUID DEFAULT NULL,
    min_price_filter NUMERIC DEFAULT NULL,
    max_price_filter NUMERIC DEFAULT NULL,
    in_stock_filter BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    product_id UUID,
    name VARCHAR(255),
    slug VARCHAR(255),
    description TEXT,
    short_description VARCHAR(500),
    price NUMERIC(10, 2),
    compare_at_price NUMERIC(10, 2),
    stock_quantity INTEGER,
    image_url VARCHAR(500),
    category_id UUID,
    category_name VARCHAR(100),
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.product_id,
        p.name,
        p.slug,
        p.description,
        p.short_description,
        p.price,
        p.compare_at_price,
        p.stock_quantity,
        (SELECT pi.image_url FROM product_images pi 
         WHERE pi.product_id = p.product_id AND pi.is_primary = TRUE 
         LIMIT 1) AS image_url,
        p.category_id,
        c.name AS category_name,
        (1 - (p.embedding <=> query_embedding))::FLOAT AS similarity_score
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.category_id
    WHERE 
        p.is_active = TRUE
        AND p.embedding IS NOT NULL
        AND (1 - (p.embedding <=> query_embedding)) > similarity_threshold
        AND (category_filter IS NULL OR p.category_id = category_filter)
        AND (min_price_filter IS NULL OR p.price >= min_price_filter)
        AND (max_price_filter IS NULL OR p.price <= max_price_filter)
        AND (in_stock_filter = FALSE OR p.stock_quantity > 0)
    ORDER BY p.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Step 8: Create Function for Keyword Fallback Search
-- ============================================================================

CREATE OR REPLACE FUNCTION keyword_search_fallback(
    search_query TEXT,
    max_results INTEGER DEFAULT 20,
    category_filter UUID DEFAULT NULL,
    min_price_filter NUMERIC DEFAULT NULL,
    max_price_filter NUMERIC DEFAULT NULL,
    in_stock_filter BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    product_id UUID,
    name VARCHAR(255),
    slug VARCHAR(255),
    description TEXT,
    short_description VARCHAR(500),
    price NUMERIC(10, 2),
    compare_at_price NUMERIC(10, 2),
    stock_quantity INTEGER,
    image_url VARCHAR(500),
    category_id UUID,
    category_name VARCHAR(100),
    relevance_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.product_id,
        p.name,
        p.slug,
        p.description,
        p.short_description,
        p.price,
        p.compare_at_price,
        p.stock_quantity,
        (SELECT pi.image_url FROM product_images pi 
         WHERE pi.product_id = p.product_id AND pi.is_primary = TRUE 
         LIMIT 1) AS image_url,
        p.category_id,
        c.name AS category_name,
        ts_rank(
            to_tsvector('simple', COALESCE(p.name, '') || ' ' || COALESCE(p.description, '')),
            plainto_tsquery('simple', search_query)
        )::FLOAT AS relevance_score
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.category_id
    WHERE 
        p.is_active = TRUE
        AND (
            p.name ILIKE '%' || search_query || '%'
            OR p.description ILIKE '%' || search_query || '%'
            OR p.short_description ILIKE '%' || search_query || '%'
            OR to_tsvector('simple', COALESCE(p.name, '') || ' ' || COALESCE(p.description, ''))
               @@ plainto_tsquery('simple', search_query)
        )
        AND (category_filter IS NULL OR p.category_id = category_filter)
        AND (min_price_filter IS NULL OR p.price >= min_price_filter)
        AND (max_price_filter IS NULL OR p.price <= max_price_filter)
        AND (in_stock_filter = FALSE OR p.stock_quantity > 0)
    ORDER BY relevance_score DESC, p.view_count DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Step 9: Update Existing Products with Search Text
-- ============================================================================

UPDATE products
SET search_text = COALESCE(name, '') || ' ' || 
                  COALESCE(short_description, '') || ' ' ||
                  COALESCE(description, '')
WHERE search_text IS NULL;

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- 
-- Post-migration tasks:
-- 1. Run embedding generation job to populate embedding column
-- 2. Tune IVFFlat lists parameter based on actual product count
-- 3. Monitor query performance and adjust similarity threshold
--
-- Example usage:
-- SELECT * FROM semantic_search(
--     '[0.1, 0.2, ...]'::vector(768),  -- Query embedding
--     0.7,                              -- Similarity threshold
--     20,                               -- Max results
--     NULL,                             -- Category filter (optional)
--     NULL,                             -- Min price (optional)
--     NULL,                             -- Max price (optional)
--     TRUE                              -- In stock only
-- );
-- ============================================================================
