# SRIBEESonline Backend - Complete Implementation Plan

> **Document Status**: As-Built Implementation (February 2026)  
> **Last Updated**: February 2026
>
> This document reflects the actual implemented backend architecture using FastAPI.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Development Phases](#development-phases)
- [Modules Breakdown](#modules-breakdown)
- [Database Design](#database-design)
- [API Documentation](#api-documentation)
- [Security Implementation](#security-implementation)
- [Testing Strategy](#testing-strategy)
- [Deployment Plan](#deployment-plan)

---

## 🎯 Overview

### Project Goal

Build a scalable, production-ready backend for SRIBEESonline e-commerce platform using a **modular monolith architecture** with Python FastAPI and PostgreSQL.

### Key Objectives (As-Built)

- ✅ Implement modular backend with feature-based modules
- ✅ RESTful API design with `/api/v1` versioning
- ✅ JWT-based authentication with Redis session management
- ✅ **Multi-Branch RBAC** (Role-Based Access Control)
- ✅ PostgreSQL + Redis architecture
- ✅ Product variants and multi-image gallery support
- ✅ Redis-backed wishlist with price tracking
- ✅ Comprehensive error handling and logging (Loguru)
- ✅ Rate limiting and security best practices (slowapi, CORS)
- ✅ Automated database migrations (Alembic) and seeding
- ✅ Auto-generated OpenAPI/Swagger documentation

### Timeline

**Total Duration**: 4-6 weeks (160-240 hours)

**Breakdown**:
- Week 1: Setup + Auth Service
- Week 2: Product Service + Cart Service
- Week 3: Order Service + Payment Service
- Week 4: Notification + Search + Review Services
- Week 5-6: Testing, Documentation, Deployment

---

## 🛠️ Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Runtime | Python | 3.11+ | Python runtime |
| Framework | FastAPI | 0.109+ | Async web framework |
| ASGI Server | Uvicorn | 0.27+ | Production server |
| API Style | REST | v1 | API architecture |

### Databases

| Database | Purpose | Port |
|----------|---------|------|
| PostgreSQL | Users, orders, branches, inventory, products, wishlist | 5432 |
| Redis | Sessions, cache, wishlist, rate limiting | 6379 |

### Key Libraries (As-Built)

**Authentication & Security**:
- `python-jose[cryptography]` - JWT token generation with JTI claim
- `passlib[argon2]` - Password hashing
- `slowapi` - Rate limiting
- `FastAPI CORS Middleware` - CORS handling

**Validation & Schemas**:
- `pydantic` (v2) - Schema validation and serialization

**Database**:
- `SQLAlchemy` (2.0+) - Async ORM
- `asyncpg` - Async PostgreSQL driver
- `alembic` - Database migrations
- `redis-py` (async) - Redis client

**Utilities**:
- `pydantic-settings` - Environment configuration
- `httpx` - Async HTTP client
- `aiosmtplib` - Async email sending
- `loguru` - Structured logging

---

## 🏗️ System Architecture (As-Built)

### Modular Monolith Architecture

The backend is implemented as a **modular monolith** with feature-based modules using FastAPI:

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│                     Port: 8000                              │
│    ┌────────────────────────────────────────────────────┐   │
│    │              Middleware Stack                       │   │
│    │     CORS → Rate Limit → JWT Verify → RBAC Check    │   │
│    └────────────────────────────────────────────────────┘   │
│                              │                              │
│    ┌─────────────────────────┼─────────────────────────┐   │
│    │                         │                         │   │
│    ▼                         ▼                         ▼   │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│ │   Auth   │  │ Products │  │   Cart   │  │  Orders  │    │
│ │  Router  │  │  Router  │  │  Router  │  │  Router  │    │
│ └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│ │  Admin   │  │ Wishlist │  │Inventory │  │ Notifi-  │    │
│ │  Router  │  │  Router  │  │  Router  │  │ cations  │    │
│ └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
        │                                       │
        ▼                                       ▼
┌──────────────┐                        ┌──────────────┐
│ PostgreSQL   │                        │    Redis     │
│   (Primary)  │                        │(Sessions/    │
│              │                        │ Cache)       │
└──────────────┘                        └──────────────┘
```

### Project Structure (As-Built)

```
fastapi_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   │
│   ├── api/                       # API routes
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # Main API router
│   │       ├── auth.py            # Customer authentication
│   │       ├── admin_auth.py      # Admin RBAC system
│   │       ├── products.py        # Product catalog
│   │       ├── cart.py            # Shopping cart (Redis-backed)
│   │       ├── orders.py          # Order management
│   │       ├── wishlist.py        # Wishlist with variants
│   │       ├── inventory.py       # Branch inventory
│   │       ├── categories.py      # Category management
│   │       └── notifications.py   # Push/email notifications
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py            # JWT verification, password hashing
│   │   ├── dependencies.py        # FastAPI dependencies (auth, RBAC)
│   │   └── exceptions.py          # Custom exception handlers
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # Pydantic settings
│   │   ├── database.py            # SQLAlchemy async setup
│   │   └── redis.py               # Redis async client
│   │
│   ├── models/                    # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── admin.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── ...
│   │
│   ├── schemas/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── admin_auth.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── ...
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── admin_auth_service.py
│   │   ├── product_service.py
│   │   ├── cart_service.py
│   │   └── ...
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py              # Loguru setup
│
├── alembic/                       # Database migrations
│   ├── versions/
│   └── env.py
│
├── tests/                         # Pytest tests
├── scripts/                       # Seeding scripts
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── pyproject.toml
├── tsconfig.json
└── README.md
```
│   └── workflows/
│       └── ci.yml
│
├── package.json                   # Root package.json
├── tsconfig.json                  # Root TypeScript config
└── README.md
```

---

## 📅 Development Phases

### Phase 1: Foundation Setup (Week 1)

**Duration**: 8-10 hours

**Tasks**:
1. ✅ Create backend directory structure
2. ✅ Set up root package.json with workspaces
3. ✅ Configure TypeScript for all services
4. ✅ Set up shared utilities and types
5. ✅ Configure ESLint and Prettier
6. ✅ Set up Docker Compose for databases
7. ✅ Create database migration scripts
8. ✅ Set up logging infrastructure (Winston)

**Deliverables**:
- Complete project structure
- Docker Compose running PostgreSQL, MongoDB, Redis
- Shared utilities ready for use
- Development environment configured

---

### Phase 2: User Service (Week 1)

**Duration**: 12-16 hours

**Features**:
- User registration with email verification
- Login with JWT tokens (access + refresh)
- Password reset flow
- Profile management
- Address management
- Social login (Google, Facebook)
- Two-factor authentication

**Database Tables** (PostgreSQL):
```sql
users
├── user_id (UUID, PK)
├── email (VARCHAR, UNIQUE)
├── password_hash (VARCHAR)
├── full_name (VARCHAR)
├── phone (VARCHAR)
├── profile_picture_url (TEXT)
├── is_verified (BOOLEAN)
├── two_factor_enabled (BOOLEAN)
├── two_factor_secret (VARCHAR)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

addresses
├── address_id (UUID, PK)
├── user_id (UUID, FK → users)
├── type (VARCHAR) -- 'home', 'work', 'other'
├── address_line1 (VARCHAR)
├── address_line2 (VARCHAR)
├── city (VARCHAR)
├── state (VARCHAR)
├── postal_code (VARCHAR)
├── country (VARCHAR)
├── is_default (BOOLEAN)
└── created_at (TIMESTAMP)

sessions
├── session_id (UUID, PK)
├── user_id (UUID, FK → users)
├── refresh_token_hash (VARCHAR)
├── ip_address (INET)
├── user_agent (TEXT)
├── expires_at (TIMESTAMP)
└── created_at (TIMESTAMP)

email_verifications
├── verification_id (UUID, PK)
├── user_id (UUID, FK → users)
├── token (VARCHAR, UNIQUE)
├── expires_at (TIMESTAMP)
└── created_at (TIMESTAMP)

password_resets
├── reset_id (UUID, PK)
├── user_id (UUID, FK → users)
├── token (VARCHAR, UNIQUE)
├── expires_at (TIMESTAMP)
├── used (BOOLEAN)
└── created_at (TIMESTAMP)

social_accounts
├── social_account_id (UUID, PK)
├── user_id (UUID, FK → users)
├── provider (VARCHAR) -- 'google', 'facebook'
├── provider_user_id (VARCHAR)
├── email (VARCHAR)
├── access_token (TEXT)
├── refresh_token (TEXT)
└── created_at (TIMESTAMP)
```

**API Endpoints**:
```
Authentication:
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh-token
POST   /api/v1/auth/verify-email
POST   /api/v1/auth/resend-verification
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password
GET    /api/v1/auth/google
GET    /api/v1/auth/google/callback
GET    /api/v1/auth/facebook
GET    /api/v1/auth/facebook/callback

User Management:
GET    /api/v1/users/profile
PUT    /api/v1/users/profile
POST   /api/v1/users/profile/picture
PUT    /api/v1/users/change-password
DELETE /api/v1/users/account

Address Management:
GET    /api/v1/users/addresses
POST   /api/v1/users/addresses
PUT    /api/v1/users/addresses/:id
DELETE /api/v1/users/addresses/:id
PUT    /api/v1/users/addresses/:id/set-default

2FA:
POST   /api/v1/users/2fa/enable
POST   /api/v1/users/2fa/verify
POST   /api/v1/users/2fa/disable
GET    /api/v1/users/2fa/backup-codes
```

**Key Files**:
```python
# fastapi_backend/app/api/v1/auth.py
class AuthRouter:
    async def register(request: RegisterSchema) -> UserResponse
    async def login(request: LoginSchema) -> TokenResponse
    async def logout(current_user: User) -> MessageResponse
    async def refresh_token(refresh_token: str) -> TokenResponse
    async def forgot_password(request: ForgotPasswordSchema) -> MessageResponse
    async def reset_password(request: ResetPasswordSchema) -> MessageResponse

# fastapi_backend/app/services/auth_service.py
class AuthService:
    async def register_user(data: RegisterSchema) -> User
    async def login_user(email: str, password: str) -> AuthTokens
    async def verify_email(token: str) -> None
    async def generate_tokens(user_id: str) -> AuthTokens
    async def hash_password(password: str) -> str
    async def verify_password(password: str, hash: str) -> bool

# fastapi_backend/app/core/dependencies.py
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
def require_roles(*roles: str) -> Callable
```

---

### Phase 3: Product Service (Week 2)

**Duration**: 10-12 hours

**Features**:
- Product CRUD operations
- Category management (hierarchical)
- Brand management
- Inventory tracking
- Product attributes (flexible schema)
- Image management

**Database Collections** (MongoDB):
```javascript
// products collection
{
  _id: ObjectId,
  sku: String (unique),
  name: String,
  slug: String (unique),
  description_short: String,
  description_long: String,
  category_id: ObjectId,
  brand: String,
  price: Number,
  discount_price: Number,
  stock_quantity: Number,
  images: [String],
  attributes: {
    weight: String,
    unit: String,
    organic: Boolean,
    // Dynamic attributes
  },
  tags: [String],
  rating_average: Number,
  review_count: Number,
  is_active: Boolean,
  created_at: Date,
  updated_at: Date
}

// categories collection
{
  _id: ObjectId,
  name: String,
  slug: String (unique),
  parent_id: ObjectId (nullable),
  image_url: String,
  description: String,
  display_order: Number,
  is_active: Boolean,
  created_at: Date
}

// brands collection
{
  _id: ObjectId,
  name: String,
  slug: String (unique),
  logo_url: String,
  description: String,
  is_active: Boolean
}
```

**API Endpoints**:
```
Products:
GET    /api/v1/products
GET    /api/v1/products/:id
POST   /api/v1/products              (Admin)
PUT    /api/v1/products/:id          (Admin)
DELETE /api/v1/products/:id          (Admin)
PATCH  /api/v1/products/:id/stock    (Admin)

Categories:
GET    /api/v1/categories
GET    /api/v1/categories/:id
GET    /api/v1/categories/:id/products
POST   /api/v1/categories            (Admin)
PUT    /api/v1/categories/:id        (Admin)
DELETE /api/v1/categories/:id        (Admin)

Brands:
GET    /api/v1/brands
GET    /api/v1/brands/:id
POST   /api/v1/brands                (Admin)
PUT    /api/v1/brands/:id            (Admin)
```

---

### Phase 4: Cart Service (Week 2)

**Duration**: 6-8 hours

**Features**:
- Add items to cart
- Update quantities
- Remove items
- Apply coupon codes
- Calculate totals (subtotal, tax, shipping, discount)
- Cart persistence (Redis)

**Redis Data Structure**:
```
Key: cart:{userId}
Value: {
  items: [
    {
      productId: string,
      quantity: number,
      price: number,
      name: string,
      image: string
    }
  ],
  coupon: {
    code: string,
    discount: number,
    type: 'percentage' | 'fixed'
  },
  totals: {
    subtotal: number,
    discount: number,
    tax: number,
    shipping: number,
    total: number
  },
  updatedAt: timestamp
}
TTL: 30 days
```

**API Endpoints**:
```
GET    /api/v1/cart
POST   /api/v1/cart/items
PUT    /api/v1/cart/items/:productId
DELETE /api/v1/cart/items/:productId
DELETE /api/v1/cart
POST   /api/v1/cart/coupon
DELETE /api/v1/cart/coupon
GET    /api/v1/cart/totals
```

---

### Phase 5: Order Service (Week 3)

**Duration**: 10-12 hours

**Features**:
- Order creation
- Order history
- Order details
- Order tracking
- Order cancellation
- Returns and refunds
- Invoice generation

**Database Tables** (PostgreSQL):
```sql
orders
├── order_id (UUID, PK)
├── user_id (UUID, FK → users)
├── order_number (VARCHAR, UNIQUE)
├── status (VARCHAR) -- 'pending', 'confirmed', 'packed', 'shipped', 'delivered', 'cancelled'
├── payment_status (VARCHAR) -- 'pending', 'paid', 'failed', 'refunded'
├── total_amount (DECIMAL)
├── subtotal (DECIMAL)
├── tax_amount (DECIMAL)
├── shipping_amount (DECIMAL)
├── discount_amount (DECIMAL)
├── delivery_address_id (UUID, FK → addresses)
├── delivery_slot_id (UUID)
├── payment_id (UUID, FK → payments)
├── coupon_code (VARCHAR)
├── notes (TEXT)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

order_items
├── order_item_id (UUID, PK)
├── order_id (UUID, FK → orders)
├── product_id (VARCHAR)
├── product_name (VARCHAR)
├── product_image (TEXT)
├── quantity (INTEGER)
├── unit_price (DECIMAL)
├── subtotal (DECIMAL)
└── created_at (TIMESTAMP)

order_status_history
├── history_id (UUID, PK)
├── order_id (UUID, FK → orders)
├── status (VARCHAR)
├── notes (TEXT)
├── created_by (UUID)
└── created_at (TIMESTAMP)

returns
├── return_id (UUID, PK)
├── order_id (UUID, FK → orders)
├── user_id (UUID, FK → users)
├── items (JSONB)
├── reason (VARCHAR)
├── status (VARCHAR) -- 'requested', 'approved', 'picked_up', 'refunded', 'rejected'
├── refund_amount (DECIMAL)
├── images (TEXT[])
├── pickup_date (DATE)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

**API Endpoints**:
```
GET    /api/v1/orders
GET    /api/v1/orders/:id
POST   /api/v1/orders
PUT    /api/v1/orders/:id/cancel
GET    /api/v1/orders/:id/tracking
GET    /api/v1/orders/:id/invoice
POST   /api/v1/orders/:id/return
POST   /api/v1/orders/:id/reorder
```

---

### Phase 6: Payment Service (Week 3)

**Duration**: 10-12 hours

**Features**:
- Payment intent creation
- Payment confirmation
- Stripe/Razorpay integration
- Refund processing
- Transaction logging
- Webhook handling

**Database Tables** (PostgreSQL):
```sql
payments
├── payment_id (UUID, PK)
├── order_id (UUID, FK → orders)
├── user_id (UUID, FK → users)
├── amount (DECIMAL)
├── currency (VARCHAR)
├── payment_method (VARCHAR) -- 'card', 'upi', 'wallet', 'cod'
├── status (VARCHAR) -- 'pending', 'processing', 'succeeded', 'failed', 'refunded'
├── gateway (VARCHAR) -- 'stripe', 'razorpay'
├── transaction_id (VARCHAR)
├── gateway_response (JSONB)
├── refund_amount (DECIMAL)
├── refund_reason (TEXT)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

saved_cards
├── card_id (UUID, PK)
├── user_id (UUID, FK → users)
├── last_four (VARCHAR)
├── card_type (VARCHAR) -- 'visa', 'mastercard', 'amex'
├── expiry_month (INTEGER)
├── expiry_year (INTEGER)
├── token (VARCHAR) -- Tokenized card
└── created_at (TIMESTAMP)
```

**API Endpoints**:
```
POST   /api/v1/payments/initiate
POST   /api/v1/payments/confirm
POST   /api/v1/payments/verify
POST   /api/v1/payments/refund        (Admin)
GET    /api/v1/payments/:id
POST   /api/v1/payments/webhook       (Stripe/Razorpay webhook)
GET    /api/v1/payments/cards
POST   /api/v1/payments/cards
DELETE /api/v1/payments/cards/:id
```

---

### Phase 7: Supporting Services (Week 4)

#### Notification Service (Port 3006)

**Duration**: 8-10 hours

**Features**:
- Email notifications (SendGrid)
- SMS notifications (Twilio)
- Push notifications (Firebase)
- Notification queue (RabbitMQ/Bull)
- Template management

**API Endpoints**:
```
POST   /api/v1/notifications/email
POST   /api/v1/notifications/sms
POST   /api/v1/notifications/push
GET    /api/v1/notifications
PUT    /api/v1/notifications/:id/read
```

#### Search Service (Port 3007)

**Duration**: 6-8 hours

**Features**:
- Product search (Elasticsearch)
- Autocomplete
- Filters and facets
- Search analytics

**API Endpoints**:
```
GET    /api/v1/search?q=query
GET    /api/v1/search/suggestions?q=query
GET    /api/v1/search/history
```

#### Review Service (Port 3008)

**Duration**: 6-8 hours

**Features**:
- Product reviews
- Rating calculation
- Review moderation
- Helpful votes

**Database Tables** (PostgreSQL):
```sql
reviews
├── review_id (UUID, PK)
├── product_id (VARCHAR)
├── user_id (UUID, FK → users)
├── order_id (UUID, FK → orders)
├── rating (INTEGER) -- 1-5
├── title (VARCHAR)
├── comment (TEXT)
├── images (TEXT[])
├── helpful_count (INTEGER)
├── status (VARCHAR) -- 'pending', 'approved', 'rejected'
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

**API Endpoints**:
```
GET    /api/v1/products/:id/reviews
POST   /api/v1/products/:id/reviews
PUT    /api/v1/reviews/:id
DELETE /api/v1/reviews/:id
POST   /api/v1/reviews/:id/helpful
```

---

## 🔐 Security Implementation (As-Built)

### Authentication Flow

```
1. User Login
   ↓
2. Verify Credentials (Argon2)
   ↓
3. Generate JWT Tokens with JTI claim
   - Access Token (15 min)
   - Refresh Token (7 days, 30 days with Remember Me)
   ↓
4. Store Session in Redis
   Key: sessions:{userId}:{sessionId}
   ↓
5. Return Tokens to Client
   ↓
6. Client Stores in httpOnly Cookies / SecureStore (mobile)
```

### Redis Session Management

```typescript
// Session key patterns
sessions:{userId}:{sessionId}     // Individual session data
user:sessions:{userId}            // SET of active session IDs
blacklist:token:{jti}             // Revoked token (24hr TTL)
blacklist:user:{userId}           // Global invalidation timestamp
```

### Multi-Branch RBAC Middleware Chain

```typescript
// Example protected admin route
router.get('/inventory',
    authenticateAdmin,                    // 1. Verify JWT
    requireRole([AdminRole.SUPER_ADMIN, AdminRole.BRANCH_MANAGER]),
    injectBranchFilter,                   // 2. Auto-inject branch filter
    InventoryController.getInventory
);
```

### Branch Isolation SQL Helper

```typescript
// Automatic branch filter injection
export const getBranchFilterSQL = (req: Request, alias?: string): string => {
    if (req.branchContext?.hasFullAccess) return '';
    const prefix = alias ? `${alias}.` : '';
    return `AND ${prefix}branch_id = '${req.branchContext.branchId}'`;
};
```

### Security Checklist (As-Built)

- ✅ Password hashing with Argon2 (passlib)
- ✅ JWT tokens with JTI claim for revocation (python-jose)
- ✅ Redis-backed session management
- ✅ Token blacklisting (individual and user-wide)
- ✅ CORS configuration (FastAPI CORSMiddleware)
- ✅ Security headers middleware
- ✅ Rate limiting (1000/15min API, 5/15min auth, 3/1hr password reset)
- ✅ Input validation with Pydantic v2
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Branch isolation middleware
- ✅ Admin audit logging

---

## 🧪 Testing Strategy

### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Target: >80% code coverage

### Integration Tests
- Test API endpoints
- Test database operations
- Test service interactions

### E2E Tests
- Test complete user flows
- Test order processing
- Test payment processing

### Load Testing
- Apache JMeter or k6
- Test concurrent users
- Identify bottlenecks

---

## 🚀 Deployment Plan

### Docker Containers

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: SRIBEESonline
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  user-service:
    build: ./services/user-service
    ports:
      - "3001:3001"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/SRIBEESonline
      - REDIS_URL=redis://redis:6379

  product-service:
    build: ./services/product-service
    ports:
      - "3002:3002"
    depends_on:
      - mongodb

volumes:
  postgres_data:
  mongo_data:
  redis_data:
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest
      - run: pip install build && python -m build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Deployment commands
```

---

## 📊 Monitoring & Logging

### Logging Strategy

```typescript
// Winston logger configuration
import winston from 'winston';

export const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' }),
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});
```

### Metrics to Track

- Request rate and latency
- Error rates (4xx, 5xx)
- Database query performance
- Cache hit/miss ratio
- Payment success rate
- Order conversion rate

---

## 📝 API Endpoints (As-Built)

### Customer Authentication

```
POST   /api/v1/auth/register              # User registration
POST   /api/v1/auth/login                 # Login with email/password
POST   /api/v1/auth/logout                # Logout current session
POST   /api/v1/auth/logout-all            # Logout all sessions
POST   /api/v1/auth/refresh-token         # Refresh access token
GET    /api/v1/auth/sessions              # List active sessions
DELETE /api/v1/auth/sessions/:sessionId   # Revoke specific session
POST   /api/v1/auth/forgot-password       # Request password reset
POST   /api/v1/auth/reset-password        # Reset with token
```

### Admin Authentication & RBAC

```
POST   /api/v1/admin/auth/login           # Admin login
GET    /api/v1/admin/auth/profile         # Admin profile
POST   /api/v1/admin/auth/logout          # Admin logout
GET    /api/v1/admin/users                # List admin users (super_admin)
POST   /api/v1/admin/users                # Create admin user (super_admin)
PUT    /api/v1/admin/users/:id            # Update admin user
DELETE /api/v1/admin/users/:id            # Deactivate admin user
```

### Branch Management (Super Admin)

```
GET    /api/v1/admin/branches             # List all branches
POST   /api/v1/admin/branches             # Create branch
GET    /api/v1/admin/branches/:id         # Get branch details
PUT    /api/v1/admin/branches/:id         # Update branch
DELETE /api/v1/admin/branches/:id         # Deactivate branch
```

### Branch Inventory

```
GET    /api/v1/admin/inventory            # List inventory (branch-filtered)
PUT    /api/v1/admin/inventory/:id        # Update stock level
GET    /api/v1/admin/inventory/low-stock  # Low stock alerts
POST   /api/v1/admin/transfers            # Create stock transfer
GET    /api/v1/admin/transfers            # List transfers
PUT    /api/v1/admin/transfers/:id/approve  # Approve transfer
```

### Products

```
GET    /api/v1/products                   # List products (paginated)
GET    /api/v1/products/:id               # Get product with variants
POST   /api/v1/admin/products             # Create product (admin)
PUT    /api/v1/admin/products/:id         # Update product (admin)
DELETE /api/v1/admin/products/:id         # Delete product (admin)
POST   /api/v1/admin/products/:id/images  # Upload images
DELETE /api/v1/admin/products/:id/images/:imageId  # Delete image
```

### Cart

```
GET    /api/v1/cart                       # Get cart contents
POST   /api/v1/cart/items                 # Add item to cart
PUT    /api/v1/cart/items/:productId      # Update quantity
DELETE /api/v1/cart/items/:productId      # Remove item
DELETE /api/v1/cart                       # Clear cart
POST   /api/v1/cart/coupon                # Apply coupon
DELETE /api/v1/cart/coupon                # Remove coupon
POST   /api/v1/cart/merge                 # Merge guest cart on login
POST   /api/v1/cart/validate              # Validate cart before checkout
```

### Wishlist

```
GET    /api/v1/wishlist                   # Get wishlist items
POST   /api/v1/wishlist/items             # Add item (with variant)
DELETE /api/v1/wishlist/items/:productId  # Remove item
GET    /api/v1/wishlist/check/:productId  # Check if in wishlist (O(1))
GET    /api/v1/wishlist/price-drops       # Get items with price drops
POST   /api/v1/wishlist/sync              # Sync Redis cache with DB
POST   /api/v1/wishlist/:productId/move-to-cart  # Move to cart
```

### Orders

```
GET    /api/v1/orders                     # List orders (user or admin)
GET    /api/v1/orders/:id                 # Get order details
POST   /api/v1/orders                     # Create order
PUT    /api/v1/admin/orders/:id/status    # Update status (admin)
POST   /api/v1/orders/:id/cancel          # Cancel order
GET    /api/v1/orders/:id/invoice         # Download invoice PDF
```

---

*Document Version: 2.0 (As-Built)*  
*Last Updated: January 29, 2026*  
*Document reflects actual implementation state*
