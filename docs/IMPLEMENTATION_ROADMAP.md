# 🚀 SRIBEESonline Technical Implementation Roadmap
## Industry-Standard Cart, Product & Session Architecture

> **Version**: 2.1 | **Last Updated**: February 17, 2026  
> **Author**: Tech Lead | **Status**: Infrastructure Verified, Implementation In Progress
> **Tech Stack**: FastAPI (Backend) | Flutter (Mobile) | React (Admin)

---

## 📋 Executive Summary

This roadmap outlines the implementation of three critical systems that will bring SRIBEESonline to industry-standard quality:

1. **Redis-Cached Product Details** - Sub-50ms response times
2. **Advanced Cart System** - Redis Hash-based with PostgreSQL sync
3. **Global Session Security** - Token rotation with forced logout

---

## 🏗️ System Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              FLUTTER APP                                        │
├────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │ Riverpod     │   │   Riverpod   │   │   Riverpod   │   │    Dio       │    │
│  │ Query        │   │  CartState   │   │  AuthState   │   │ Interceptor  │    │
│  │ (Products)   │   │ (Optimistic) │   │  (Session)   │   │  (Refresh)   │    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘    │
│         │                  │                  │                  │             │
└─────────┼──────────────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │                  │
          ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐          │
│   │   Product Cache   │  │   Cart Service    │  │  Session Service  │          │
│   │   Dependency      │  │   (Redis-First)   │  │  (Token Rotation) │          │
│   └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘          │
│             │                      │                      │                     │
│             ▼                      ▼                      ▼                     │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                           REDIS LAYER                                    │  │
│   │                                                                          │  │
│   │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐               │  │
│   │  │product:{id}    │ │cart:{userId}   │ │session:{uid}   │               │  │
│   │  │TTL: 1 hour     │ │TTL: 30 days    │ │:{sid}          │               │  │
│   │  │{product JSON}  │ │HASH {items}    │ │TTL: 7 days     │               │  │
│   │  └────────────────┘ └────────────────┘ └────────────────┘               │  │
│   │                                                                          │  │
│   │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐               │  │
│   │  │blacklist:token │ │cart:sync:queue │ │refresh:{uid}   │               │  │
│   │  │:{jti}          │ │LIST [userIds]  │ │:{sid}          │               │  │
│   │  └────────────────┘ └────────────────┘ └────────────────┘               │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                          │
│                                      ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────────┐  │
│   │                       POSTGRESQL (Persistence)                           │  │
│   │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│   │  │   users    │ │   carts    │ │ cart_items │ │  sessions  │            │  │
│   │  └────────────┘ └────────────┘ └────────────┘ └────────────┘            │  │
│   └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Phase Breakdown

### Phase 1: Product Details & Performance
| Task | Priority | Effort | Dependency |
|------|----------|--------|------------|
| Create ProductCacheService | High | 3h | Redis Service |
| Add `/products/:id/similar` endpoint | Medium | 2h | None |
| Implement ProductDetailScreen with TanStack | High | 4h | Cache Service |
| Add prefetching for product lists | Low | 2h | TanStack Setup |

**Expected Outcome**: Product detail loads in <50ms (from Redis), <200ms (from DB)

---

### Phase 2: Advanced Cart System
| Task | Priority | Effort | Dependency |
|------|----------|--------|------------|
| Create RedisCartService with Hashes | Critical | 5h | Redis Service |
| Implement Cart Sync Queue | High | 3h | RedisCartService |
| Create Background Sync Worker | High | 4h | Sync Queue |
| Refactor cart_provider.dart with optimistic UI | High | 4h | Backend Cart |
| Add Cart Conflict Resolution | Medium | 2h | Sync Worker |

**Expected Outcome**: Cart operations in <20ms, PostgreSQL sync async

---

### Phase 3: Global Session Security
| Task | Priority | Effort | Dependency |
|------|----------|--------|------------|
| Implement Refresh Token Rotation | Critical | 4h | Auth Service |
| Add session:deleted pub/sub | High | 2h | Redis |
| Update HTTP client interceptor for forced logout | High | 3h | Backend Changes |
| Add multi-device session management | Medium | 3h | Session Service |

**Expected Outcome**: Zero stale sessions, instant forced logout

---

### Phase 4: Semantic Search Integration
| Task | Priority | Effort | Dependency |
|------|----------|--------|------------|
| Enable pgvector extension | Critical | 1h | PostgreSQL |
| Create embedding service (Gemini) | Critical | 4h | API Key |
| Implement semantic search service | Critical | 5h | Embedding Service |
| Create search API endpoints | High | 3h | Search Service |
| Add Redis caching for embeddings | High | 2h | Redis |
| Implement fallback to keyword search | High | 2h | Search Service |
| Build search suggestions/autocomplete | Medium | 2h | Analytics |

**Expected Outcome**: Multilingual semantic search in <100ms (cached), <500ms (uncached)

---

### Phase 5: Testing & Quality
| Task | Priority | Effort | Dependency |
|------|----------|--------|------------|
| Unit tests: Cart price calculation | High | 2h | Cart Service |
| Unit tests: Quantity limits | High | 1h | Cart Service |
| Unit tests: Embedding service | High | 2h | Embedding Service |
| Integration tests: Cart sync | High | 3h | All Cart |
| Integration tests: Search API | High | 3h | Search Service |
| E2E tests: Product → Cart flow | Medium | 3h | All Systems |

---

## 🔑 Redis Key Schema (Complete)

```python
# Redis key patterns
REDIS_KEYS = {
    # ═══════════════════════════════════════════════════════════════════
    # PRODUCT CACHING
    # ═══════════════════════════════════════════════════════════════════
    "PRODUCT_DETAIL": lambda product_id: f"product:detail:{product_id}",
    "PRODUCT_SIMILAR": lambda product_id: f"product:similar:{product_id}",
    "CATEGORY_PRODUCTS": lambda category_id: f"category:products:{category_id}",
    
    # ═══════════════════════════════════════════════════════════════════
    # SEMANTIC SEARCH (AI-powered)
    # ═══════════════════════════════════════════════════════════════════
    "SEARCH_EMBEDDING": lambda hash: f"search:embedding:{hash}",      # Query embedding
    "SEARCH_RESULTS": lambda hash: f"search:results:{hash}",          # Cached results
    "SEARCH_POPULAR": lambda: "search:popular",                       # ZSET popular queries
    "SEARCH_SUGGESTIONS": lambda prefix: f"search:suggestions:{prefix}",
    
    # ═══════════════════════════════════════════════════════════════════
    # CART SYSTEM (Hash-based for atomic operations)
    # ═══════════════════════════════════════════════════════════════════
    "CART": lambda user_id: f"cart:{user_id}",                    # HASH
    "CART_META": lambda user_id: f"cart:meta:{user_id}",          # coupon, totals
    "CART_SYNC_QUEUE": lambda: "cart:sync:queue",                 # LIST
    "CART_SYNC_LOCK": lambda user_id: f"cart:sync:lock:{user_id}", # Mutex
    
    # ═══════════════════════════════════════════════════════════════════
    # SESSION & AUTH
    # ═══════════════════════════════════════════════════════════════════
    "SESSION": lambda user_id, session_id: f"session:{user_id}:{session_id}",
    "REFRESH_TOKEN": lambda user_id, session_id: f"refresh:{user_id}:{session_id}",
    "BLACKLIST_TOKEN": lambda jti: f"blacklist:token:{jti}",
    
    # ═══════════════════════════════════════════════════════════════════
    # RATE LIMITING
    # ═══════════════════════════════════════════════════════════════════
    "RATE_LIMIT": lambda identifier, endpoint: f"rate:{identifier}:{endpoint}",
}

REDIS_TTL = {
    "PRODUCT_DETAIL": 60 * 60,           # 1 hour
    "PRODUCT_SIMILAR": 6 * 60 * 60,      # 6 hours
    "SEARCH_EMBEDDING": 24 * 60 * 60,    # 24 hours
    "SEARCH_RESULTS": 60 * 60,           # 1 hour
    "SEARCH_SUGGESTIONS": 15 * 60,       # 15 minutes
    "CART": 30 * 24 * 60 * 60,           # 30 days
    "SESSION": 7 * 24 * 60 * 60,         # 7 days
    "REFRESH_TOKEN": 30 * 24 * 60 * 60,  # 30 days
    "BLACKLIST_TOKEN": 24 * 60 * 60,     # 24 hours
}
```

---

## 🛒 Cart Data Model (Redis Hash)

```
┌─────────────────────────────────────────────────────────────────┐
│  KEY: cart:{userId}                                             │
│  TYPE: HASH                                                     │
│  TTL: 30 days (reset on each write)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FIELD: item:{productId}                                        │
│  VALUE: JSON {                                                  │
│      "productId": "prod_123",                                   │
│      "quantity": 2,                                             │
│      "price": 9.99,                                             │
│      "name": "Organic Apples",                                  │
│      "image": "https://...",                                    │
│      "addedAt": 1706400000000                                   │
│  }                                                              │
│                                                                 │
│  FIELD: _meta                                                   │
│  VALUE: JSON {                                                  │
│      "couponCode": "SAVE10",                                    │
│      "couponDiscount": 5.00,                                    │
│      "lastSyncedAt": 1706400000000,                             │
│      "version": 42                                              │
│  }                                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Cart Sync Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Mobile  │     │  Backend │     │   Redis  │     │ Postgres │
│   App    │     │          │     │          │     │          │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ 1. Add to Cart │                │                │
     │───────────────►│                │                │
     │                │ 2. HSET cart   │                │
     │                │───────────────►│                │
     │                │     (20ms)     │                │
     │◄───────────────│ 3. Return OK   │                │
     │  (Optimistic)  │                │                │
     │                │ 4. LPUSH queue │                │
     │                │───────────────►│                │
     │                │                │                │
═════╪════════════════╪════════════════╪════════════════╪═════════
     │          Background Worker (every 5s or on checkout)
     │                │                │                │
     │                │ 5. BRPOP queue │                │
     │                │◄───────────────│                │
     │                │                │                │
     │                │ 6. HGETALL cart│                │
     │                │───────────────►│                │
     │                │◄───────────────│                │
     │                │                │                │
     │                │ 7. UPSERT cart │                │
     │                │───────────────────────────────►│
     │                │                │    (async)     │
     │                │ 8. Update _meta│                │
     │                │───────────────►│                │
     │                │                │                │
```

---

## 🔐 Token Rotation Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Mobile  │     │  Backend │     │   Redis  │
│   App    │     │          │     │          │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     │ 1. Request with expired token   │
     │───────────────►│                │
     │                │                │
     │◄───────────────│ 2. 401 Expired │
     │                │                │
     │ 3. POST /auth/refresh           │
     │    {refreshToken}               │
     │───────────────►│                │
     │                │ 4. GET refresh │
     │                │───────────────►│
     │                │◄───────────────│
     │                │                │
     │                │ 5. Verify & Rotate:
     │                │   - Blacklist old refresh
     │                │   - Generate new tokens
     │                │   - Store new refresh
     │                │───────────────►│
     │                │                │
     │◄───────────────│ 6. {newAccessToken, newRefreshToken}
     │                │                │
     │ 7. Retry original request       │
     │───────────────►│                │
     │                │                │
```

---

## 📊 Performance Targets

| Operation | Current | Target | Method |
|-----------|---------|--------|--------|
| Product Detail Fetch | ~200ms | <50ms | Redis Cache |
| Add to Cart | ~150ms | <30ms | Redis Hash |
| Cart Totals | ~100ms | <10ms | In-memory calc |
| Session Validation | ~50ms | <5ms | Redis lookup |
| Token Refresh | ~300ms | <100ms | Redis-only |

---

## 🚨 Error Handling Matrix

| Error Code | Scenario | Mobile Action |
|------------|----------|---------------|
| `SESSION_REVOKED` | User logged out elsewhere | Force logout, show modal |
| `TOKEN_BLACKLISTED` | Refresh token already used | Force logout |
| `CART_CONFLICT` | Cart modified on another device | Show merge dialog |
| `PRODUCT_UNAVAILABLE` | Item out of stock | Remove from cart, notify |
| `COUPON_EXPIRED` | Coupon no longer valid | Remove coupon, notify |

---

## ✅ Implementation Order

```
Week 1: Foundation
├── Day 1-2: Redis Cart Service (Backend)
├── Day 3: Cart Sync Queue & Worker
├── Day 4-5: Frontend Cart Store Refactor

Week 2: Products & Sessions
├── Day 1-2: Product Cache Service
├── Day 3: ProductDetailScreen with TanStack
├── Day 4-5: Token Rotation & Forced Logout

Week 3: Quality
├── Day 1-2: Unit Tests
├── Day 3-4: Integration Tests
├── Day 5: Performance Testing & Optimization
```

---

## 🎯 Success Criteria

- [ ] Cart add/remove/update < 30ms (Redis)
- [ ] Product detail load < 50ms (cached)
- [ ] Zero stale sessions after logout
- [ ] Cart persists across sessions
- [ ] Unit test coverage > 80% for Cart logic
- [ ] All API errors handled gracefully

---

## 🐳 Infrastructure Status (February 17, 2026)

### Completed
- [x] Docker Compose setup with 4 core services (Postgres+pgvector, Redis, MinIO, FastAPI)
- [x] Database schema initialized (16 tables in `sribees` schema)
- [x] SQL migrations 001-014 applied successfully
- [x] MinIO bucket `sribees-assets` with public-read policy
- [x] Splash video stored and URL seeded in `app_settings`
- [x] Android emulator URL rewriting (`10.0.2.2` support)
- [x] Jenkins CI/CD pipeline created (`Jenkinsfile`)
- [x] Flutter mobile app verified on Android emulator
- [x] End-to-end `/api/v1/app/splash-config` returns correct emulator-friendly URL

### Pending
- [ ] Admin dashboard TypeScript errors (blocked - not critical for backend development)
- [ ] Firebase configuration for push notifications
- [ ] Custom Sinhala/Tamil font assets for Flutter app
- [ ] Production deployment (AWS/Kubernetes)
