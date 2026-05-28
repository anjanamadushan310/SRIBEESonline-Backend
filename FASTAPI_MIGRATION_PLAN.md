# SRIBEESonline Backend Migration: Node.js/Express to FastAPI

**Document Version:** 2.0  
**Migration Lead:** Tech Lead  
**Date Created:** January 30, 2026  
**Status:** ✅ COMPLETED (February 2026)  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Target Architecture](#target-architecture)
4. [Migration Strategy](#migration-strategy)
5. [Technology Stack Mapping](#technology-stack-mapping)
6. [Project Structure](#project-structure)
7. [Phase-wise Migration Plan](#phase-wise-migration-plan)
8. [API Endpoint Mapping](#api-endpoint-mapping)
9. [Database Migration Strategy](#database-migration-strategy)
10. [Risk Assessment & Mitigation](#risk-assessment--mitigation)
11. [Testing Strategy](#testing-strategy)
12. [Rollback Plan](#rollback-plan)
13. [Timeline & Resources](#timeline--resources)

---

## Executive Summary

### Overview
This document outlines the completed migration of the SRIBEESonline e-commerce backend from **Node.js/Express.js (TypeScript)** to **Python/FastAPI**. The migration was completed successfully, improving performance and developer productivity.

### Key Benefits of Migration
| Benefit | Description |
|---------|-------------|
| **Performance** | FastAPI is one of the fastest Python frameworks (comparable to Node.js) |
| **Type Safety** | Native Python type hints with Pydantic validation |
| **Auto Documentation** | Built-in OpenAPI/Swagger documentation |
| **Async Support** | Native async/await support for high concurrency |
| **Data Science Ready** | Seamless integration with ML/AI libraries |
| **Developer Experience** | Less boilerplate, cleaner code structure |

### Migration Scope
- **Total Modules:** 8 core modules ✅
- **API Endpoints:** ~50+ endpoints ✅
- **Database:** PostgreSQL 15+ (unchanged), Redis 7+ (unchanged)
- **Duration:** Completed

---

## Current Architecture Analysis

### Technology Stack (Previous - Node.js)
```
┌─────────────────────────────────────────────────────────────────┐
│                     PREVIOUS STACK (Node.js)                     │
├─────────────────────────────────────────────────────────────────┤
│  Runtime      │ Node.js 20+ LTS                                 │
│  Framework    │ Express.js 4.21+                                │
│  Language     │ TypeScript 5.6+                                 │
│  Auth         │ jsonwebtoken + argon2                           │
│  Validation   │ Zod 3.23+                                       │
│  ORM/DB       │ pg-promise 11+ (PostgreSQL)                     │
│  Cache        │ ioredis 5+ (Redis)                              │
│  Security     │ helmet + cors + express-rate-limit              │
│  Testing      │ Jest + Supertest                                │
└─────────────────────────────────────────────────────────────────┘
```

### Current Module Structure
```
backend/src/
├── app.ts                    # Express app configuration
├── index.ts                  # Server entry point
├── config/                   # Configuration management
│   ├── index.ts              # Environment config
│   └── database.ts           # PostgreSQL connection
├── database/
│   ├── migrations/           # SQL migration files
│   └── seeds/                # Seed data
├── modules/
│   ├── auth/                 # Authentication (Customer + Admin)
│   │   ├── controllers/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── types/
│   │   └── validators/
│   ├── products/             # Product catalog
│   ├── categories/           # Category management
│   ├── cart/                 # Cart + Wishlist
│   ├── orders/               # Order management
│   ├── payments/             # Payment processing
│   ├── notifications/        # Push + Email notifications
│   └── admin/                # Admin operations
├── services/                 # Shared services
├── shared/
│   ├── middleware/           # Auth, RBAC, Rate limiting
│   └── utils/                # Logger, helpers
└── types/                    # Global type definitions
```

### Current API Endpoints Summary

| Module | Endpoints | Auth Required | Description |
|--------|-----------|---------------|-------------|
| Auth | 8 | Mixed | User registration, login, password reset |
| Admin Auth | 6 | Admin | Admin authentication + RBAC |
| Products | 2+ | Public | Product catalog CRUD |
| Categories | 4+ | Mixed | Category management |
| Cart | 10 | Customer | Redis-backed cart operations |
| Wishlist | 7 | Customer | Wishlist with Redis caching |
| Orders | 8 | Customer | Order lifecycle management |
| Payments | 8 | Customer | Payment processing + Stripe |
| Notifications | 4+ | Customer | Push notifications |
| Delivery Slots | 4+ | Customer | Delivery scheduling |

---

## Target Architecture

### Technology Stack (FastAPI)
```
┌─────────────────────────────────────────────────────────────────┐
│                     TARGET STACK (FastAPI)                       │
├─────────────────────────────────────────────────────────────────┤
│  Runtime      │ Python 3.11+                                    │
│  Framework    │ FastAPI 0.109+                                  │
│  ASGI Server  │ Uvicorn + Gunicorn                              │
│  Auth         │ python-jose[cryptography] + passlib[argon2]     │
│  Validation   │ Pydantic v2                                     │
│  ORM/DB       │ SQLAlchemy 2.0+ (async) / asyncpg               │
│  Cache        │ redis-py (async) / aioredis                     │
│  Security     │ FastAPI Security + slowapi                      │
│  Testing      │ pytest + pytest-asyncio + httpx                 │
│  Migrations   │ Alembic                                         │
│  Task Queue   │ Celery + Redis (optional)                       │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Diagram (Target)
```
┌─────────────────────────────────────────────────────────────────┐
│                      SRIBEESonline FastAPI Backend                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────┐    ┌─────────────────┐                    │
│   │  Mobile App     │    │  Admin Panel    │                    │
│   │  (React Native) │    │  (React)        │                    │
│   └────────┬────────┘    └────────┬────────┘                    │
│            │                      │                              │
│            └──────────────────────┘                              │
│                        │                                         │
│           ┌────────────▼────────────┐                           │
│           │   NGINX / Load Balancer │                           │
│           └────────────┬────────────┘                           │
│                        │                                         │
│           ┌────────────▼────────────┐                           │
│           │   Uvicorn ASGI Server   │                           │
│           │   (Multiple Workers)    │                           │
│           └────────────┬────────────┘                           │
│                        │                                         │
│           ┌────────────▼────────────┐                           │
│           │    FastAPI Application  │                           │
│           │  ┌───────────────────┐  │                           │
│           │  │   API Router      │  │                           │
│           │  │  /api/v1/*        │  │                           │
│           │  └─────────┬─────────┘  │                           │
│           │            │            │                           │
│           │  ┌─────────▼─────────┐  │                           │
│           │  │  Middleware Stack │  │                           │
│           │  │ - CORS            │  │                           │
│           │  │ - Rate Limiting   │  │                           │
│           │  │ - Auth/RBAC       │  │                           │
│           │  │ - Request Logging │  │                           │
│           │  └─────────┬─────────┘  │                           │
│           │            │            │                           │
│           │  ┌─────────▼─────────┐  │                           │
│           │  │ Dependency Inject │  │                           │
│           │  │ - DB Sessions     │  │                           │
│           │  │ - Redis Client    │  │                           │
│           │  │ - Current User    │  │                           │
│           │  └─────────┬─────────┘  │                           │
│           │            │            │                           │
│           └────────────┼────────────┘                           │
│                        │                                         │
│     ┌──────────────────┼──────────────────┐                     │
│     │                  │                  │                     │
│ ┌───▼───┐        ┌─────▼─────┐      ┌─────▼─────┐              │
│ │ PostgreSQL     │   Redis   │      │   Celery  │              │
│ │ (asyncpg)      │ (aioredis)│      │  Workers  │              │
│ │               │           │      │ (optional)│              │
│ └───────┘        └───────────┘      └───────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Migration Strategy

### Approach: **Strangler Fig Pattern** (Recommended)

We'll use the **Strangler Fig Pattern** for gradual migration:

1. **Phase 1:** Set up FastAPI alongside Express (both running)
2. **Phase 2:** Migrate modules one by one to FastAPI
3. **Phase 3:** Route traffic gradually to FastAPI
4. **Phase 4:** Deprecate and remove Express backend

```
                    ┌─────────────────────────────────────────┐
                    │              API Gateway                 │
                    │         (NGINX / Load Balancer)         │
                    └─────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
   ┌──────────▼──────────┐                     ┌─────────────▼───────────┐
   │   Express Backend   │                     │    FastAPI Backend      │
   │   (Legacy - Port    │                     │    (New - Port 8000)    │
   │    3000)            │                     │                         │
   │                     │                     │                         │
   │ - /api/v1/products  │ ──────────────────▶ │ - /api/v1/auth ✓       │
   │ - /api/v1/orders    │     Migrate         │ - /api/v1/products ✓   │
   │ - /api/v1/payments  │     Gradually       │ - /api/v1/cart ✓       │
   └─────────────────────┘                     └─────────────────────────┘
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      │
                          ┌───────────▼───────────┐
                          │   Shared Databases     │
                          │  PostgreSQL + Redis    │
                          └───────────────────────┘
```

### Migration Order (Priority-Based)
| Order | Module | Priority | Complexity | Dependencies |
|-------|--------|----------|------------|--------------|
| 1 | Core Setup + Config | Critical | Low | None |
| 2 | Auth (Customer) | Critical | Medium | Core |
| 3 | Products | High | Low | Auth |
| 4 | Categories | High | Low | Auth |
| 5 | Cart | High | Medium | Auth, Products |
| 6 | Wishlist | Medium | Medium | Auth, Products |
| 7 | Orders | High | High | Auth, Cart, Products |
| 8 | Payments | High | High | Auth, Orders |
| 9 | Admin Auth + RBAC | Medium | High | Core |
| 10 | Notifications | Medium | Medium | Auth |
| 11 | Admin Features | Low | Medium | Admin Auth |

---

## Technology Stack Mapping

### Library/Package Equivalents

| Node.js/Express | FastAPI/Python | Purpose |
|-----------------|----------------|---------|
| `express` | `fastapi` | Web framework |
| `typescript` | Python type hints + Pydantic | Type safety |
| `zod` | `pydantic v2` | Schema validation |
| `jsonwebtoken` | `python-jose[cryptography]` | JWT handling |
| `argon2` | `passlib[argon2]` | Password hashing |
| `pg-promise` | `asyncpg` + `SQLAlchemy 2.0` | PostgreSQL client |
| `ioredis` | `redis-py[hiredis]` (async) | Redis client |
| `helmet` | FastAPI security headers | Security headers |
| `cors` | `fastapi.middleware.cors` | CORS handling |
| `express-rate-limit` | `slowapi` | Rate limiting |
| `express-validator` | Pydantic validators | Input validation |
| `winston` | `loguru` / `structlog` | Logging |
| `nodemailer` | `fastapi-mail` / `aiosmtplib` | Email sending |
| `stripe` | `stripe-python` | Payment processing |
| `uuid` | `uuid` (stdlib) | UUID generation |
| `jest` | `pytest` + `pytest-asyncio` | Testing |
| `supertest` | `httpx` (async client) | API testing |
| `dotenv` | `pydantic-settings` | Environment config |
| `ts-node-dev` | `uvicorn --reload` | Hot reloading |

### Code Pattern Mapping

#### Express Route → FastAPI Route
```typescript
// Express (Before)
router.post('/register', authLimiter, AuthController.register);
router.get('/:id', ProductController.getProductById);
```

```python
# FastAPI (After)
@router.post("/register", dependencies=[Depends(auth_limiter)])
async def register(data: RegisterDTO, db: AsyncSession = Depends(get_db)):
    return await AuthService.register(data, db)

@router.get("/{product_id}")
async def get_product_by_id(product_id: UUID, db: AsyncSession = Depends(get_db)):
    return await ProductService.get_by_id(product_id, db)
```

#### Express Middleware → FastAPI Dependency
```typescript
// Express (Before)
router.use(authenticate);
router.get('/cart', CartController.getCart);
```

```python
# FastAPI (After)
@router.get("/cart")
async def get_cart(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    return await CartService.get_cart(current_user.id, redis, db)
```

#### Zod Schema → Pydantic Model
```typescript
// Zod (Before)
const RegisterSchema = z.object({
    email: z.string().email(),
    password: z.string().min(8),
    fullName: z.string().min(2).max(100),
});
```

```python
# Pydantic (After)
from pydantic import BaseModel, EmailStr, Field

class RegisterDTO(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    
    class Config:
        str_strip_whitespace = True
```

---

## Project Structure

### FastAPI Project Layout
```
fastapi_backend/
├── alembic/                          # Database migrations
│   ├── versions/                     # Migration files
│   ├── env.py                        # Alembic environment
│   └── alembic.ini                   # Alembic config
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py               # Pydantic Settings
│   │   └── database.py               # DB connection setup
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py               # JWT, password hashing
│   │   ├── dependencies.py           # Common dependencies
│   │   └── exceptions.py             # Custom exceptions
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── cors.py                   # CORS configuration
│   │   ├── rate_limiter.py           # Rate limiting
│   │   ├── logging.py                # Request logging
│   │   └── error_handler.py          # Global error handling
│   ├── models/                       # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py                   # Base model class
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── category.py
│   │   ├── order.py
│   │   ├── cart.py
│   │   ├── payment.py
│   │   ├── admin.py
│   │   └── notification.py
│   ├── schemas/                      # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── category.py
│   │   ├── order.py
│   │   ├── cart.py
│   │   ├── payment.py
│   │   └── common.py                 # Shared schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                   # Route dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # Main v1 router
│   │       ├── auth.py               # Auth endpoints
│   │       ├── admin_auth.py         # Admin auth endpoints
│   │       ├── products.py           # Product endpoints
│   │       ├── categories.py         # Category endpoints
│   │       ├── cart.py               # Cart endpoints
│   │       ├── wishlist.py           # Wishlist endpoints
│   │       ├── orders.py             # Order endpoints
│   │       ├── payments.py           # Payment endpoints
│   │       └── notifications.py      # Notification endpoints
│   ├── services/                     # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── product_service.py
│   │   ├── category_service.py
│   │   ├── cart_service.py
│   │   ├── wishlist_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── notification_service.py
│   │   ├── email_service.py
│   │   └── redis_service.py
│   ├── repositories/                 # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py                   # Base repository
│   │   ├── user_repository.py
│   │   ├── product_repository.py
│   │   ├── order_repository.py
│   │   └── ...
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                 # Logging setup
│       ├── pagination.py             # Pagination helpers
│       └── helpers.py                # Utility functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_cart.py
│   ├── test_orders.py
│   └── ...
├── scripts/
│   ├── seed_data.py                  # Database seeding
│   └── run_migrations.py             # Migration runner
├── .env.example                      # Environment template
├── .gitignore
├── docker-compose.yml                # Docker setup
├── Dockerfile                        # Container build
├── pyproject.toml                    # Poetry config
├── requirements.txt                  # Pip requirements
└── README.md                         # Documentation
```

---

## Phase-wise Migration Plan

### Phase 1: Foundation Setup (Week 1-2)

#### Goals
- Set up FastAPI project structure
- Configure database connections (PostgreSQL + Redis)
- Implement core middleware and utilities
- Set up testing infrastructure

#### Tasks
| Task | Description | Owner | Est. Hours |
|------|-------------|-------|------------|
| 1.1 | Initialize FastAPI project with Poetry | Backend | 2 |
| 1.2 | Configure Pydantic Settings | Backend | 4 |
| 1.3 | Set up async PostgreSQL (asyncpg + SQLAlchemy) | Backend | 8 |
| 1.4 | Set up async Redis client | Backend | 4 |
| 1.5 | Implement CORS middleware | Backend | 2 |
| 1.6 | Implement rate limiting (slowapi) | Backend | 4 |
| 1.7 | Implement request logging | Backend | 4 |
| 1.8 | Implement global error handler | Backend | 4 |
| 1.9 | Set up Alembic for migrations | Backend | 4 |
| 1.10 | Set up pytest + fixtures | QA | 8 |
| 1.11 | Docker setup | DevOps | 4 |
| 1.12 | CI/CD pipeline update | DevOps | 8 |

#### Deliverables
- [ ] Running FastAPI server
- [ ] Database connections working
- [ ] Basic middleware functional
- [ ] Test framework ready
- [ ] Docker compose updated

---

### Phase 2: Authentication Module (Week 3-4)

#### Goals
- Migrate customer authentication
- Implement JWT token management
- Set up session handling with Redis

#### API Endpoints to Migrate
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/auth/verify-email` | POST | Email verification |
| `/api/v1/auth/resend-verification` | POST | Resend verification email |
| `/api/v1/auth/forgot-password` | POST | Request password reset |
| `/api/v1/auth/reset-password` | POST | Reset password |
| `/api/v1/auth/refresh-token` | POST | Refresh JWT token |
| `/api/v1/auth/logout` | POST | User logout |

#### Tasks
| Task | Description | Owner | Est. Hours |
|------|-------------|-------|------------|
| 2.1 | Create User SQLAlchemy model | Backend | 4 |
| 2.2 | Create Auth Pydantic schemas | Backend | 4 |
| 2.3 | Implement password hashing (argon2) | Backend | 2 |
| 2.4 | Implement JWT generation/validation | Backend | 8 |
| 2.5 | Implement auth service | Backend | 16 |
| 2.6 | Create auth router/endpoints | Backend | 8 |
| 2.7 | Implement auth dependencies | Backend | 4 |
| 2.8 | Email verification service | Backend | 8 |
| 2.9 | Write auth tests | QA | 16 |
| 2.10 | Integration testing | QA | 8 |

#### Deliverables
- [ ] User registration working
- [ ] Login/logout functional
- [ ] JWT authentication working
- [ ] Email verification integrated
- [ ] 90%+ test coverage

---

### Phase 3: Products & Categories (Week 5-6)

#### Goals
- Migrate product catalog
- Migrate category management
- Implement search and filtering

#### API Endpoints to Migrate
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/products` | GET | List products (paginated) |
| `/api/v1/products/{id}` | GET | Get product by ID |
| `/api/v1/products/search` | GET | Search products |
| `/api/v1/categories` | GET | List categories |
| `/api/v1/categories/{id}` | GET | Get category by ID |
| `/api/v1/categories/{id}/products` | GET | Get products by category |

#### Tasks
| Task | Description | Owner | Est. Hours |
|------|-------------|-------|------------|
| 3.1 | Create Product/Category SQLAlchemy models | Backend | 8 |
| 3.2 | Create Product/Category Pydantic schemas | Backend | 4 |
| 3.3 | Implement product service | Backend | 12 |
| 3.4 | Implement category service | Backend | 8 |
| 3.5 | Create product router | Backend | 8 |
| 3.6 | Create category router | Backend | 4 |
| 3.7 | Implement search functionality | Backend | 8 |
| 3.8 | Implement pagination helper | Backend | 4 |
| 3.9 | Write product/category tests | QA | 16 |

---

### Phase 4: Cart & Wishlist (Week 7-8)

#### Goals
- Migrate Redis-backed cart
- Migrate wishlist functionality
- Implement cart-PostgreSQL sync

#### API Endpoints to Migrate
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/cart` | GET | Get user cart |
| `/api/v1/cart/items` | POST | Add item to cart |
| `/api/v1/cart/items/{productId}` | PUT | Update item quantity |
| `/api/v1/cart/items/{productId}` | DELETE | Remove item |
| `/api/v1/cart` | DELETE | Clear cart |
| `/api/v1/cart/coupon` | POST | Apply coupon |
| `/api/v1/cart/coupon` | DELETE | Remove coupon |
| `/api/v1/wishlist` | GET | Get wishlist |
| `/api/v1/wishlist/items` | POST | Add to wishlist |
| `/api/v1/wishlist/items/{productId}` | DELETE | Remove from wishlist |

#### Tasks
| Task | Description | Owner | Est. Hours |
|------|-------------|-------|------------|
| 4.1 | Create Cart/Wishlist Pydantic schemas | Backend | 4 |
| 4.2 | Implement Redis cart service | Backend | 16 |
| 4.3 | Implement cart-PostgreSQL sync | Backend | 8 |
| 4.4 | Create cart router | Backend | 8 |
| 4.5 | Implement wishlist service | Backend | 12 |
| 4.6 | Create wishlist router | Backend | 4 |
| 4.7 | Coupon validation logic | Backend | 8 |
| 4.8 | Write cart/wishlist tests | QA | 16 |

---

### Phase 5: Orders & Payments (Week 9-10)

#### Goals
- Migrate order management
- Migrate payment processing (Stripe)
- Implement order tracking

#### API Endpoints to Migrate
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/orders` | POST | Create order |
| `/api/v1/orders` | GET | Get user orders |
| `/api/v1/orders/{id}` | GET | Get order by ID |
| `/api/v1/orders/{id}/cancel` | PUT | Cancel order |
| `/api/v1/orders/{id}/tracking` | GET | Get tracking info |
| `/api/v1/payments/initiate` | POST | Initiate payment |
| `/api/v1/payments/confirm` | POST | Confirm payment |
| `/api/v1/payments/history` | GET | Payment history |
| `/api/v1/delivery/slots` | GET | Available slots |

#### Tasks
| Task | Description | Owner | Est. Hours |
|------|-------------|-------|------------|
| 5.1 | Create Order/Payment SQLAlchemy models | Backend | 8 |
| 5.2 | Create Order/Payment Pydantic schemas | Backend | 6 |
| 5.3 | Implement order service | Backend | 20 |
| 5.4 | Implement Stripe payment service | Backend | 16 |
| 5.5 | Create order router | Backend | 8 |
| 5.6 | Create payment router | Backend | 8 |
| 5.7 | Delivery slot service | Backend | 8 |
| 5.8 | Order status webhooks | Backend | 8 |
| 5.9 | Write order/payment tests | QA | 20 |

---

### Phase 6: Admin & RBAC (Week 11)

#### Goals
- Migrate admin authentication
- Implement multi-branch RBAC
- Migrate admin operations

#### API Endpoints to Migrate
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/auth/login` | POST | Admin login |
| `/api/v1/admin/auth/logout` | POST | Admin logout |
| `/api/v1/admin/auth/refresh` | POST | Refresh token |
| `/api/v1/orders/admin/all` | GET | All orders (admin) |
| `/api/v1/orders/{id}/status` | PUT | Update order status |
| `/api/v1/payments/{id}/refund` | POST | Process refund |

#### Tasks
| Task | Description | Owner | Est. Hours |
|------|-------------|-------|------------|
| 6.1 | Create Admin SQLAlchemy models | Backend | 6 |
| 6.2 | Implement RBAC middleware | Backend | 12 |
| 6.3 | Implement admin auth service | Backend | 12 |
| 6.4 | Create admin auth router | Backend | 6 |
| 6.5 | Branch isolation logic | Backend | 8 |
| 6.6 | Audit logging | Backend | 8 |
| 6.7 | Write admin tests | QA | 12 |

---

### Phase 7: Notifications & Final Integration (Week 12)

#### Goals
- Migrate push notifications
- Migrate email service
- Final integration testing
- Performance optimization

#### Tasks
| Task | Description | Owner | Est. Hours |
|------|-------------|-------|------------|
| 7.1 | Implement notification service | Backend | 12 |
| 7.2 | Expo push notifications | Backend | 8 |
| 7.3 | Email service (fastapi-mail) | Backend | 8 |
| 7.4 | End-to-end testing | QA | 20 |
| 7.5 | Performance testing | QA | 8 |
| 7.6 | Security audit | Security | 8 |
| 7.7 | Documentation update | All | 8 |
| 7.8 | Deployment preparation | DevOps | 8 |

---

## API Endpoint Mapping

### Complete Endpoint Reference

```yaml
# Authentication (Customer)
POST   /api/v1/auth/register           → app.api.v1.auth.register
POST   /api/v1/auth/login              → app.api.v1.auth.login
POST   /api/v1/auth/verify-email       → app.api.v1.auth.verify_email
POST   /api/v1/auth/resend-verification → app.api.v1.auth.resend_verification
POST   /api/v1/auth/forgot-password    → app.api.v1.auth.forgot_password
POST   /api/v1/auth/reset-password     → app.api.v1.auth.reset_password
POST   /api/v1/auth/refresh-token      → app.api.v1.auth.refresh_token
POST   /api/v1/auth/logout             → app.api.v1.auth.logout

# Admin Authentication
POST   /api/v1/admin/auth/login        → app.api.v1.admin_auth.login
POST   /api/v1/admin/auth/logout       → app.api.v1.admin_auth.logout
POST   /api/v1/admin/auth/refresh      → app.api.v1.admin_auth.refresh_token
GET    /api/v1/admin/auth/me           → app.api.v1.admin_auth.get_current_admin

# Products
GET    /api/v1/products                → app.api.v1.products.list_products
GET    /api/v1/products/{id}           → app.api.v1.products.get_product
GET    /api/v1/products/search         → app.api.v1.products.search_products

# Categories
GET    /api/v1/categories              → app.api.v1.categories.list_categories
GET    /api/v1/categories/{id}         → app.api.v1.categories.get_category
GET    /api/v1/categories/{id}/products → app.api.v1.categories.get_category_products

# Cart
GET    /api/v1/cart                    → app.api.v1.cart.get_cart
GET    /api/v1/cart/count              → app.api.v1.cart.get_item_count
POST   /api/v1/cart/items              → app.api.v1.cart.add_item
PUT    /api/v1/cart/items/{productId}  → app.api.v1.cart.update_item
DELETE /api/v1/cart/items/{productId}  → app.api.v1.cart.remove_item
DELETE /api/v1/cart                    → app.api.v1.cart.clear_cart
POST   /api/v1/cart/coupon             → app.api.v1.cart.apply_coupon
DELETE /api/v1/cart/coupon             → app.api.v1.cart.remove_coupon
POST   /api/v1/cart/validate           → app.api.v1.cart.validate_cart

# Wishlist
GET    /api/v1/wishlist                → app.api.v1.wishlist.get_wishlist
POST   /api/v1/wishlist/items          → app.api.v1.wishlist.add_item
DELETE /api/v1/wishlist/items/{productId}/{variantId?} → app.api.v1.wishlist.remove_item
GET    /api/v1/wishlist/check/{productId}/{variantId?} → app.api.v1.wishlist.check_in_wishlist
POST   /api/v1/wishlist/items/{productId}/move-to-cart → app.api.v1.wishlist.move_to_cart
GET    /api/v1/wishlist/count          → app.api.v1.wishlist.get_count
GET    /api/v1/wishlist/price-drops    → app.api.v1.wishlist.get_price_drops

# Orders
POST   /api/v1/orders                  → app.api.v1.orders.create_order
GET    /api/v1/orders                  → app.api.v1.orders.get_user_orders
GET    /api/v1/orders/{id}             → app.api.v1.orders.get_order
PUT    /api/v1/orders/{id}/cancel      → app.api.v1.orders.cancel_order
POST   /api/v1/orders/{id}/reorder     → app.api.v1.orders.reorder
GET    /api/v1/orders/{id}/tracking    → app.api.v1.orders.get_tracking
GET    /api/v1/orders/admin/all        → app.api.v1.orders.get_all_orders (admin)
PUT    /api/v1/orders/{id}/status      → app.api.v1.orders.update_status (admin)

# Payments
POST   /api/v1/payments/initiate       → app.api.v1.payments.initiate_payment
POST   /api/v1/payments/confirm        → app.api.v1.payments.confirm_payment
GET    /api/v1/payments/history        → app.api.v1.payments.get_history
GET    /api/v1/payments/{id}           → app.api.v1.payments.get_payment
GET    /api/v1/payments/cards          → app.api.v1.payments.get_saved_cards
POST   /api/v1/payments/cards          → app.api.v1.payments.save_card
DELETE /api/v1/payments/cards/{id}     → app.api.v1.payments.delete_card
POST   /api/v1/payments/{id}/refund    → app.api.v1.payments.process_refund (admin)

# Delivery Slots
GET    /api/v1/delivery/slots          → app.api.v1.delivery.get_available_slots
POST   /api/v1/delivery/slots/reserve  → app.api.v1.delivery.reserve_slot

# Notifications
GET    /api/v1/notifications           → app.api.v1.notifications.get_notifications
PUT    /api/v1/notifications/{id}/read → app.api.v1.notifications.mark_read
POST   /api/v1/notifications/register-token → app.api.v1.notifications.register_push_token
```

---

## Database Migration Strategy

### Approach: **Schema Reuse**

Since FastAPI will use the same PostgreSQL database, we'll:
1. **Reuse existing schema** - No schema changes needed
2. **Use Alembic** for future migrations
3. **Generate SQLAlchemy models** from existing schema

### SQLAlchemy Model Generation

```python
# Example: User model mapping to existing 'users' table
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base
import uuid

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    profile_picture_url = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
```

### Redis Key Compatibility

Ensure Redis key patterns remain compatible:
```python
# Cart keys (same pattern as Express)
CART_KEY = "cart:{user_id}"
CART_ITEMS_KEY = "cart:{user_id}:items"

# Wishlist keys
WISHLIST_KEY = "wishlist:{user_id}"

# Session keys
SESSION_KEY = "session:{session_id}"

# Rate limiting keys
RATE_LIMIT_KEY = "ratelimit:{ip}:{endpoint}"
```

---

## Risk Assessment & Mitigation

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Data inconsistency** during migration | Medium | High | Use shared database, comprehensive testing |
| **Performance regression** | Low | High | Load testing, benchmarking vs Express |
| **Authentication issues** | Medium | Critical | Parallel auth testing, gradual rollout |
| **Payment integration failures** | Low | Critical | Stripe sandbox testing, fallback to Express |
| **Downtime during cutover** | Low | High | Blue-green deployment, feature flags |
| **Team Python expertise** | Medium | Medium | Training sessions, code reviews |
| **Third-party library incompatibility** | Low | Medium | Research alternatives, early testing |

### Mitigation Strategies

1. **Parallel Running Period**
   - Run both backends for 2-4 weeks
   - Route 10% → 25% → 50% → 100% traffic to FastAPI
   - Monitor errors and latency

2. **Feature Flags**
   - Use feature flags to enable/disable FastAPI routes
   - Quick rollback without deployment

3. **Comprehensive Testing**
   - Unit tests: 90%+ coverage
   - Integration tests: All API endpoints
   - E2E tests: Critical user journeys
   - Load tests: 2x expected traffic

4. **Database Transaction Isolation**
   - Use database transactions for critical operations
   - Implement idempotency keys for payments

---

## Testing Strategy

### Test Pyramid

```
                    ┌─────────────┐
                    │    E2E      │  10%
                    │   Tests     │
                    └─────────────┘
               ┌─────────────────────┐
               │   Integration       │  30%
               │      Tests          │
               └─────────────────────┘
          ┌─────────────────────────────┐
          │        Unit Tests           │  60%
          │                             │
          └─────────────────────────────┘
```

### Test Coverage Requirements

| Module | Unit Tests | Integration | E2E |
|--------|------------|-------------|-----|
| Auth | 95% | ✓ | ✓ |
| Products | 90% | ✓ | - |
| Categories | 90% | ✓ | - |
| Cart | 95% | ✓ | ✓ |
| Wishlist | 90% | ✓ | - |
| Orders | 95% | ✓ | ✓ |
| Payments | 95% | ✓ | ✓ |
| Admin | 90% | ✓ | - |

### Testing Tools

```python
# pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto
addopts = -v --cov=app --cov-report=html

# conftest.py
@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()
```

---

## Rollback Plan

### Rollback Triggers
- Error rate > 5%
- P95 latency > 500ms (2x baseline)
- Critical payment failures
- Authentication issues affecting > 1% users

### Rollback Procedure

```bash
# 1. Switch traffic back to Express (via NGINX/Load Balancer)
# Update nginx.conf or load balancer rules

# 2. Disable FastAPI feature flags
export FASTAPI_ENABLED=false

# 3. Restart Express backend with full capacity
pm2 restart SRIBEESonline-backend --update-env

# 4. Monitor Express metrics
# Check error rates, latency, database connections

# 5. Post-mortem analysis
# Document what went wrong, fix, and retry
```

---

## Timeline & Resources

### Team Structure

| Role | Count | Responsibilities |
|------|-------|------------------|
| Tech Lead | 1 | Architecture, code review, decisions |
| Senior Backend Dev | 2 | Core module implementation |
| Backend Dev | 2 | Module implementation, testing |
| QA Engineer | 1 | Test strategy, automation |
| DevOps Engineer | 1 | CI/CD, deployment, monitoring |

### Timeline (12 Weeks)

```
Week 1-2:   [████████████████████] Foundation Setup
Week 3-4:   [████████████████████] Auth Module
Week 5-6:   [████████████████████] Products & Categories
Week 7-8:   [████████████████████] Cart & Wishlist
Week 9-10:  [████████████████████] Orders & Payments
Week 11:    [████████████████████] Admin & RBAC
Week 12:    [████████████████████] Final Integration & Launch
```

### Cost Estimate

| Item | Cost/Week | Weeks | Total |
|------|-----------|-------|-------|
| Development Team (7 members) | $15,000 | 12 | $180,000 |
| Infrastructure (parallel running) | $500 | 4 | $2,000 |
| Testing/QA Tools | $200 | 12 | $2,400 |
| Training | - | - | $3,000 |
| **Total** | | | **$187,400** |

---

## Appendix

### A. Environment Variables (FastAPI)

```env
# Application
APP_NAME=SRIBEESonline
APP_ENV=development
DEBUG=true
API_VERSION=v1

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database - PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/SRIBEESonline
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Database - Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Email
MAIL_FROM=noreply@SRIBEESonline.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Expo Push Notifications
EXPO_ACCESS_TOKEN=

# CORS
CORS_ORIGINS=["http://localhost:3001", "http://localhost:19006"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

### B. Key Dependencies (requirements.txt)

```txt
# Core
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Database
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
alembic==1.13.1

# Redis
redis[hiredis]==5.0.1

# Authentication
python-jose[cryptography]==3.3.0
passlib[argon2]==1.7.4
python-multipart==0.0.6

# HTTP Client
httpx==0.26.0

# Email
fastapi-mail==1.4.1

# Payments
stripe==7.10.0

# Rate Limiting
slowapi==0.1.9

# Logging
loguru==0.7.2

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0

# Development
black==23.12.1
isort==5.13.2
mypy==1.8.0
```

### C. Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml (addition for FastAPI)
services:
  fastapi:
    build: ./fastapi_backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/SRIBEESonline
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./fastapi_backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 30, 2026 | Tech Lead | Initial migration plan |

---

**Next Steps:**
1. Review and approve this migration plan
2. Set up FastAPI project structure
3. Begin Phase 1: Foundation Setup
4. Schedule team training on FastAPI/Python

---

*Document maintained by: SRIBEESonline Engineering Team*
