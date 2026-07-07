# SRIBEESonline Database Specification

**Document Version:** 2.0  
**Last Updated:** February 17, 2026  
**Database Stack:** PostgreSQL 15+ | Redis 7+ | SQLAlchemy 2.0+ (async)

---

## Table of Contents

1. [Overview](#overview)
2. [Database Architecture](#database-architecture)
3. [PostgreSQL Schema](#postgresql-schema)
   - [User Management](#1-user-management)
   - [Products & Catalog](#2-products--catalog)
   - [Admin & RBAC](#3-admin--rbac)
   - [Cart & Coupons](#4-cart--coupons)
   - [Orders & Fulfillment](#5-orders--fulfillment)
   - [Payments](#6-payments)
   - [Product Variants](#7-product-variants)
   - [Multi-Branch Inventory](#8-multi-branch-inventory)
   - [Notifications](#9-notifications)
4. [Redis Data Structures](#redis-data-structures)
5. [Database Indexes](#database-indexes)
6. [Triggers & Functions](#triggers--functions)
7. [Entity Relationship Diagram](#entity-relationship-diagram)
8. [Data Retention & TTL](#data-retention--ttl)
9. [Migration History](#migration-history)

---

## Overview

SRIBEESonline uses PostgreSQL as the primary relational database and Redis for caching, session management, and cart storage. The platform includes AI-powered multilingual semantic search using the pgvector extension and Google Gemini embeddings.

### Database Summary

| Database | Purpose | Tables/Structures |
|----------|---------|-------------------|
| **PostgreSQL** | Transactional data, user accounts, products, orders, payments, RBAC, vector search, branch routing | 38+ tables |
| **Redis** | Sessions, caching, cart storage, rate limiting, search cache, branch context | 19+ key patterns |

### Extensions

| Extension | Version | Purpose |
|-----------|---------|---------|
| **pgvector** | 0.5+ | Vector similarity search for semantic product search |
| **pg_trgm** | Built-in | Trigram matching for fuzzy text search |

---

## Database Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SRIBEESonline Application                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────┐    ┌─────────────────┐    ┌────────────┐ │
│   │  Mobile App     │    │  Admin Panel    │    │  Backend   │ │
│   │  (Flutter)      │    │  (React)        │    │  (FastAPI) │ │
│   └────────┬────────┘    └────────┬────────┘    └─────┬──────┘ │
│            │                      │                    │        │
│            └──────────────────────┼────────────────────┘        │
│                                   │                             │
│                        ┌──────────▼──────────┐                  │
│                        │    API Layer        │                  │
│                        │    (FastAPI)        │                  │
│                        └──────────┬──────────┘                  │
│                                   │                             │
│            ┌──────────────────────┼──────────────────────┐      │
│            │                      │                      │      │
│   ┌────────▼────────┐    ┌───────▼───────┐    ┌────────▼────┐ │
│   │  PostgreSQL     │    │    Redis      │    │  File       │ │
│   │  (SQLAlchemy)   │    │   (Cache)     │    │  Storage    │ │
│   │                 │    │               │    │             │ │
│   │  - Users        │    │  - Sessions   │    │  - Images   │ │
│   │  - Orders       │    │  - Carts      │    │  - Assets   │ │
│   │  - Products     │    │  - Rate Limit │    │             │ │
│   │  - Payments     │    │  - Cache      │    │             │ │
│   └─────────────────┘    └───────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## PostgreSQL Schema

### 1. User Management

#### `users`
Primary table for customer accounts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| `password_hash` | VARCHAR(255) | NOT NULL | Argon2id hashed password |
| `full_name` | VARCHAR(100) | NOT NULL | User's display name |
| `phone` | VARCHAR(20) | NULL | Phone number |
| `profile_picture_url` | TEXT | NULL | Avatar URL |
| `is_verified` | BOOLEAN | DEFAULT FALSE | Email verification status |
| `two_factor_enabled` | BOOLEAN | DEFAULT FALSE | 2FA enabled flag |
| `two_factor_secret` | VARCHAR(255) | NULL | TOTP secret |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |
| `last_login` | TIMESTAMP | NULL | Last login timestamp |

**Indexes:**
- `idx_users_email` ON (email)

---

#### `email_verifications`
Stores email verification tokens.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `verification_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `token` | VARCHAR(255) | UNIQUE, NOT NULL | Verification token |
| `expires_at` | TIMESTAMP | NOT NULL | Token expiration |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_email_verifications_token` ON (token)
- `idx_email_verifications_user_id` ON (user_id)

---

#### `password_resets`
Stores password reset tokens.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `reset_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `token` | VARCHAR(255) | UNIQUE, NOT NULL | Reset token |
| `expires_at` | TIMESTAMP | NOT NULL | Token expiration |
| `used` | BOOLEAN | DEFAULT FALSE | Token used flag |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_password_resets_token` ON (token)
- `idx_password_resets_user_id` ON (user_id)

---

#### `sessions`
PostgreSQL session storage (fallback when Redis unavailable).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `session_id` | UUID | PK, DEFAULT gen_random_uuid() | Session identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `refresh_token_hash` | VARCHAR(255) | NOT NULL | Hashed refresh token |
| `ip_address` | INET | NULL | Client IP address |
| `user_agent` | TEXT | NULL | Browser user agent |
| `expires_at` | TIMESTAMP | NOT NULL | Session expiration |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_sessions_user_id` ON (user_id)

---

#### `addresses`
User delivery addresses.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `address_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `address_line1` | VARCHAR(255) | NOT NULL | Street address |
| `address_line2` | VARCHAR(255) | NULL | Apt/Suite number |
| `post_office` | VARCHAR(100) | NOT NULL | Post office name |
| `district` | VARCHAR(100) | NOT NULL | District name |
| `postal_code` | VARCHAR(20) | NOT NULL | ZIP/Postal code |
| `province` | VARCHAR(100) | NOT NULL | Province name |
| `is_default` | BOOLEAN | DEFAULT FALSE | Default address flag |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Indexes:**
- `idx_addresses_user_id` ON (user_id)

---

#### `social_accounts`
OAuth provider connections.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `social_account_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `provider` | VARCHAR(20) | CHECK (provider IN ('google', 'facebook')) | OAuth provider |
| `provider_user_id` | VARCHAR(255) | NOT NULL | Provider's user ID |
| `email` | VARCHAR(255) | NULL | OAuth email |
| `access_token` | TEXT | NULL | OAuth access token |
| `refresh_token` | TEXT | NULL | OAuth refresh token |
| `token_expires_at` | TIMESTAMP | NULL | Token expiration |
| `profile_data` | JSONB | NULL | Raw profile data |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Constraints:**
- `UNIQUE(provider, provider_user_id)`

**Indexes:**
- `idx_social_accounts_user_id` ON (user_id)
- `idx_social_accounts_provider` ON (provider, provider_user_id)

---

### 2. Products & Catalog

#### `categories`
Product category hierarchy.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `category_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `name` | VARCHAR(100) | UNIQUE, NOT NULL | Category name |
| `slug` | VARCHAR(100) | UNIQUE, NOT NULL | URL-friendly slug |
| `description` | TEXT | NULL | Category description |
| `image_url` | TEXT | NULL | Category image |
| `parent_category_id` | UUID | FK → categories(category_id) ON DELETE SET NULL | Parent category |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Indexes:**
- `idx_categories_slug` ON (slug)
- `idx_categories_parent` ON (parent_category_id)

---

#### `products`
Main product catalog.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `product_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Product name |
| `slug` | VARCHAR(255) | UNIQUE, NOT NULL | URL-friendly slug |
| `description` | TEXT | NULL | Full description |
| `short_description` | VARCHAR(500) | NULL | Brief description |
| `category_id` | UUID | FK → categories(category_id) ON DELETE SET NULL | Category reference |
| `price` | DECIMAL(10,2) | NOT NULL, CHECK (price >= 0) | Current price |
| `compare_at_price` | DECIMAL(10,2) | CHECK (>= 0) | Original/compare price |
| `cost_per_unit` | DECIMAL(10,2) | NULL | Cost for margin calculation |
| `sku` | VARCHAR(100) | UNIQUE | Stock keeping unit |
| `barcode` | VARCHAR(100) | NULL | Product barcode |
| `stock_quantity` | INTEGER | DEFAULT 0, CHECK (>= 0) | Available stock |
| `low_stock_threshold` | INTEGER | DEFAULT 10 | Low stock alert level |
| `weight` | DECIMAL(10,2) | NULL | Product weight |
| `weight_unit` | VARCHAR(10) | DEFAULT 'kg' | Weight unit |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `is_featured` | BOOLEAN | DEFAULT FALSE | Featured product flag |
| `rating_average` | DECIMAL(3,2) | DEFAULT 0.00, CHECK (0-5) | Average rating |
| `rating_count` | INTEGER | DEFAULT 0 | Number of ratings |
| `view_count` | INTEGER | DEFAULT 0 | Page view count |
| `sold_count` | INTEGER | DEFAULT 0 | Units sold count |
| `embedding` | VECTOR(768) | NULL | Gemini text-embedding-004 vector for semantic search |
| `embedding_updated_at` | TIMESTAMP | NULL | Last embedding generation timestamp |
| `search_text` | TEXT | NULL | Concatenated searchable text (auto-generated) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Indexes:**
- `idx_products_slug` ON (slug)
- `idx_products_category` ON (category_id)
- `idx_products_sku` ON (sku)
- `idx_products_is_active` ON (is_active)
- `idx_products_is_featured` ON (is_featured)
- `idx_products_embedding` ON (embedding) USING ivfflat WITH (lists = 100) - pgvector similarity search
- `idx_products_search_text` ON (search_text) USING gin(to_tsvector('english', search_text)) - Full-text fallback

---

#### `product_images`
Product image gallery.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `image_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `product_id` | UUID | FK → products(product_id) ON DELETE CASCADE | Product reference |
| `image_url` | TEXT | NOT NULL | Image URL |
| `alt_text` | VARCHAR(255) | NULL | Alt text for accessibility |
| `is_primary` | BOOLEAN | DEFAULT FALSE | Primary image flag |
| `sort_order` | INTEGER | DEFAULT 0 | Display order |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_product_images_product` ON (product_id)

---

#### `product_tags`
Tag definitions for products.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tag_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `name` | VARCHAR(50) | UNIQUE, NOT NULL | Tag name |
| `slug` | VARCHAR(50) | UNIQUE, NOT NULL | URL-friendly slug |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_product_tags_slug` ON (slug)

---

#### `product_tag_relations`
Many-to-many relationship between products and tags.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `product_id` | UUID | FK → products(product_id) ON DELETE CASCADE | Product reference |
| `tag_id` | UUID | FK → product_tags(tag_id) ON DELETE CASCADE | Tag reference |

**Constraints:**
- `PRIMARY KEY (product_id, tag_id)`

---

#### `product_translations`
Multilingual product content for semantic search in Sinhala, Tamil, and Singlish.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `translation_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `product_id` | UUID | FK → products(product_id) ON DELETE CASCADE | Product reference |
| `language_code` | VARCHAR(10) | NOT NULL, CHECK (IN lang_enum) | Language code |
| `name` | VARCHAR(255) | NOT NULL | Translated product name |
| `description` | TEXT | NULL | Translated description |
| `short_description` | VARCHAR(500) | NULL | Translated brief description |
| `keywords` | TEXT[] | NULL | Language-specific search keywords |
| `embedding` | VECTOR(768) | NULL | Language-specific embedding vector |
| `embedding_updated_at` | TIMESTAMP | NULL | Last embedding update |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Language Code Enum:**
- `en` - English (default in products table)
- `si` - Sinhala (සිංහල)
- `ta` - Tamil (தமிழ்)
- `si_lk` - Singlish (transliterated Sinhala)

**Constraints:**
- `UNIQUE(product_id, language_code)`

**Indexes:**
- `idx_product_translations_product` ON (product_id)
- `idx_product_translations_language` ON (language_code)
- `idx_product_translations_embedding` ON (embedding) USING ivfflat WITH (lists = 100)

---

#### `search_analytics`
Tracks search queries for analytics and autocomplete suggestions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `search_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `query` | TEXT | NOT NULL | Original search query |
| `normalized_query` | TEXT | NOT NULL | Lowercase trimmed query |
| `language_detected` | VARCHAR(10) | NULL | Detected query language |
| `search_type` | VARCHAR(20) | NOT NULL | 'semantic', 'keyword', or 'hybrid' |
| `total_results` | INTEGER | DEFAULT 0 | Number of results returned |
| `user_id` | UUID | FK → users(user_id) ON DELETE SET NULL | User reference (if logged in) |
| `session_id` | VARCHAR(255) | NULL | Anonymous session identifier |
| `response_time_ms` | INTEGER | NULL | Search response time in milliseconds |
| `clicked_product_id` | UUID | NULL | Product clicked from results |
| `clicked_position` | INTEGER | NULL | Position of clicked result |
| `filters_applied` | JSONB | DEFAULT '{}' | Applied search filters |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Search timestamp |

**Indexes:**
- `idx_search_analytics_query` ON (normalized_query)
- `idx_search_analytics_created` ON (created_at DESC)
- `idx_search_analytics_user` ON (user_id) WHERE user_id IS NOT NULL
- `idx_search_analytics_language` ON (language_detected)

---
- `PRIMARY KEY (product_id, tag_id)`

---

### 3. Admin & RBAC

#### `admin_users`
Administrative user accounts with role-based access.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `admin_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Admin email |
| `password_hash` | VARCHAR(255) | NOT NULL | Argon2id hashed password |
| `full_name` | VARCHAR(255) | NOT NULL | Display name |
| `role` | VARCHAR(50) | NOT NULL, CHECK (IN role_enum) | Admin role |
| `branch_id` | UUID | FK → branches(branch_id) ON DELETE SET NULL | Assigned branch |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |
| `last_login` | TIMESTAMP | NULL | Last login timestamp |

**Role Enum Values:**
- `super_admin` - Full system access
- `branch_manager` - Branch-level management
- `marketing_manager` - Branch-specific marketing & discount management
- `staff` - Limited operational access
- `support` - Customer support access
- `inventory` - Inventory management access

**Indexes:**
- `idx_admin_users_email` ON (email)
- `idx_admin_users_role` ON (role)
- `idx_admin_users_branch_id` ON (branch_id)

---

#### `branches`
Store branch locations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `branch_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Branch name |
| `code` | VARCHAR(50) | UNIQUE, NOT NULL | Branch code |
| `address` | TEXT | NULL | Street address |
| `post_office` | VARCHAR(100) | NULL | Post office name |
| `district` | VARCHAR(100) | NULL | District name |
| `province` | VARCHAR(100) | NOT NULL | Province name |
| `manager_id` | UUID | FK → admin_users(admin_id) ON DELETE SET NULL | Branch manager |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Indexes:**
- `idx_branches_code` ON (code)
- `idx_branches_manager_id` ON (manager_id)

---

#### `post_office_branch_mapping`
Maps Post Office names to serving branches for address-based branch routing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `mapping_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `post_office` | VARCHAR(100) | UNIQUE, NOT NULL | Post office name (matches `addresses.post_office`) |
| `branch_id` | UUID | FK → branches(branch_id) ON DELETE CASCADE | Serving branch |
| `branch_name` | VARCHAR(255) | NOT NULL | Denormalized branch name for fast reads |
| `district` | VARCHAR(100) | NULL | District context |
| `province` | VARCHAR(100) | NULL | Province context |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active mapping |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Indexes:**
- `idx_po_branch_mapping_post_office` ON (post_office) — Primary lookup index
- `idx_po_branch_mapping_branch` ON (branch_id)
- `idx_po_branch_mapping_district` ON (district)

**Usage:** When a customer selects an address during branch selection, the backend extracts the `post_office` field from that address and looks up this table to find which `branch_id` serves that area. The resolved `branch_id` is stored in the customer's Redis session.

---

#### `role_permissions`
Fine-grained role permissions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `permission_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `role` | VARCHAR(50) | NOT NULL, CHECK (IN role_enum) | Role name |
| `resource` | VARCHAR(100) | NOT NULL | Resource identifier (* = all) |
| `action` | VARCHAR(50) | CHECK (IN action_enum) | CRUD action |
| `is_allowed` | BOOLEAN | DEFAULT TRUE | Permission granted |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Action Enum Values:**
- `create`, `read`, `update`, `delete`

**Indexes:**
- `idx_role_permissions_role` ON (role, resource, action)

---

#### `admin_audit_logs`
Tracks all admin actions for compliance.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `log_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `admin_id` | UUID | FK → admin_users(admin_id) ON DELETE SET NULL | Admin reference |
| `branch_id` | UUID | FK → branches(branch_id) ON DELETE SET NULL | Branch context |
| `action` | VARCHAR(100) | NOT NULL | Action performed |
| `resource_type` | VARCHAR(100) | NOT NULL | Resource type affected |
| `resource_id` | VARCHAR(255) | NULL | Specific resource ID |
| `old_value` | JSONB | NULL | Previous state |
| `new_value` | JSONB | NULL | New state |
| `ip_address` | INET | NULL | Client IP |
| `user_agent` | TEXT | NULL | Browser user agent |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp |

**Indexes:**
- `idx_audit_logs_admin` ON (admin_id)
- `idx_audit_logs_branch` ON (branch_id)
- `idx_audit_logs_action` ON (action, resource_type)
- `idx_audit_logs_created` ON (created_at DESC)

---

### 4. Cart & Coupons

#### `coupons`
Promotional discount codes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `coupon_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `code` | VARCHAR(50) | UNIQUE, NOT NULL | Coupon code |
| `type` | VARCHAR(20) | CHECK (IN type_enum) | Discount type |
| `value` | DECIMAL(10,2) | NOT NULL | Discount value |
| `min_order_amount` | DECIMAL(10,2) | DEFAULT 0 | Minimum order required |
| `max_discount` | DECIMAL(10,2) | NULL | Maximum discount cap |
| `valid_from` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Start validity |
| `valid_until` | TIMESTAMP | NOT NULL | End validity |
| `usage_limit` | INTEGER | NULL (unlimited) | Max usage count |
| `usage_count` | INTEGER | DEFAULT 0 | Current usage |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Type Enum Values:**
- `percentage` - Percentage discount
- `fixed` - Fixed amount discount
- `free_shipping` - Free shipping

**Indexes:**
- `idx_coupons_code` ON (code) WHERE is_active = true
- `idx_coupons_validity` ON (valid_from, valid_until) WHERE is_active = true

---

#### `wishlist_items`
User product wishlists with variant support.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `wishlist_item_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `product_id` | VARCHAR(255) | NOT NULL | Product ID |
| `variant_id` | UUID | FK → product_variants(variant_id) ON DELETE CASCADE | Optional variant |
| `price_at_watch` | DECIMAL(10,2) | NULL | Price when added |
| `added_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Addition timestamp |

**Constraints:**
- `UNIQUE(user_id, product_id, variant_id)`

**Indexes:**
- `idx_wishlist_user` ON (user_id)
- `idx_wishlist_product` ON (product_id)
- `idx_wishlist_variant` ON (variant_id) WHERE variant_id IS NOT NULL
- `idx_wishlist_user_variant` ON (user_id, variant_id) WHERE variant_id IS NOT NULL

---

### 5. Orders & Fulfillment

#### `orders`
Customer order records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `order_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE RESTRICT | Customer reference |
| `order_number` | VARCHAR(50) | UNIQUE, NOT NULL | Display order number |
| `status` | VARCHAR(20) | CHECK (IN status_enum) | Order status |
| `payment_status` | VARCHAR(20) | CHECK (IN payment_enum) | Payment status |
| `total_amount` | DECIMAL(10,2) | NOT NULL | Final total |
| `subtotal` | DECIMAL(10,2) | NOT NULL | Pre-tax/shipping total |
| `tax_amount` | DECIMAL(10,2) | DEFAULT 0 | Tax amount |
| `shipping_amount` | DECIMAL(10,2) | DEFAULT 0 | Shipping cost |
| `discount_amount` | DECIMAL(10,2) | DEFAULT 0 | Discount applied |
| `delivery_address_id` | UUID | FK → addresses(address_id) ON DELETE RESTRICT | Delivery address |
| `delivery_slot_date` | DATE | NULL | Scheduled delivery date |
| `delivery_slot_time` | VARCHAR(20) | NULL | Delivery time slot |
| `payment_id` | UUID | NULL | Payment reference |
| `coupon_code` | VARCHAR(50) | NULL | Applied coupon |
| `notes` | TEXT | NULL | Order notes |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Order timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Status Enum Values:**
- `pending`, `confirmed`, `packed`, `shipped`, `delivered`, `cancelled`

**Payment Status Enum:**
- `pending`, `paid`, `failed`, `refunded`

**Indexes:**
- `idx_orders_user` ON (user_id)
- `idx_orders_status` ON (status)
- `idx_orders_payment_status` ON (payment_status)
- `idx_orders_created_at` ON (created_at DESC)
- `idx_orders_number` ON (order_number)

---

#### `order_items`
Individual items within an order (snapshot at time of order).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `order_item_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `order_id` | UUID | FK → orders(order_id) ON DELETE CASCADE | Order reference |
| `product_id` | VARCHAR(255) | NOT NULL | Product ID snapshot |
| `product_name` | VARCHAR(255) | NOT NULL | Product name snapshot |
| `product_sku` | VARCHAR(100) | NULL | SKU snapshot |
| `product_image` | TEXT | NULL | Image URL snapshot |
| `quantity` | INTEGER | NOT NULL, CHECK (> 0) | Ordered quantity |
| `unit_price` | DECIMAL(10,2) | NOT NULL | Price per unit |
| `subtotal` | DECIMAL(10,2) | NOT NULL | Line item total |
| `tax_amount` | DECIMAL(10,2) | DEFAULT 0 | Line item tax |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Indexes:**
- `idx_order_items_order` ON (order_id)
- `idx_order_items_product` ON (product_id)

---

#### `order_status_history`
Tracks order status changes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `history_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `order_id` | UUID | FK → orders(order_id) ON DELETE CASCADE | Order reference |
| `status` | VARCHAR(20) | NOT NULL | New status |
| `notes` | TEXT | NULL | Status change notes |
| `created_by` | UUID | NULL | Admin who made change |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Change timestamp |

**Indexes:**
- `idx_order_status_history_order` ON (order_id)
- `idx_order_status_history_created_at` ON (created_at DESC)

---

#### `returns`
Return/refund requests.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `return_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `order_id` | UUID | FK → orders(order_id) ON DELETE RESTRICT | Order reference |
| `user_id` | UUID | FK → users(user_id) ON DELETE RESTRICT | User reference |
| `items` | JSONB | NOT NULL | Return items array |
| `reason` | VARCHAR(255) | NOT NULL | Return reason |
| `status` | VARCHAR(20) | CHECK (IN status_enum) | Return status |
| `refund_amount` | DECIMAL(10,2) | NULL | Approved refund |
| `images` | TEXT[] | NULL | Supporting images |
| `pickup_date` | DATE | NULL | Scheduled pickup |
| `admin_notes` | TEXT | NULL | Internal notes |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Request timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Status Enum Values:**
- `requested`, `approved`, `picked_up`, `refunded`, `rejected`

**Items JSONB Structure:**
```json
[
  {
    "product_id": "uuid",
    "quantity": 1,
    "reason": "Damaged item"
  }
]
```

**Indexes:**
- `idx_returns_order` ON (order_id)
- `idx_returns_user` ON (user_id)
- `idx_returns_status` ON (status)
- `idx_returns_created_at` ON (created_at DESC)

---

#### `delivery_slots`
Available delivery time slots.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `slot_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `date` | DATE | NOT NULL | Delivery date |
| `time_slot` | VARCHAR(20) | CHECK (IN slot_enum) | Time slot |
| `time_range` | VARCHAR(50) | NOT NULL | Readable time range |
| `capacity` | INTEGER | DEFAULT 50 | Max orders |
| `booked_count` | INTEGER | DEFAULT 0 | Current bookings |
| `delivery_charge` | DECIMAL(10,2) | DEFAULT 5.99 | Slot fee |
| `is_active` | BOOLEAN | DEFAULT TRUE | Available status |

**Time Slot Enum:**
- `morning` (8AM-12PM)
- `afternoon` (12PM-4PM)
- `evening` (4PM-8PM)

**Constraints:**
- `UNIQUE(date, time_slot)`

**Indexes:**
- `idx_delivery_slots_date` ON (date)
- `idx_delivery_slots_active` ON (is_active) WHERE is_active = true

---

### 6. Payments

#### `payments`
Payment transaction records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `payment_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `order_id` | UUID | FK → orders(order_id) ON DELETE RESTRICT | Order reference |
| `user_id` | UUID | FK → users(user_id) ON DELETE RESTRICT | User reference |
| `amount` | DECIMAL(10,2) | NOT NULL | Payment amount |
| `currency` | VARCHAR(3) | DEFAULT 'USD' | Currency code |
| `payment_method` | VARCHAR(20) | CHECK (IN method_enum) | Payment method |
| `status` | VARCHAR(20) | CHECK (IN status_enum) | Payment status |
| `gateway` | VARCHAR(20) | CHECK (IN gateway_enum) | Payment gateway |
| `transaction_id` | VARCHAR(255) | NULL | Gateway transaction ID |
| `payment_intent_id` | VARCHAR(255) | NULL | Stripe payment intent |
| `gateway_response` | JSONB | NULL | Raw gateway response |
| `refund_amount` | DECIMAL(10,2) | DEFAULT 0 | Refunded amount |
| `refund_reason` | TEXT | NULL | Refund reason |
| `refunded_at` | TIMESTAMP | NULL | Refund timestamp |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Method Enum:**
- `card`, `upi`, `wallet`, `cod`

**Status Enum:**
- `pending`, `processing`, `succeeded`, `failed`, `refunded`

**Gateway Enum:**
- `stripe`, `razorpay`, `manual`

**Indexes:**
- `idx_payments_order` ON (order_id)
- `idx_payments_user` ON (user_id)
- `idx_payments_status` ON (status)
- `idx_payments_transaction` ON (transaction_id)
- `idx_payments_created_at` ON (created_at DESC)

---

#### `saved_cards`
Tokenized saved payment cards.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `card_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `last_four` | VARCHAR(4) | NOT NULL | Last 4 digits |
| `card_brand` | VARCHAR(20) | NOT NULL | Card brand |
| `expiry_month` | INTEGER | CHECK (1-12) | Expiration month |
| `expiry_year` | INTEGER | CHECK (>= 2024) | Expiration year |
| `card_token` | VARCHAR(255) | NOT NULL | Gateway card token |
| `gateway` | VARCHAR(20) | DEFAULT 'stripe' | Payment gateway |
| `is_default` | BOOLEAN | DEFAULT FALSE | Default card flag |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Constraints:**
- `UNIQUE NULLS NOT DISTINCT (user_id, is_default)` - One default per user

**Indexes:**
- `idx_saved_cards_user` ON (user_id)
- `idx_saved_cards_default` ON (user_id, is_default) WHERE is_default = true

---

#### `payment_webhooks`
Webhook event log for payment gateway callbacks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `webhook_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `gateway` | VARCHAR(20) | NOT NULL | Payment gateway |
| `event_type` | VARCHAR(100) | NOT NULL | Webhook event type |
| `event_id` | VARCHAR(255) | NULL | Gateway event ID |
| `payload` | JSONB | NOT NULL | Full webhook payload |
| `processed` | BOOLEAN | DEFAULT FALSE | Processing status |
| `processed_at` | TIMESTAMP | NULL | Processing timestamp |
| `error_message` | TEXT | NULL | Error if failed |
| `retry_count` | INTEGER | DEFAULT 0 | Retry attempts |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Received timestamp |

**Indexes:**
- `idx_webhooks_gateway` ON (gateway)
- `idx_webhooks_event_type` ON (event_type)
- `idx_webhooks_processed` ON (processed)
- `idx_webhooks_created_at` ON (created_at DESC)
- `idx_webhooks_event_id` ON (event_id)

---

### 7. Product Variants

#### `variant_types`
Variant attribute types (Size, Color, Weight, etc.).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `variant_type_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `name` | VARCHAR(50) | UNIQUE, NOT NULL | Type identifier |
| `display_name` | VARCHAR(100) | NOT NULL | UI label |
| `display_order` | INTEGER | DEFAULT 0 | Sort order |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Seeded Values:**
- `size` - "Select Size"
- `color` - "Choose Color"
- `weight` - "Select Weight"
- `pack_size` - "Pack Size"

---

#### `variant_options`
Specific values for variant types.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `variant_option_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `variant_type_id` | UUID | FK → variant_types(variant_type_id) ON DELETE CASCADE | Type reference |
| `value` | VARCHAR(100) | NOT NULL | Option value |
| `display_value` | VARCHAR(100) | NULL | Display label |
| `color_hex` | VARCHAR(7) | NULL | Hex color code |
| `display_order` | INTEGER | DEFAULT 0 | Sort order |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Constraints:**
- `UNIQUE(variant_type_id, value)`

**Indexes:**
- `idx_variant_options_type` ON (variant_type_id)

---

#### `product_variants`
Specific product variations with stock and pricing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `variant_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `product_id` | UUID | FK → products(product_id) ON DELETE CASCADE | Product reference |
| `sku` | VARCHAR(100) | UNIQUE | Variant SKU |
| `name` | VARCHAR(255) | NULL | Variant name |
| `price` | DECIMAL(10,2) | NOT NULL | Variant price |
| `compare_at_price` | DECIMAL(10,2) | NULL | Compare/sale price |
| `cost_per_unit` | DECIMAL(10,2) | NULL | Cost price |
| `stock_quantity` | INTEGER | DEFAULT 0 | Available stock |
| `low_stock_threshold` | INTEGER | DEFAULT 5 | Low stock alert |
| `weight` | DECIMAL(10,3) | NULL | Variant weight |
| `weight_unit` | VARCHAR(10) | DEFAULT 'kg' | Weight unit |
| `image_url` | TEXT | NULL | Variant image |
| `is_default` | BOOLEAN | DEFAULT FALSE | Default variant |
| `is_active` | BOOLEAN | DEFAULT TRUE | Active status |
| `display_order` | INTEGER | DEFAULT 0 | Sort order |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Indexes:**
- `idx_product_variants_product` ON (product_id)
- `idx_product_variants_sku` ON (sku)
- `idx_product_variants_active` ON (is_active)

---

#### `product_variant_options`
Maps variants to their option combinations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `product_variant_option_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `variant_id` | UUID | FK → product_variants(variant_id) ON DELETE CASCADE | Variant reference |
| `variant_type_id` | UUID | FK → variant_types(variant_type_id) ON DELETE CASCADE | Type reference |
| `variant_option_id` | UUID | FK → variant_options(variant_option_id) ON DELETE CASCADE | Option reference |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Constraints:**
- `UNIQUE(variant_id, variant_type_id)` - One option per type per variant

**Indexes:**
- `idx_product_variant_options_variant` ON (variant_id)

---

### 8. Multi-Branch Inventory

#### `branch_inventory`
Branch-specific stock tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `inventory_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `branch_id` | UUID | FK → branches(branch_id) ON DELETE CASCADE | Branch reference |
| `product_id` | VARCHAR(255) | NOT NULL | Product ID |
| `variant_id` | UUID | FK → product_variants(variant_id) ON DELETE CASCADE | Variant reference |
| `stock_quantity` | INTEGER | DEFAULT 0, CHECK (>= 0) | Available stock |
| `reserved_quantity` | INTEGER | DEFAULT 0, CHECK (>= 0) | Reserved stock |
| `low_stock_threshold` | INTEGER | DEFAULT 10 | Alert threshold |
| `reorder_point` | INTEGER | DEFAULT 5 | Reorder trigger |
| `max_stock_level` | INTEGER | DEFAULT 1000 | Max capacity |
| `last_restocked` | TIMESTAMP | NULL | Last restock date |
| `last_sold` | TIMESTAMP | NULL | Last sale date |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Constraints:**
- `UNIQUE(branch_id, product_id, variant_id)`
- `CHECK (reserved_quantity <= stock_quantity)`

**Indexes:**
- `idx_branch_inventory_branch` ON (branch_id)
- `idx_branch_inventory_product` ON (product_id)
- `idx_branch_inventory_variant` ON (variant_id) WHERE variant_id IS NOT NULL
- `idx_branch_inventory_low_stock` ON (branch_id, stock_quantity) WHERE stock_quantity <= low_stock_threshold

---

#### `stock_transfers`
Inter-branch stock transfer requests.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `transfer_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `from_branch_id` | UUID | FK → branches(branch_id) ON DELETE RESTRICT | Source branch |
| `to_branch_id` | UUID | FK → branches(branch_id) ON DELETE RESTRICT | Destination branch |
| `product_id` | VARCHAR(255) | NOT NULL | Product ID |
| `variant_id` | UUID | FK → product_variants(variant_id) ON DELETE CASCADE | Variant reference |
| `quantity` | INTEGER | NOT NULL, CHECK (> 0) | Transfer quantity |
| `status` | VARCHAR(50) | CHECK (IN status_enum) | Transfer status |
| `requested_by` | UUID | FK → admin_users(admin_id) ON DELETE SET NULL | Requester |
| `approved_by` | UUID | FK → admin_users(admin_id) ON DELETE SET NULL | Approver |
| `notes` | TEXT | NULL | Transfer notes |
| `requested_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Request timestamp |
| `approved_at` | TIMESTAMP | NULL | Approval timestamp |
| `completed_at` | TIMESTAMP | NULL | Completion timestamp |

**Status Enum:**
- `pending`, `approved`, `in_transit`, `completed`, `cancelled`

**Constraints:**
- `CHECK (from_branch_id != to_branch_id)`

**Indexes:**
- `idx_transfers_from_branch` ON (from_branch_id)
- `idx_transfers_to_branch` ON (to_branch_id)
- `idx_transfers_status` ON (status)
- `idx_transfers_requested_at` ON (requested_at DESC)

---

#### `branch_settings`
Branch-specific configuration.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `setting_id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `branch_id` | UUID | FK → branches(branch_id) ON DELETE CASCADE | Branch reference |
| `setting_key` | VARCHAR(100) | NOT NULL | Setting name |
| `setting_value` | TEXT | NULL | Setting value |
| `setting_type` | VARCHAR(50) | CHECK (IN type_enum) | Value type |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update |

**Type Enum:**
- `string`, `number`, `boolean`, `json`

**Constraints:**
- `UNIQUE(branch_id, setting_key)`

**Common Settings:**
| Key | Type | Example |
|-----|------|---------|
| `operating_hours` | json | `{"open": "08:00", "close": "21:00"}` |
| `delivery_radius_km` | number | `15` |
| `min_order_amount` | number | `500` |

---

### 9. Notifications

#### `notification_preferences`
User notification preferences.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE, UNIQUE | User reference |
| `push_enabled` | BOOLEAN | DEFAULT TRUE | Push notifications |
| `email_enabled` | BOOLEAN | DEFAULT TRUE | Email notifications |
| `sms_enabled` | BOOLEAN | DEFAULT FALSE | SMS notifications |
| `order_updates` | BOOLEAN | DEFAULT TRUE | Order status alerts |
| `promotions` | BOOLEAN | DEFAULT TRUE | Marketing messages |
| `price_drops` | BOOLEAN | DEFAULT TRUE | Price drop alerts |
| `cart_reminders` | BOOLEAN | DEFAULT TRUE | Abandoned cart reminders |
| `stock_alerts` | BOOLEAN | DEFAULT TRUE | Back in stock alerts |
| `dnd_enabled` | BOOLEAN | DEFAULT FALSE | Do Not Disturb mode |
| `dnd_start_time` | TIME | DEFAULT '22:00:00' | DND start time |
| `dnd_end_time` | TIME | DEFAULT '08:00:00' | DND end time |
| `max_daily_notifications` | INTEGER | DEFAULT 10, CHECK (0-100) | Daily limit |
| `digest_mode` | BOOLEAN | DEFAULT FALSE | Batch into digest |
| `digest_time` | TIME | DEFAULT '09:00:00' | Digest delivery time |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Indexes:**
- `idx_notification_preferences_user` ON (user_id)

---

#### `push_tokens`
Push notification device tokens.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `token` | TEXT | NOT NULL | Push token |
| `platform` | VARCHAR(20) | CHECK (IN ('ios', 'android', 'web')) | Device platform |
| `device_id` | VARCHAR(255) | NULL | Device identifier |
| `device_name` | VARCHAR(255) | NULL | Device name |
| `is_active` | BOOLEAN | DEFAULT TRUE | Token active status |
| `last_used_at` | TIMESTAMPTZ | DEFAULT NOW() | Last activity |
| `failed_count` | INTEGER | DEFAULT 0 | Delivery failures |
| `last_failure_reason` | TEXT | NULL | Last error |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Constraints:**
- `UNIQUE(user_id, token)`

**Indexes:**
- `idx_push_tokens_user` ON (user_id)
- `idx_push_tokens_active` ON (is_active) WHERE is_active = TRUE
- `idx_push_tokens_token` ON (token)

---

#### `notifications`
Notification records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | FK → users(user_id) ON DELETE CASCADE | User reference |
| `type` | notification_type | NOT NULL | Notification type |
| `title` | VARCHAR(255) | NOT NULL | Notification title |
| `body` | TEXT | NOT NULL | Message body |
| `image_url` | TEXT | NULL | Image attachment |
| `action_url` | TEXT | NULL | Deep link URL |
| `action_data` | JSONB | NULL | Action metadata |
| `channel` | notification_channel | NOT NULL | Delivery channel |
| `status` | notification_status | DEFAULT 'pending' | Delivery status |
| `priority` | INTEGER | DEFAULT 5, CHECK (1-10) | Queue priority |
| `scheduled_for` | TIMESTAMPTZ | NULL | Scheduled delivery |
| `sent_at` | TIMESTAMPTZ | NULL | Sent timestamp |
| `delivered_at` | TIMESTAMPTZ | NULL | Delivery timestamp |
| `read_at` | TIMESTAMPTZ | NULL | Read timestamp |
| `error_message` | TEXT | NULL | Error details |
| `retry_count` | INTEGER | DEFAULT 0, CHECK (>= 0) | Retry attempts |
| `metadata` | JSONB | DEFAULT '{}' | Additional data |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `expires_at` | TIMESTAMPTZ | DEFAULT NOW() + 30 days | Expiration |

**Enum Types:**

```sql
CREATE TYPE notification_type AS ENUM (
    'order_placed', 'order_confirmed', 'order_shipped', 'order_delivered',
    'order_cancelled', 'price_drop', 'back_in_stock', 'cart_reminder',
    'promotion', 'account', 'system'
);

CREATE TYPE notification_channel AS ENUM ('push', 'email', 'sms', 'in_app');

CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'delivered', 'read', 'failed');
```

**Indexes:**
- `idx_notifications_user` ON (user_id)
- `idx_notifications_type` ON (type)
- `idx_notifications_status` ON (status)
- `idx_notifications_user_unread` ON (user_id, status) WHERE status IN ('sent', 'delivered')
- `idx_notifications_scheduled` ON (scheduled_for) WHERE scheduled_for IS NOT NULL AND status = 'pending'
- `idx_notifications_created` ON (created_at DESC)
- `idx_notifications_pending` ON (priority, created_at) WHERE status = 'pending'

---

#### `notification_failures`
Dead letter queue for failed notifications.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `notification_id` | UUID | FK → notifications(id) ON DELETE SET NULL | Original notification |
| `user_id` | UUID | FK → users(user_id) ON DELETE SET NULL | User reference |
| `original_payload` | JSONB | NOT NULL | Original data |
| `channel` | notification_channel | NOT NULL | Delivery channel |
| `error_code` | VARCHAR(50) | NULL | Error code |
| `error_message` | TEXT | NOT NULL | Error description |
| `attempt_number` | INTEGER | NOT NULL | Attempt count |
| `max_attempts` | INTEGER | DEFAULT 3 | Max retries |
| `failed_at` | TIMESTAMPTZ | DEFAULT NOW() | Failure timestamp |
| `resolved` | BOOLEAN | DEFAULT FALSE | Resolution status |
| `resolved_at` | TIMESTAMPTZ | NULL | Resolution timestamp |
| `resolution_notes` | TEXT | NULL | Resolution details |

**Indexes:**
- `idx_notification_failures_user` ON (user_id)
- `idx_notification_failures_channel` ON (channel)
- `idx_notification_failures_unresolved` ON (failed_at) WHERE resolved = FALSE

---

#### `notification_analytics`
Aggregated notification performance metrics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| `date` | DATE | NOT NULL | Aggregation date |
| `hour` | INTEGER | NULL | Hour (0-23) for hourly |
| `type` | notification_type | NOT NULL | Notification type |
| `channel` | notification_channel | NOT NULL | Delivery channel |
| `sent_count` | INTEGER | DEFAULT 0 | Sent count |
| `delivered_count` | INTEGER | DEFAULT 0 | Delivered count |
| `read_count` | INTEGER | DEFAULT 0 | Read count |
| `failed_count` | INTEGER | DEFAULT 0 | Failed count |
| `click_through_count` | INTEGER | DEFAULT 0 | Click-through count |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Constraints:**
- `UNIQUE(date, hour, type, channel)`

**Indexes:**
- `idx_notification_analytics_date` ON (date DESC)
- `idx_notification_analytics_type` ON (type)

---

## Redis Data Structures

### Session Management

```
Key Pattern: sessions:{userId}:{sessionId}
Type: HASH
TTL: 7-30 days (based on rememberMe)

Fields:
  - userId: string
  - email: string
  - sessionId: string
  - deviceInfo: string (optional)
  - ipAddress: string
  - userAgent: string
  - createdAt: number (timestamp)
  - lastActivityAt: number (timestamp)
  - expiresAt: number (timestamp)
  - isRememberMe: boolean
```

### User Sessions Index

```
Key Pattern: user:sessions:{userId}
Type: SET
TTL: None (managed by session cleanup)
Members: sessionId strings
```

### Token Blacklisting

```
Key Pattern: blacklist:token:{jti}
Type: STRING
TTL: 24 hours
Value: "1" (exists = blacklisted)

Key Pattern: blacklist:user:{userId}
Type: STRING
TTL: 24 hours
Value: timestamp when blacklisted
```

### User Profile Cache

```
Key Pattern: user:profile:{userId}
Type: HASH
TTL: 15 minutes

Fields:
  - userId: string
  - email: string
  - fullName: string
  - phone: string (optional)
  - profilePictureUrl: string (optional)
  - isVerified: boolean
  - cachedAt: number (timestamp)
```

### Rate Limiting

```
Key Pattern: rate:login:{identifier}
Type: STRING (counter)
TTL: 15 minutes
Value: attempt count

Key Pattern: rate:api:{userId}:{endpoint}
Type: STRING (counter)
TTL: 15 minutes
Value: request count
```

### Refresh Tokens

```
Key Pattern: refresh:{userId}:{sessionId}
Type: STRING
TTL: 7-30 days (based on rememberMe)
Value: hashed refresh token
```

### Customer Branch Context

```
Key Pattern: session:{userId}:branch_context
Type: STRING (JSON)
TTL: 30 days

JSON Structure:
{
  "branch_id": "uuid",
  "branch_name": "Colombo Branch",
  "post_office": "Nugegoda",
  "resolved_at": "2026-02-17T10:30:00Z"
}

Description: Stores the active branch context for a customer session.
Resolved from the customer's selected delivery address via
the post_office_branch_mapping table. All Home Page content
(Quick Sale feed) and product availability are filtered by this branch.
Cleared when the user explicitly switches delivery address.
```

### Shopping Cart

```
Key Pattern: cart:{userId}
Type: STRING (JSON)
TTL: 30 days

JSON Structure:
{
  "items": [
    {
      "productId": "uuid",
      "quantity": 2,
      "price": 29.99,
      "name": "Product Name",
      "image": "url",
      "sku": "SKU-123"
    }
  ],
  "coupon": {
    "code": "SAVE10",
    "discount": 10.00,
    "type": "percentage"
  },
  "totals": {
    "subtotal": 59.98,
    "discount": 6.00,
    "tax": 4.80,
    "shipping": 5.99,
    "total": 64.77
  },
  "updatedAt": 1705766400000
}
```

### Branch Inventory Cache

```
Key Pattern: inventory:branch:{branchId}:product:{productId}
Type: HASH
TTL: 5 minutes

Fields:
  - stockQuantity: number
  - reservedQuantity: number
  - availableQuantity: number
  - lowStockThreshold: number
  - isLowStock: boolean
  - lastUpdated: number (timestamp)
```

```
Key Pattern: inventory:branch:{branchId}:low_stock
Type: SET
TTL: 10 minutes
Members: productId strings with low stock
```

```
Key Pattern: inventory:branch:{branchId}:summary
Type: HASH
TTL: 15 minutes

Fields:
  - branchName: string
  - totalProducts: number
  - totalStock: number
  - lowStockCount: number
  - outOfStockCount: number
  - lastUpdated: number (timestamp)
```

```
Key Pattern: branches:active:list
Type: STRING (JSON array)
TTL: 1 hour
Value: Array of active branch objects
```

### Semantic Search Cache

```
Key Pattern: search:embedding:{hash}
Type: STRING (JSON array of floats)
TTL: 24 hours
Value: 768-dimensional embedding vector from Gemini

Description: Caches query embeddings to avoid redundant API calls.
Hash is SHA256 of normalized query text.
```

```
Key Pattern: search:results:{hash}
Type: STRING (JSON)
TTL: 1 hour
Value: Cached search results

JSON Structure:
{
  "products": [...],
  "totalCount": 45,
  "searchType": "semantic",
  "cachedAt": 1707350400000
}
```

```
Key Pattern: search:popular
Type: SORTED SET
TTL: None (managed by cleanup job)
Members: normalized search queries
Scores: search frequency count

Description: Tracks popular searches for autocomplete suggestions.
Limited to top 1000 queries by periodic cleanup.
```

```
Key Pattern: search:suggestions:{prefix}
Type: LIST
TTL: 15 minutes
Value: Array of autocomplete suggestions

Description: Caches autocomplete results for common query prefixes.
```

---

## Database Indexes

### Performance Critical Indexes

| Table | Index Name | Columns | Type |
|-------|------------|---------|------|
| `users` | `idx_users_email` | email | B-tree |
| `products` | `idx_products_slug` | slug | B-tree |
| `products` | `idx_products_category` | category_id | B-tree |
| `orders` | `idx_orders_user` | user_id | B-tree |
| `orders` | `idx_orders_created_at` | created_at DESC | B-tree |
| `notifications` | `idx_notifications_pending` | priority, created_at | Partial |

### Partial Indexes (Conditional)

```sql
-- Only active coupons
CREATE INDEX idx_coupons_code ON coupons(code) WHERE is_active = true;

-- Only pending notifications
CREATE INDEX idx_notifications_pending ON notifications(priority, created_at) 
    WHERE status = 'pending';

-- Low stock items by branch
CREATE INDEX idx_branch_inventory_low_stock ON branch_inventory(branch_id, stock_quantity) 
    WHERE stock_quantity <= low_stock_threshold;
```

---

## Triggers & Functions

### `update_updated_at_column()`
Automatically updates `updated_at` timestamp on row modification.

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';
```

**Applied to tables:**
- users, addresses, social_accounts
- categories, products
- admin_users, branches
- orders, returns
- payments, coupons
- variant_types, product_variants
- branch_inventory, branch_settings
- notification_preferences

### `ensure_single_default_card()`
Ensures only one default card per user.

```sql
CREATE OR REPLACE FUNCTION ensure_single_default_card()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_default = true THEN
        UPDATE saved_cards
        SET is_default = false
        WHERE user_id = NEW.user_id
          AND card_id != NEW.card_id
          AND is_default = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### `create_notification_preferences_for_new_user()`
Auto-creates notification preferences when a new user is registered.

```sql
CREATE OR REPLACE FUNCTION create_notification_preferences_for_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO notification_preferences (user_id)
    VALUES (NEW.user_id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### `semantic_search()`
Performs vector similarity search using pgvector cosine distance.

```sql
CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding VECTOR(768),
    similarity_threshold FLOAT DEFAULT 0.35,
    max_results INT DEFAULT 50,
    category_filter UUID DEFAULT NULL,
    min_price DECIMAL DEFAULT NULL,
    max_price DECIMAL DEFAULT NULL,
    in_stock_only BOOLEAN DEFAULT TRUE,
    offset_val INT DEFAULT 0
)
RETURNS TABLE (
    product_id UUID,
    name VARCHAR(255),
    slug VARCHAR(255),
    description TEXT,
    short_description VARCHAR(500),
    price DECIMAL(10,2),
    compare_at_price DECIMAL(10,2),
    stock_quantity INT,
    image_url TEXT,
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
         WHERE pi.product_id = p.product_id AND pi.is_primary = true LIMIT 1),
        p.category_id,
        c.name as category_name,
        1 - (p.embedding <=> query_embedding) as similarity_score
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.category_id
    WHERE p.is_active = true
        AND p.embedding IS NOT NULL
        AND 1 - (p.embedding <=> query_embedding) >= similarity_threshold
        AND (category_filter IS NULL OR p.category_id = category_filter)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (NOT in_stock_only OR p.stock_quantity > 0)
    ORDER BY p.embedding <=> query_embedding
    LIMIT max_results
    OFFSET offset_val;
END;
$$ LANGUAGE plpgsql;
```

### `keyword_search_fallback()`
Full-text search fallback when AI embedding service is unavailable.

```sql
CREATE OR REPLACE FUNCTION keyword_search_fallback(
    search_query TEXT,
    max_results INT DEFAULT 50,
    category_filter UUID DEFAULT NULL,
    min_price DECIMAL DEFAULT NULL,
    max_price DECIMAL DEFAULT NULL,
    in_stock_only BOOLEAN DEFAULT TRUE,
    offset_val INT DEFAULT 0
)
RETURNS TABLE (
    product_id UUID,
    name VARCHAR(255),
    slug VARCHAR(255),
    description TEXT,
    short_description VARCHAR(500),
    price DECIMAL(10,2),
    compare_at_price DECIMAL(10,2),
    stock_quantity INT,
    image_url TEXT,
    category_id UUID,
    category_name VARCHAR(100),
    relevance_score FLOAT
) AS $$
DECLARE
    tsquery_val TSQUERY;
BEGIN
    tsquery_val := plainto_tsquery('english', search_query);
    
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
         WHERE pi.product_id = p.product_id AND pi.is_primary = true LIMIT 1),
        p.category_id,
        c.name as category_name,
        ts_rank(to_tsvector('english', COALESCE(p.search_text, '')), tsquery_val)::FLOAT
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.category_id
    WHERE p.is_active = true
        AND to_tsvector('english', COALESCE(p.search_text, '')) @@ tsquery_val
        AND (category_filter IS NULL OR p.category_id = category_filter)
        AND (min_price IS NULL OR p.price >= min_price)
        AND (max_price IS NULL OR p.price <= max_price)
        AND (NOT in_stock_only OR p.stock_quantity > 0)
    ORDER BY ts_rank(to_tsvector('english', COALESCE(p.search_text, '')), tsquery_val) DESC
    LIMIT max_results
    OFFSET offset_val;
END;
$$ LANGUAGE plpgsql;
```

### `update_product_search_text()`
Auto-generates concatenated search text when product is inserted/updated.

```sql
CREATE OR REPLACE FUNCTION update_product_search_text()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_text := CONCAT_WS(' ',
        NEW.name,
        NEW.description,
        NEW.short_description,
        NEW.sku,
        NEW.barcode
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
CREATE TRIGGER trg_update_search_text
    BEFORE INSERT OR UPDATE OF name, description, short_description, sku, barcode
    ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_product_search_text();
```
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Entity Relationship Diagram

```mermaid
erDiagram
    %% ===== USER MANAGEMENT =====
    users ||--o{ addresses : "has"
    users ||--o{ sessions : "has"
    users ||--o{ email_verifications : "has"
    users ||--o{ password_resets : "has"
    users ||--o{ social_accounts : "has"
    users ||--o{ orders : "places"
    users ||--o{ returns : "requests"
    users ||--o{ payments : "makes"
    users ||--o{ saved_cards : "saves"
    users ||--o{ wishlist_items : "saves"
    users ||--|| notification_preferences : "has"
    users ||--o{ push_tokens : "has"
    users ||--o{ notifications : "receives"

    users {
        uuid user_id PK
        varchar email UK
        varchar password_hash
        varchar full_name
        varchar phone
        text profile_picture_url
        boolean is_verified
        boolean two_factor_enabled
        timestamp created_at
        timestamp updated_at
        timestamp last_login
    }

    addresses {
        uuid address_id PK
        uuid user_id FK
        varchar address_line1
        varchar address_line2
        varchar post_office
        varchar district
        varchar postal_code
        varchar province
        boolean is_default
    }

    %% ===== PRODUCTS & CATALOG =====
    categories ||--o{ products : "contains"
    categories ||--o{ categories : "parent_of"
    products ||--o{ product_images : "has"
    products ||--o{ product_tag_relations : "tagged_with"
    product_tags ||--o{ product_tag_relations : "applies_to"
    products ||--o{ product_variants : "has"
    products ||--o{ order_items : "ordered_in"

    categories {
        uuid category_id PK
        varchar name UK
        varchar slug UK
        text description
        text image_url
        uuid parent_category_id FK
        boolean is_active
    }

    products {
        uuid product_id PK
        varchar name
        varchar slug UK
        text description
        uuid category_id FK
        decimal price
        decimal compare_at_price
        varchar sku UK
        integer stock_quantity
        integer low_stock_threshold
        boolean is_active
        boolean is_featured
        decimal rating_average
        integer rating_count
        integer sold_count
    }

    product_images {
        uuid image_id PK
        uuid product_id FK
        text image_url
        varchar alt_text
        boolean is_primary
        integer sort_order
    }

    %% ===== VARIANTS =====
    variant_types ||--o{ variant_options : "has"
    variant_types ||--o{ product_variant_options : "used_in"
    variant_options ||--o{ product_variant_options : "applied_to"
    product_variants ||--o{ product_variant_options : "defined_by"
    product_variants ||--o{ wishlist_items : "watched_in"
    product_variants ||--o{ branch_inventory : "stocked_at"
    product_variants ||--o{ stock_transfers : "transferred"

    variant_types {
        uuid variant_type_id PK
        varchar name UK
        varchar display_name
        integer display_order
        boolean is_active
    }

    variant_options {
        uuid variant_option_id PK
        uuid variant_type_id FK
        varchar value
        varchar display_value
        varchar color_hex
        integer display_order
    }

    product_variants {
        uuid variant_id PK
        uuid product_id FK
        varchar sku UK
        varchar name
        decimal price
        decimal compare_at_price
        integer stock_quantity
        integer low_stock_threshold
        text image_url
        boolean is_default
        boolean is_active
    }

    %% ===== ADMIN & RBAC =====
    admin_users ||--o{ branches : "manages"
    branches ||--o{ admin_users : "employs"
    branches ||--o{ branch_inventory : "stocks"
    branches ||--o{ branch_settings : "configured_with"
    branches ||--o{ stock_transfers : "transfers_from"
    branches ||--o{ stock_transfers : "transfers_to"
    branches ||--o{ post_office_branch_mapping : "serves"
    admin_users ||--o{ admin_audit_logs : "creates"
    admin_users ||--o{ stock_transfers : "requests"
    admin_users ||--o{ stock_transfers : "approves"

    admin_users {
        uuid admin_id PK
        varchar email UK
        varchar password_hash
        varchar full_name
        varchar role
        uuid branch_id FK
        boolean is_active
        timestamp last_login
    }

    branches {
        uuid branch_id PK
        varchar name
        varchar code UK
        text address
        varchar post_office
        varchar district
        varchar province
        uuid manager_id FK
        boolean is_active
    }

    role_permissions {
        uuid permission_id PK
        varchar role
        varchar resource
        varchar action
        boolean is_allowed
    }

    %% ===== ORDERS & FULFILLMENT =====
    orders ||--o{ order_items : "contains"
    orders ||--o{ order_status_history : "tracked_by"
    orders ||--o{ returns : "may_have"
    orders ||--o{ payments : "paid_by"
    addresses ||--o{ orders : "delivered_to"
    delivery_slots ||--o{ orders : "scheduled_in"
    coupons ||--o{ orders : "applied_to"

    orders {
        uuid order_id PK
        uuid user_id FK
        varchar order_number UK
        varchar status
        varchar payment_status
        decimal total_amount
        decimal subtotal
        decimal tax_amount
        decimal shipping_amount
        decimal discount_amount
        uuid delivery_address_id FK
        date delivery_slot_date
        varchar delivery_slot_time
        varchar coupon_code
        timestamp created_at
    }

    order_items {
        uuid order_item_id PK
        uuid order_id FK
        varchar product_id
        varchar product_name
        varchar product_sku
        integer quantity
        decimal unit_price
        decimal subtotal
    }

    order_status_history {
        uuid history_id PK
        uuid order_id FK
        varchar status
        text notes
        uuid created_by
        timestamp created_at
    }

    returns {
        uuid return_id PK
        uuid order_id FK
        uuid user_id FK
        jsonb items
        varchar reason
        varchar status
        decimal refund_amount
    }

    delivery_slots {
        uuid slot_id PK
        date date
        varchar time_slot
        varchar time_range
        integer capacity
        integer booked_count
        decimal delivery_charge
        boolean is_active
    }

    %% ===== PAYMENTS =====
    payments {
        uuid payment_id PK
        uuid order_id FK
        uuid user_id FK
        decimal amount
        varchar currency
        varchar payment_method
        varchar status
        varchar gateway
        varchar transaction_id
        jsonb gateway_response
        decimal refund_amount
    }

    saved_cards {
        uuid card_id PK
        uuid user_id FK
        varchar last_four
        varchar card_brand
        integer expiry_month
        integer expiry_year
        varchar card_token
        varchar gateway
        boolean is_default
    }

    payment_webhooks {
        uuid webhook_id PK
        varchar gateway
        varchar event_type
        varchar event_id
        jsonb payload
        boolean processed
        text error_message
    }

    %% ===== CART & COUPONS =====
    coupons {
        uuid coupon_id PK
        varchar code UK
        varchar type
        decimal value
        decimal min_order_amount
        decimal max_discount
        timestamp valid_from
        timestamp valid_until
        integer usage_limit
        integer usage_count
        boolean is_active
    }

    wishlist_items {
        uuid wishlist_item_id PK
        uuid user_id FK
        varchar product_id
        uuid variant_id FK
        decimal price_at_watch
        timestamp added_at
    }

    %% ===== MULTI-BRANCH INVENTORY =====
    branch_inventory {
        uuid inventory_id PK
        uuid branch_id FK
        varchar product_id
        uuid variant_id FK
        integer stock_quantity
        integer reserved_quantity
        integer low_stock_threshold
        integer reorder_point
        timestamp last_restocked
    }

    stock_transfers {
        uuid transfer_id PK
        uuid from_branch_id FK
        uuid to_branch_id FK
        varchar product_id
        uuid variant_id FK
        integer quantity
        varchar status
        uuid requested_by FK
        uuid approved_by FK
        timestamp requested_at
    }

    branch_settings {
        uuid setting_id PK
        uuid branch_id FK
        varchar setting_key
        text setting_value
        varchar setting_type
    }

    admin_audit_logs {
        uuid log_id PK
        uuid admin_id FK
        uuid branch_id FK
        varchar action
        varchar resource_type
        varchar resource_id
        jsonb old_value
        jsonb new_value
        inet ip_address
    }

    post_office_branch_mapping {
        uuid mapping_id PK
        varchar post_office UK
        uuid branch_id FK
        varchar branch_name
        varchar district
        varchar province
        boolean is_active
    }

    %% ===== NOTIFICATIONS =====
    notification_preferences {
        uuid id PK
        uuid user_id FK UK
        boolean push_enabled
        boolean email_enabled
        boolean sms_enabled
        boolean order_updates
        boolean promotions
        boolean price_drops
        boolean dnd_enabled
        time dnd_start_time
        time dnd_end_time
        integer max_daily_notifications
    }

    push_tokens {
        uuid id PK
        uuid user_id FK
        text token
        varchar platform
        varchar device_id
        boolean is_active
        integer failed_count
    }

    notifications {
        uuid id PK
        uuid user_id FK
        enum type
        varchar title
        text body
        text action_url
        jsonb action_data
        enum channel
        enum status
        integer priority
        timestamptz scheduled_for
        timestamptz sent_at
        timestamptz read_at
    }

    notification_failures {
        uuid id PK
        uuid notification_id FK
        uuid user_id FK
        jsonb original_payload
        varchar error_code
        text error_message
        integer attempt_number
        boolean resolved
    }

    notification_analytics {
        uuid id PK
        date date
        integer hour
        enum type
        enum channel
        integer sent_count
        integer delivered_count
        integer read_count
        integer failed_count
    }
```

---

## Data Retention & TTL

### PostgreSQL Data Retention

| Table | Retention Policy | Cleanup Method |
|-------|------------------|----------------|
| `sessions` | 30 days after expiry | Cron job / scheduled task |
| `email_verifications` | 24 hours after expiry | Triggered cleanup |
| `password_resets` | 1 hour after expiry | Triggered cleanup |
| `payment_webhooks` | 90 days | Archive then delete |
| `admin_audit_logs` | 2 years | Archive to cold storage |
| `notifications` | 30 days (expires_at) | Automatic via expires_at |
| `notification_failures` | 90 days after resolution | Cron job cleanup |
| `notification_analytics` | 1 year | Archive to data warehouse |

### Redis TTL Configuration

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `sessions:*` | 7-30 days | User sessions |
| `cart:*` | 30 days | Shopping carts |
| `rate:*` | 15 minutes | Rate limiting |
| `user:profile:*` | 15 minutes | Profile cache |
| `blacklist:token:*` | 24 hours | Token blacklist |
| `inventory:*:stock` | 5 minutes | Stock cache |
| `inventory:*:summary` | 15 minutes | Summary cache |
| `branches:active:list` | 1 hour | Branch list cache |
| `session:*:branch_context` | 30 days | Customer branch session |

---

## Migration History

| Version | File | Description | Date |
|---------|------|-------------|------|
| 001 | `001_create_users_tables.sql` | User management tables | Initial |
| 001 | `001_create_notification_tables.sql` | Notification system | Initial |
| 002 | `002_create_products_tables.sql` | Products & categories | Initial |
| 003 | `003_create_admin_rbac_tables.sql` | Admin RBAC system | Initial |
| 004 | `004_create_cart_tables.sql` | Coupons & wishlist | Initial |
| 005 | `005_create_order_tables.sql` | Orders & fulfillment | Initial |
| 006 | `006_create_payment_tables.sql` | Payments & cards | Initial |
| 007 | `007_create_product_variants.sql` | Product variants system | Enhancement |
| 008 | `008_enhance_watchlist_table.sql` | Wishlist variant support | Enhancement |
| 009 | `009_multi_branch_rbac.sql` | Multi-branch inventory | Enhancement |
| 010 | `010_enable_semantic_search.sql` | pgvector extension, embeddings, multilingual search | Feb 2026 |
| 011 | `011_create_post_office_branch_mapping.sql` | Post Office → Branch mapping, add province/post_office to branches | Feb 2026 |
| 012 | `012_add_product_discount_and_branch_fields.sql` | Add discount_percentage, discount_price, is_on_sale to products | Feb 2026 |
| 013 | `013_create_branch_inventory.sql` | Branch-specific inventory overrides (price, stock, visibility) | Feb 2026 |
| 014 | `014_create_app_settings.sql` | Runtime app_settings table (splash video URL, etc.) | Feb 2026 |

---

## Notes

1. **UUID Primary Keys**: All tables use UUID v4 for primary keys via `gen_random_uuid()` for security and distributed system compatibility.

2. **Soft Deletes**: Most tables use `is_active` flags rather than hard deletes to maintain referential integrity and audit trails.

3. **JSONB Fields**: Used for flexible data like `gateway_response`, `profile_data`, and `action_data` where schema flexibility is needed.

4. **Timestamps**: All tables include `created_at` with most also having `updated_at` managed by triggers.

5. **Foreign Key Actions**: Carefully chosen ON DELETE actions:
   - `CASCADE` for dependent data (addresses, order items)
   - `RESTRICT` for critical references (orders → users)
   - `SET NULL` for optional references (branches → managers)

6. **Password Security**: All passwords use Argon2id hashing (memory-hard algorithm).

7. **pgvector Extension**: The `vector` extension enables AI-powered semantic search using 768-dimensional embeddings from Google Gemini `text-embedding-004`. IVFFlat indexes with 100 lists provide efficient approximate nearest neighbor (ANN) search with cosine distance (`<=>` operator).

8. **Multilingual Search**: Product search supports English, Sinhala (සිංහල), Tamil (தமிழ்), and Singlish queries through:
   - Gemini embeddings that understand semantic meaning across languages
   - `product_translations` table for localized content
   - Automatic fallback to PostgreSQL full-text search when AI is unavailable

7. **Token Security**: Refresh tokens and session tokens are stored as hashes, never in plaintext.

8. **Schema Organization**: All application tables are created under the `sribees` schema with `search_path` set to `sribees, public`. The `app_settings` table for runtime configuration (splash video URL, etc.) also resides in the `sribees` schema.

9. **MinIO S3 Storage**: Splash video and product assets are stored in MinIO (S3-compatible) at bucket `sribees-assets`. URLs are dynamically rewritten for Android Emulator access (`10.0.2.2:9000` instead of `localhost:9000`).

---

*Document generated for SRIBEESonline E-Commerce Platform*  
*PostgreSQL 15+ | Redis 7+ | FastAPI (Python 3.11+)*
