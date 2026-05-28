# Multilingual Semantic Search - Technical Design Document

**Document Version:** 1.0  
**Created:** February 2026  
**Author:** Senior Backend Engineer  
**Status:** Approved for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Database Schema](#database-schema)
4. [AI Integration](#ai-integration)
5. [Search Logic](#search-logic)
6. [Caching Strategy](#caching-strategy)
7. [Error Handling](#error-handling)
8. [API Design](#api-design)
9. [Performance Considerations](#performance-considerations)
10. [Security Considerations](#security-considerations)
11. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

### Overview

This document outlines the technical design for implementing a **Multilingual Semantic Search** feature in the SRIBEESonline e-commerce platform. The system will enable users to search for grocery products using natural language queries in **English, Sinhala (සිංහල), Tamil (தமிழ்), and Singlish** (colloquial Sri Lankan English).

### Goals

- **Semantic Understanding**: Move beyond keyword matching to understand user intent
- **Multilingual Support**: Handle queries in 4 languages seamlessly
- **High Performance**: Sub-200ms response times for search queries
- **Graceful Degradation**: Fallback to keyword search if AI services fail
- **Scalability**: Support 10,000+ products with efficient vector search

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Embedding Model** | Google Gemini 1.5 Flash (text-embedding-004) |
| **Vector Database** | PostgreSQL 15+ with pgvector extension |
| **Backend Framework** | FastAPI (async) |
| **Caching** | Redis |
| **ORM** | SQLAlchemy 2.0 (async) |

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SRIBEESonline Search System                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │              │     │                  FastAPI Backend                  │  │
│  │   Client     │     │  ┌────────────────────────────────────────────┐  │  │
│  │  (Mobile/    │────▶│  │            /api/v1/search                  │  │  │
│  │   Web App)   │     │  │                                            │  │  │
│  │              │     │  │  ┌─────────────┐    ┌──────────────────┐   │  │  │
│  └──────────────┘     │  │  │  Query      │    │  Search          │   │  │  │
│                       │  │  │  Processor  │───▶│  Service         │   │  │  │
│                       │  │  └─────────────┘    └────────┬─────────┘   │  │  │
│                       │  │                              │             │  │  │
│                       │  └──────────────────────────────┼─────────────┘  │  │
│                       └─────────────────────────────────┼────────────────┘  │
│                                                         │                    │
│            ┌────────────────────────────────────────────┼────────────────┐  │
│            │                                            │                │  │
│            ▼                                            ▼                │  │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐   │  │
│  │                  │    │                  │    │                  │   │  │
│  │   Redis Cache    │    │  Gemini API      │    │   PostgreSQL     │   │  │
│  │                  │    │  (Embeddings)    │    │   (pgvector)     │   │  │
│  │  - Query Cache   │    │                  │    │                  │   │  │
│  │  - Embedding     │    │  768-dim vectors │    │  - Products      │   │  │
│  │    Cache         │    │                  │    │  - Embeddings    │   │  │
│  │                  │    │                  │    │                  │   │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘   │  │
│                                                                          │  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Search Request Flow                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. User Query                                                               │
│     "රතු ඇපල් ගෙඩි" (Red apples in Sinhala)                                  │
│            │                                                                 │
│            ▼                                                                 │
│  2. Cache Lookup ─────────────────────────────────────────┐                  │
│     Check Redis for cached results                        │                  │
│            │                                              │                  │
│            ▼ (Cache Miss)                                 │ (Cache Hit)      │
│  3. Query Normalization                                   │                  │
│     - Trim & lowercase                                    │                  │
│     - Remove extra spaces                                 │                  │
│            │                                              │                  │
│            ▼                                              │                  │
│  4. Generate Query Embedding                              │                  │
│     - Call Gemini API                                     │                  │
│     - Get 768-dim vector                                  │                  │
│            │                                              │                  │
│            ▼                                              │                  │
│  5. Vector Similarity Search                              │                  │
│     - pgvector cosine similarity                          │                  │
│     - Filter by threshold (0.7)                           │                  │
│            │                                              │                  │
│            ▼                                              │                  │
│  6. Result Processing                                     │                  │
│     - Score normalization                                 │                  │
│     - Product enrichment                                  │                  │
│            │                                              │                  │
│            ▼                                              ▼                  │
│  7. Cache Results ──────────────────────────────────▶ Return Response       │
│     Store in Redis (TTL: 1 hour)                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### pgvector Extension Setup

```sql
-- Enable pgvector extension (requires superuser)
CREATE EXTENSION IF NOT EXISTS vector;
```

### Products Table Enhancement

The existing `products` table will be enhanced with an embedding column:

```sql
-- Add embedding column to products table
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Create index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_products_embedding 
ON products 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Complete Products Schema with Embeddings

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `product_id` | UUID | PK | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Product name |
| `slug` | VARCHAR(255) | UNIQUE, NOT NULL | URL-friendly slug |
| `description` | TEXT | NULL | Full description |
| `short_description` | VARCHAR(500) | NULL | Brief description |
| `category_id` | UUID | FK → categories | Category reference |
| `price` | DECIMAL(10,2) | NOT NULL | Current price |
| `sku` | VARCHAR(100) | UNIQUE | Stock keeping unit |
| `stock_quantity` | INTEGER | DEFAULT 0 | Available stock |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `**embedding**` | **VECTOR(768)** | **NULL** | **Semantic embedding** |
| `embedding_updated_at` | TIMESTAMP | NULL | Last embedding update |
| `search_text` | TEXT | NULL | Combined searchable text |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update timestamp |

### Search Text Composition

The `search_text` column stores a combined, multilingual text for embedding generation:

```sql
-- Trigger to auto-generate search_text
CREATE OR REPLACE FUNCTION update_product_search_text()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_text = COALESCE(NEW.name, '') || ' ' || 
                      COALESCE(NEW.short_description, '') || ' ' ||
                      COALESCE(NEW.description, '');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_search_text
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_product_search_text();
```

### Product Multilingual Names Table (Optional Extension)

For better multilingual support, consider a separate translations table:

```sql
CREATE TABLE product_translations (
    translation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    language_code VARCHAR(10) NOT NULL, -- 'en', 'si', 'ta', 'si-LK-singlish'
    name VARCHAR(255) NOT NULL,
    description TEXT,
    keywords TEXT[], -- Additional search keywords
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(product_id, language_code)
);

CREATE INDEX idx_product_translations_product ON product_translations(product_id);
CREATE INDEX idx_product_translations_language ON product_translations(language_code);
```

### Embedding Index Strategies

| Index Type | Use Case | Configuration |
|------------|----------|---------------|
| **IVFFlat** | General purpose, good balance | `lists = sqrt(num_rows)` |
| **HNSW** | Higher accuracy, more memory | `m = 16, ef_construction = 64` |

```sql
-- IVFFlat (recommended for < 1M products)
CREATE INDEX idx_products_embedding_ivfflat
ON products USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- HNSW (alternative for higher accuracy)
CREATE INDEX idx_products_embedding_hnsw
ON products USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## AI Integration

### Gemini API Configuration

#### Model Selection

| Model | Dimensions | Use Case |
|-------|------------|----------|
| `text-embedding-004` | 768 | **Selected** - Best multilingual support |
| `embedding-001` | 768 | Legacy, less accurate |

#### API Configuration

```python
# Environment Variables
GEMINI_API_KEY=your_api_key_here
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_EMBEDDING_DIMENSION=768
GEMINI_API_TIMEOUT=30
GEMINI_MAX_RETRIES=3
```

### Embedding Generation Process

```
┌─────────────────────────────────────────────────────────────────┐
│                   Embedding Generation Flow                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input Text                                                      │
│  "Fresh Red Apples - ඇපල් - அப்பிள்"                             │
│            │                                                     │
│            ▼                                                     │
│  ┌─────────────────────────────────────┐                        │
│  │        Text Preprocessing           │                        │
│  │  - Unicode normalization (NFC)      │                        │
│  │  - Trim whitespace                  │                        │
│  │  - Remove control characters        │                        │
│  │  - Truncate to 2048 tokens max      │                        │
│  └─────────────────────────────────────┘                        │
│            │                                                     │
│            ▼                                                     │
│  ┌─────────────────────────────────────┐                        │
│  │         Gemini API Call             │                        │
│  │  POST /v1/models/text-embedding-004 │                        │
│  │  :embedContent                      │                        │
│  │                                     │                        │
│  │  {                                  │                        │
│  │    "model": "text-embedding-004",   │                        │
│  │    "content": {                     │                        │
│  │      "parts": [{"text": "..."}]     │                        │
│  │    }                                │                        │
│  │  }                                  │                        │
│  └─────────────────────────────────────┘                        │
│            │                                                     │
│            ▼                                                     │
│  Output: Float[768]                                              │
│  [0.0234, -0.0891, 0.0567, ..., 0.0123]                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Batch Embedding Generation

For initial data population and bulk updates:

```python
# Batch processing configuration
EMBEDDING_BATCH_SIZE = 100  # Products per batch
EMBEDDING_RATE_LIMIT = 1500  # Requests per minute (Gemini limit)
EMBEDDING_CONCURRENT_REQUESTS = 5  # Parallel API calls
```

### Multilingual Handling

Gemini's `text-embedding-004` model natively supports:
- **English**: Full support
- **Sinhala (සිංහල)**: Supported via multilingual training
- **Tamil (தமிழ்)**: Supported via multilingual training
- **Singlish**: Handled as English variant

#### Query Preprocessing for Languages

```python
def preprocess_query(query: str, detected_language: str = None) -> str:
    """
    Preprocess search query for optimal embedding generation.
    
    - Normalize Unicode (NFC form)
    - Handle mixed-script queries
    - Preserve semantic content
    """
    import unicodedata
    
    # Normalize to NFC (canonical composition)
    normalized = unicodedata.normalize('NFC', query)
    
    # Remove excessive whitespace
    cleaned = ' '.join(normalized.split())
    
    # Truncate if too long (Gemini limit)
    max_chars = 2048
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]
    
    return cleaned
```

---

## Search Logic

### Cosine Similarity Search

pgvector supports three distance functions:

| Operator | Function | Description |
|----------|----------|-------------|
| `<->` | L2 distance | Euclidean distance |
| `<#>` | Inner product | Negative inner product |
| `<=>` | **Cosine distance** | **1 - cosine similarity** |

**We use `<=>` (cosine distance) because:**
1. Scale-invariant (works regardless of embedding magnitude)
2. Better for semantic similarity
3. Industry standard for text embeddings

### Similarity Search Query

```sql
-- Basic similarity search
SELECT 
    product_id,
    name,
    slug,
    price,
    1 - (embedding <=> $1::vector) AS similarity_score
FROM products
WHERE 
    is_active = TRUE
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> $1::vector) > 0.7  -- Similarity threshold
ORDER BY embedding <=> $1::vector
LIMIT 20;
```

### Advanced Search with Filters

```sql
-- Search with category and price filters
SELECT 
    p.product_id,
    p.name,
    p.slug,
    p.price,
    p.stock_quantity,
    c.name AS category_name,
    1 - (p.embedding <=> $1::vector) AS similarity_score
FROM products p
LEFT JOIN categories c ON p.category_id = c.category_id
WHERE 
    p.is_active = TRUE
    AND p.embedding IS NOT NULL
    AND ($2::uuid IS NULL OR p.category_id = $2)  -- Optional category filter
    AND ($3::decimal IS NULL OR p.price >= $3)     -- Min price filter
    AND ($4::decimal IS NULL OR p.price <= $4)     -- Max price filter
    AND p.stock_quantity > 0                       -- In stock only
    AND 1 - (p.embedding <=> $1::vector) > $5      -- Similarity threshold
ORDER BY p.embedding <=> $1::vector
LIMIT $6
OFFSET $7;
```

### Hybrid Search (Semantic + Keyword)

For best results, combine semantic search with keyword matching:

```sql
-- Hybrid search combining vector similarity and text search
WITH semantic_results AS (
    SELECT 
        product_id,
        1 - (embedding <=> $1::vector) AS semantic_score
    FROM products
    WHERE 
        is_active = TRUE
        AND embedding IS NOT NULL
    ORDER BY embedding <=> $1::vector
    LIMIT 50
),
keyword_results AS (
    SELECT 
        product_id,
        ts_rank(
            to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, '')),
            plainto_tsquery('english', $2)
        ) AS keyword_score
    FROM products
    WHERE 
        is_active = TRUE
        AND to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, ''))
            @@ plainto_tsquery('english', $2)
)
SELECT 
    p.product_id,
    p.name,
    p.slug,
    p.price,
    COALESCE(s.semantic_score, 0) * 0.7 + COALESCE(k.keyword_score, 0) * 0.3 AS combined_score
FROM products p
LEFT JOIN semantic_results s ON p.product_id = s.product_id
LEFT JOIN keyword_results k ON p.product_id = k.product_id
WHERE s.product_id IS NOT NULL OR k.product_id IS NOT NULL
ORDER BY combined_score DESC
LIMIT 20;
```

### Score Interpretation

| Similarity Score | Interpretation | Action |
|------------------|----------------|--------|
| 0.90 - 1.00 | Excellent match | Show prominently |
| 0.80 - 0.89 | Good match | Include in results |
| 0.70 - 0.79 | Fair match | Include with lower ranking |
| < 0.70 | Poor match | Exclude from results |

---

## Caching Strategy

### Cache Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Caching Layers                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: Query Result Cache                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Key: search:results:{hash(query + filters)}                ││
│  │  Value: JSON array of product results                       ││
│  │  TTL: 1 hour                                                ││
│  │                                                             ││
│  │  Example:                                                   ││
│  │  search:results:a1b2c3d4 → [{"product_id": "...", ...}]    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Layer 2: Query Embedding Cache                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Key: search:embedding:{hash(normalized_query)}             ││
│  │  Value: Float[768] as JSON or binary                        ││
│  │  TTL: 24 hours                                              ││
│  │                                                             ││
│  │  Example:                                                   ││
│  │  search:embedding:e5f6g7h8 → [0.0234, -0.0891, ...]        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Layer 3: Popular Queries Cache                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Key: search:popular                                        ││
│  │  Value: Sorted set of query → count                         ││
│  │  TTL: 24 hours                                              ││
│  │                                                             ││
│  │  Used for: Autocomplete, trending searches                  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Cache Key Generation

```python
import hashlib
import json

def generate_cache_key(query: str, filters: dict = None) -> str:
    """
    Generate a deterministic cache key for search queries.
    """
    # Normalize query
    normalized_query = query.lower().strip()
    
    # Create payload for hashing
    payload = {
        "q": normalized_query,
        "f": filters or {}
    }
    
    # Generate hash
    payload_str = json.dumps(payload, sort_keys=True)
    hash_value = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    
    return f"search:results:{hash_value}"
```

### Cache Invalidation Strategy

| Event | Invalidation Action |
|-------|---------------------|
| Product updated | Invalidate all result caches containing product |
| Product deleted | Invalidate all result caches containing product |
| Product added | No invalidation needed (new products won't be in cache) |
| Price changed | Invalidate price-filtered caches |
| Category changed | Invalidate category-filtered caches |

```python
async def invalidate_product_cache(product_id: str):
    """
    Invalidate all search caches containing a specific product.
    Uses Redis SCAN to find and delete relevant keys.
    """
    pattern = "search:results:*"
    async for key in redis.scan_iter(pattern):
        cached_data = await redis.get(key)
        if cached_data and product_id in cached_data:
            await redis.delete(key)
```

### Redis Configuration

```python
# Redis cache settings
REDIS_SEARCH_CACHE_TTL = 3600          # 1 hour for search results
REDIS_EMBEDDING_CACHE_TTL = 86400      # 24 hours for embeddings
REDIS_POPULAR_QUERIES_TTL = 86400      # 24 hours for popular queries
REDIS_MAX_CACHED_RESULTS = 10000       # Max cached search results
```

---

## Error Handling

### Error Handling Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Handling Flow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Search Request                                                  │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────┐                                            │
│  │ Try Semantic    │───────────────────────────────┐            │
│  │ Search          │                               │            │
│  └────────┬────────┘                               │            │
│           │                                        │            │
│           ▼                                        │            │
│  ┌─────────────────┐     ┌─────────────────┐      │            │
│  │ Gemini API      │────▶│ API Error?      │      │            │
│  │ Call            │     │                 │      │            │
│  └─────────────────┘     └────────┬────────┘      │            │
│                                   │               │            │
│                          ┌────────┴────────┐      │            │
│                          │                 │      │            │
│                          ▼ Yes             ▼ No   │            │
│                   ┌──────────────┐   ┌──────────────┐          │
│                   │ Fallback to  │   │ Vector       │          │
│                   │ Keyword      │   │ Search       │          │
│                   │ Search       │   │              │          │
│                   └──────┬───────┘   └──────┬───────┘          │
│                          │                  │                   │
│                          │                  ▼                   │
│                          │           ┌──────────────┐          │
│                          │           │ DB Error?    │          │
│                          │           └──────┬───────┘          │
│                          │                  │                   │
│                          │         ┌────────┴────────┐         │
│                          │         ▼ Yes             ▼ No      │
│                          │   ┌──────────────┐  ┌──────────────┐│
│                          │   │ Return Empty │  │ Return       ││
│                          │   │ + Error Msg  │  │ Results      ││
│                          │   └──────────────┘  └──────────────┘│
│                          │                                      │
│                          ▼                                      │
│                   ┌──────────────┐                              │
│                   │ Return       │                              │
│                   │ Keyword      │                              │
│                   │ Results      │                              │
│                   └──────────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Error Types and Responses

| Error Type | HTTP Status | Fallback Action | User Message |
|------------|-------------|-----------------|--------------|
| Gemini API Timeout | 200 (degraded) | Keyword search | "Showing basic results" |
| Gemini API Rate Limit | 200 (degraded) | Keyword search | "Showing basic results" |
| Gemini API Auth Error | 500 | Keyword search | "Search temporarily limited" |
| Database Connection Error | 503 | None | "Search unavailable" |
| Invalid Query | 400 | None | "Please enter a valid search" |
| No Results | 200 | Suggest alternatives | "No products found" |

### Fallback Keyword Search

```sql
-- Basic keyword search fallback
SELECT 
    product_id,
    name,
    slug,
    price,
    ts_rank(
        to_tsvector('simple', COALESCE(name, '') || ' ' || COALESCE(description, '')),
        plainto_tsquery('simple', $1)
    ) AS relevance_score
FROM products
WHERE 
    is_active = TRUE
    AND stock_quantity > 0
    AND (
        name ILIKE '%' || $1 || '%'
        OR description ILIKE '%' || $1 || '%'
        OR to_tsvector('simple', COALESCE(name, '') || ' ' || COALESCE(description, ''))
           @@ plainto_tsquery('simple', $1)
    )
ORDER BY relevance_score DESC, sold_count DESC
LIMIT 20;
```

### Circuit Breaker Pattern

```python
class GeminiCircuitBreaker:
    """
    Circuit breaker for Gemini API calls.
    
    States:
    - CLOSED: Normal operation, API calls proceed
    - OPEN: API failing, use fallback immediately
    - HALF_OPEN: Testing if API recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
```

### Retry Strategy

```python
# Retry configuration
GEMINI_RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1.0,      # seconds
    "max_delay": 10.0,         # seconds
    "exponential_base": 2,
    "jitter": True,
    "retryable_errors": [
        "RESOURCE_EXHAUSTED",  # Rate limit
        "UNAVAILABLE",         # Service unavailable
        "DEADLINE_EXCEEDED",   # Timeout
    ]
}
```

---

## API Design

### Endpoint Specification

#### Search Products

```
POST /api/v1/search
```

**Request Body:**
```json
{
    "query": "රතු ඇපල්",
    "filters": {
        "category_id": "uuid-optional",
        "min_price": 0,
        "max_price": 1000,
        "in_stock_only": true
    },
    "pagination": {
        "page": 1,
        "page_size": 20
    },
    "options": {
        "include_facets": true,
        "highlight": true
    }
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "results": [
            {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Fresh Red Apples",
                "slug": "fresh-red-apples",
                "price": 350.00,
                "original_price": 400.00,
                "discount_percentage": 12.5,
                "image_url": "https://...",
                "category": {
                    "id": "...",
                    "name": "Fruits"
                },
                "in_stock": true,
                "similarity_score": 0.92,
                "highlights": {
                    "name": "<em>Red Apples</em>",
                    "description": "Fresh <em>red apples</em> from..."
                }
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total_results": 45,
            "total_pages": 3,
            "has_next": true,
            "has_previous": false
        },
        "facets": {
            "categories": [
                {"id": "...", "name": "Fruits", "count": 25},
                {"id": "...", "name": "Organic", "count": 12}
            ],
            "price_ranges": [
                {"min": 0, "max": 100, "count": 10},
                {"min": 100, "max": 500, "count": 30},
                {"min": 500, "max": null, "count": 5}
            ]
        },
        "search_metadata": {
            "query": "රතු ඇපල්",
            "search_type": "semantic",
            "took_ms": 45,
            "cached": false
        }
    },
    "message": null
}
```

**Error Response (400 Bad Request):**
```json
{
    "success": false,
    "data": null,
    "message": "Search query must be between 1 and 500 characters",
    "error_code": "INVALID_QUERY"
}
```

### Request/Response Models (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from enum import Enum

class SearchFilters(BaseModel):
    category_id: Optional[UUID] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    in_stock_only: bool = True

class SearchPagination(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

class SearchOptions(BaseModel):
    include_facets: bool = False
    highlight: bool = False

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    filters: Optional[SearchFilters] = None
    pagination: Optional[SearchPagination] = None
    options: Optional[SearchOptions] = None

class SearchType(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"

class ProductResult(BaseModel):
    product_id: UUID
    name: str
    slug: str
    price: float
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    image_url: Optional[str] = None
    category: Optional[dict] = None
    in_stock: bool
    similarity_score: Optional[float] = None
    highlights: Optional[dict] = None

class SearchMetadata(BaseModel):
    query: str
    search_type: SearchType
    took_ms: int
    cached: bool

class SearchResponse(BaseModel):
    results: List[ProductResult]
    pagination: dict
    facets: Optional[dict] = None
    search_metadata: SearchMetadata
```

---

## Performance Considerations

### Benchmarks and Targets

| Metric | Target | Measurement Point |
|--------|--------|-------------------|
| Search Latency (P50) | < 100ms | End-to-end API response |
| Search Latency (P95) | < 200ms | End-to-end API response |
| Search Latency (P99) | < 500ms | End-to-end API response |
| Embedding Generation | < 150ms | Gemini API call |
| Vector Search | < 50ms | PostgreSQL query |
| Cache Hit Rate | > 60% | Redis cache |
| Throughput | 500 req/s | Concurrent searches |

### Optimization Strategies

1. **Index Tuning**
   ```sql
   -- Adjust IVFFlat probes for accuracy vs speed
   SET ivfflat.probes = 10;  -- Higher = more accurate, slower
   ```

2. **Connection Pooling**
   ```python
   # SQLAlchemy async pool settings
   SQLALCHEMY_POOL_SIZE = 20
   SQLALCHEMY_MAX_OVERFLOW = 10
   SQLALCHEMY_POOL_TIMEOUT = 30
   ```

3. **Batch Embedding Updates**
   - Run embedding updates during off-peak hours
   - Process in batches of 100 products
   - Use background tasks (Celery/ARQ)

4. **Query Optimization**
   - Use prepared statements
   - Limit result set early with WHERE clauses
   - Avoid SELECT * in production

---

## Security Considerations

### API Key Security

```python
# Never log API keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # From environment only

# Use secrets management in production
# - AWS Secrets Manager
# - HashiCorp Vault
# - Google Secret Manager
```

### Input Validation

```python
def validate_search_query(query: str) -> str:
    """
    Validate and sanitize search query.
    
    - Prevent injection attacks
    - Limit query length
    - Remove dangerous characters
    """
    if not query or len(query.strip()) == 0:
        raise ValueError("Query cannot be empty")
    
    if len(query) > 500:
        raise ValueError("Query too long")
    
    # Remove potential SQL injection patterns
    # (pgvector handles parameterization, but defense in depth)
    sanitized = query.replace("--", "").replace(";", "")
    
    return sanitized.strip()
```

### Rate Limiting

```python
# Per-user rate limits
SEARCH_RATE_LIMIT = "100/minute"  # 100 searches per minute per user
SEARCH_RATE_LIMIT_ANONYMOUS = "30/minute"  # Lower for anonymous users
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)

- [ ] Enable pgvector extension in PostgreSQL
- [ ] Add embedding column to products table
- [ ] Create vector index
- [ ] Implement Gemini embedding service
- [ ] Write unit tests for embedding generation

### Phase 2: Core Search (Week 2)

- [ ] Implement similarity search query
- [ ] Create search endpoint
- [ ] Add request/response validation
- [ ] Implement basic caching
- [ ] Write integration tests

### Phase 3: Optimization (Week 3)

- [ ] Add fallback keyword search
- [ ] Implement circuit breaker
- [ ] Add search analytics
- [ ] Performance tuning
- [ ] Load testing

### Phase 4: Enhancement (Week 4)

- [ ] Hybrid search implementation
- [ ] Autocomplete suggestions
- [ ] Search facets
- [ ] A/B testing framework
- [ ] Documentation completion

---

## Appendix

### A. Gemini API Reference

**Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent`

**Request:**
```json
{
    "model": "models/text-embedding-004",
    "content": {
        "parts": [{"text": "Your text here"}]
    }
}
```

**Response:**
```json
{
    "embedding": {
        "values": [0.0234, -0.0891, 0.0567, ...]
    }
}
```

### B. pgvector Operators Reference

| Operator | Description |
|----------|-------------|
| `<->` | L2 (Euclidean) distance |
| `<#>` | Negative inner product |
| `<=>` | Cosine distance |
| `+` | Element-wise addition |
| `-` | Element-wise subtraction |
| `*` | Element-wise multiplication |

### C. Sample Multilingual Test Queries

| Language | Query | Expected Results |
|----------|-------|------------------|
| English | "fresh red apples" | Apple products |
| Sinhala | "රතු ඇපල් ගෙඩි" | Apple products |
| Tamil | "சிவப்பு ஆப்பிள்" | Apple products |
| Singlish | "eka bottle milk" | Milk products |

---

*Document prepared for SRIBEESonline E-Commerce Platform*  
*Semantic Search Implementation v1.0*
