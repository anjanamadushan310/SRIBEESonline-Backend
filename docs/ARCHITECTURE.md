# SRIBEESonline - Technical Architecture

> **Document Status**: As-Built Implementation (February 2026)  
> **Last Updated**: February 2026

## 🏗️ System Architecture Overview

SRIBEESonline is a modern **multi-branch e-commerce platform** with a hybrid architecture, featuring a React Web Admin Portal, Flutter Mobile App, and Python FastAPI backend. The system implements **Multi-Branch RBAC (Role-Based Access Control)** with branch isolation for inventory and operations management. Customer sessions are scoped to a specific branch via **Smart Address-to-Branch Routing** — on app launch, the user selects a saved delivery address, the backend maps the address's Post Office to a serving branch, and all subsequent content (including the "Quick Sale" Home Page feed) is filtered by that branch.

---

## 📐 Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        Mobile[Mobile App<br/>Flutter + Dart]
        Admin[Admin Dashboard<br/>React 19 + Vite 7]
    end

    subgraph "API Gateway Layer"
        Gateway[FastAPI Server<br/>REST API v1]
        AuthMW[Authentication Middleware<br/>JWT + Redis Sessions]
        RBAC[RBAC Middleware<br/>Branch Isolation]
    end

    subgraph "Service Layer"
        AuthService[Auth Service<br/>Customer + Admin]
        ProductService[Product Service<br/>Catalog + Variants]
        SearchService[Semantic Search<br/>Gemini + pgvector]
        CartService[Cart Service<br/>Redis-First]
        OrderService[Order Service]
        WishlistService[Wishlist Service<br/>Redis + PostgreSQL]
        InventoryService[Branch Inventory<br/>Multi-Branch Stock]
        NotificationService[Notification Service<br/>Push + Email]
    end

    subgraph "Data Layer"
        PostgreSQL[(🐘 PostgreSQL 15<br/>+ pgvector)]
        Redis[(Redis<br/>Sessions + Cache)]
    end

    subgraph "External Services"
        GeminiAI[Google Gemini<br/>Embeddings API]
        PushNotif[Firebase Cloud<br/>Messaging]
        EmailService[Email Service<br/>FastAPI-Mail]
        StorageService[MinIO / S3<br/>Assets + Video]
    end

    Mobile --> Gateway
    Admin --> Gateway
    
    Gateway --> AuthMW
    AuthMW --> RBAC
    
    RBAC --> AuthService
    RBAC --> ProductService
    RBAC --> SearchService
    RBAC --> CartService
    RBAC --> OrderService
    RBAC --> WishlistService
    RBAC --> InventoryService
    RBAC --> NotificationService

    AuthService --> PostgreSQL
    AuthService --> Redis
    ProductService --> PostgreSQL
    CartService --> Redis
    OrderService --> PostgreSQL
    WishlistService --> Redis
    WishlistService --> PostgreSQL
    InventoryService --> PostgreSQL
    NotificationService --> PostgreSQL

    NotificationService --> PushNotif
    NotificationService --> EmailService
    ProductService --> StorageService
```

---

## 🔧 Technology Stack

### Frontend: React Web Admin Dashboard

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 19+ |
| Build Tool | Vite | 7.3+ |
| UI Library | Ant Design | 6+ |
| State Management | TanStack Query | 5+ |
| Charts | Recharts | 3+ |
| Routing | React Router | 7+ |
| HTTP Client | Axios | 1.7+ |
| Type Safety | TypeScript | 5.6+ |
| Styling | CSS Modules + Ant Design |  |

### Mobile App: Flutter

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Flutter | 3.x+ |
| Language | Dart | 3.x+ |
| Navigation | GoRouter | 12+ |
| State Management | Riverpod / Provider | 2+ |
| HTTP Client | Dio | 5+ |
| Storage | flutter_secure_storage |  |
| Push Notifications | Firebase Cloud Messaging |  |

### Backend: FastAPI (Python)

| Component | Technology | Version |
|-----------|-----------|---------|
| Runtime | Python | 3.11+ |
| Framework | FastAPI | 0.109+ |
| ASGI Server | Uvicorn + Gunicorn | 0.27+ |
| Authentication | python-jose + passlib[argon2] |  |
| Validation | Pydantic | v2+ |
| PostgreSQL Client | SQLAlchemy 2.0+ / asyncpg |  |
| Redis Client | redis-py (async) |  |
| Security | FastAPI Security + slowapi |  |
| Logging | Loguru |  |

### Databases

| Database | Version | Purpose |
|----------|---------|---------|
| PostgreSQL | 15+ | Users, Orders, Branches, Inventory, Products, Wishlist |
| Redis | 7+ | Sessions, Cache, Wishlist, Rate Limiting |

---

## 🔐 Multi-Branch RBAC Architecture

### Role Definitions

The system implements six distinct admin roles with hierarchical permissions:

```python
from enum import Enum

class AdminRole(str, Enum):
    SUPER_ADMIN = 'super_admin'               # Full system access
    BRANCH_MANAGER = 'branch_manager'         # Branch-specific management
    MARKETING_MANAGER = 'marketing_manager'   # Branch-specific marketing & discounts
    STAFF = 'staff'                           # Basic operations
    SUPPORT = 'support'                       # Customer support (cross-branch)
    INVENTORY = 'inventory'                   # Inventory management (cross-branch)
```

### Permission Matrix

| Role | Branch Restricted | Products | Orders | Inventory | Analytics | Users | Settings | Discounts |
|------|:-----------------:|:--------:|:------:|:---------:|:---------:|:-----:|:--------:|:---------:|
| `super_admin` | ❌ | CRUD | CRUD | CRUD | ✅ Full | CRUD | ✅ Full | CRUD |
| `branch_manager` | ✅ | R/U | R/U/D | R/U | ✅ Branch | View | Branch | R/U |
| `marketing_manager` | ✅ | R | R | R | ✅ Branch | ❌ | ❌ | C/R/U |
| `staff` | ✅ | R | R/U | R | ❌ | ❌ | ❌ | ❌ |
| `support` | ❌ | R | R/U | R | ❌ | ❌ | ❌ | ❌ |
| `inventory` | ❌ | C/R/U | ❌ | C/R/U | ✅ | ❌ | ❌ | ❌ |

### Branch Isolation Middleware

```python
# FastAPI dependency for branch-restricted operations
from fastapi import Depends, Request
from app.core.dependencies import get_current_admin, require_role
from app.models.admin import AdminRole

@router.get('/inventory')
async def get_inventory(
    request: Request,
    admin = Depends(get_current_admin),
    _role = Depends(require_role([AdminRole.SUPER_ADMIN, AdminRole.BRANCH_MANAGER, AdminRole.INVENTORY]))
):
    branch_context = inject_branch_filter(admin)
    return await InventoryService.get_inventory(branch_context)

# Automatic branch filter injection
def inject_branch_filter(admin) -> dict:
    has_full_access = has_cross_branch_access(admin.role)
    
    return {
        'branch_id': admin.branch_id or '',
        'is_filtered': not has_full_access and bool(admin.branch_id),
        'has_full_access': has_full_access,
    }
```

### Database Query Branch Isolation

```python
# SQL queries automatically include branch filter using SQLAlchemy
def get_branch_filter(branch_context: dict, model):
    if not branch_context or branch_context.get('has_full_access'):
        return True  # No filter for cross-branch roles
    return model.branch_id == branch_context['branch_id']

# Example usage in inventory queries
async def get_low_stock_items(db: AsyncSession, branch_context: dict):
    query = select(BranchInventory).where(
        BranchInventory.stock_quantity <= BranchInventory.low_stock_threshold,
        get_branch_filter(branch_context, BranchInventory)
    )
    result = await db.execute(query)
    return result.scalars().all()
```

---

## 🗺️ Smart Address-to-Branch Routing

### Overview

Before accessing the Home Page, the mobile app enforces a **Branch Selection** flow. This ensures every customer session is scoped to a single branch, providing branch-isolated product listings, pricing, and marketing (Quick Sale) content.

### Routing Flow

```mermaid
sequenceDiagram
    participant User
    participant MobileApp
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant Redis

    User->>MobileApp: Opens App
    MobileApp->>API: Check active session/branch context
    API->>Redis: GET session:{userId}:branch_context
    alt Branch context exists
        Redis-->>API: {branch_id, branch_name}
        API-->>MobileApp: Branch active → Home Page
    else No branch context
        API-->>MobileApp: No branch → Address Selection
        MobileApp->>User: Show "Select Delivery Address" screen
        User->>MobileApp: Selects saved address
        MobileApp->>API: POST /api/v1/branch/resolve {address_id}
        API->>DB: Fetch address → extract post_office
        DB-->>API: Address with post_office
        API->>DB: Lookup post_office_branch_mapping
        DB-->>API: branch_id for post_office
        API->>Redis: SET session:{userId}:branch_context {branch_id}
        API-->>MobileApp: {branch_id, branch_name}
        MobileApp->>User: Redirect to Home Page (filtered by branch)
    end
```

### Backend Resolution Logic

```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.models.address import Address
from app.models.branch_mapping import PostOfficeBranchMapping

router = APIRouter(prefix="/api/v1/branch", tags=["branch-routing"])

@router.post("/resolve")
async def resolve_branch(
    address_id: str,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    # 1. Fetch the selected address
    address = await db.get(Address, address_id)
    if not address or address.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Address not found")

    # 2. Extract post_office and resolve to branch
    mapping = await db.execute(
        select(PostOfficeBranchMapping)
        .where(PostOfficeBranchMapping.post_office == address.post_office)
    )
    branch_mapping = mapping.scalar_one_or_none()
    if not branch_mapping:
        raise HTTPException(status_code=400, detail="No branch serves this area")

    # 3. Store branch context in session (Redis)
    session_key = f"session:{user.user_id}:branch_context"
    await redis.set(session_key, json.dumps({
        "branch_id": str(branch_mapping.branch_id),
        "branch_name": branch_mapping.branch_name,
        "post_office": address.post_office,
        "resolved_at": datetime.utcnow().isoformat(),
    }), ex=30 * 24 * 60 * 60)  # 30 days TTL

    return {"branch_id": branch_mapping.branch_id, "branch_name": branch_mapping.branch_name}
```

### API Endpoints

```
POST /api/v1/branch/resolve          # Resolve address → branch, set session context
GET  /api/v1/branch/current          # Get current branch context from session
DELETE /api/v1/branch/current        # Clear branch context (forces re-selection)
```

### Home Page: Quick Sale Feed

Once a branch is resolved, the Home Page displays **only** high-discount "Quick Sale" items for that branch. General product browsing is handled through Category-specific screens.

```python
@router.get("/api/v1/home/quick-sale")
async def get_quick_sale_items(
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    branch_context = await get_branch_context(user.user_id, redis)
    if not branch_context:
        raise HTTPException(status_code=428, detail="Branch selection required")

    # Fetch products with highest discounts for this branch
    query = (
        select(Product, BranchInventory)
        .join(BranchInventory, Product.product_id == BranchInventory.product_id)
        .where(
            BranchInventory.branch_id == branch_context["branch_id"],
            BranchInventory.stock_quantity > 0,
            Product.is_active == True,
            Product.compare_at_price.isnot(None),
            Product.compare_at_price > Product.price,
        )
        .order_by((Product.compare_at_price - Product.price).desc())
        .limit(20)
    )
    results = await db.execute(query)
    return results.all()
```

### MARKETING_MANAGER Role

The `MARKETING_MANAGER` is a branch-restricted admin role responsible for setting product discounts within their assigned branch. The system automatically selects the highest-discount products to populate the Home Page "Quick Sale" feed.

**Capabilities:**
- View products available in their branch
- Set / update `compare_at_price` (original price) and `price` (sale price) for branch products
- View branch-level analytics on discount performance
- Cannot manage inventory, users, or system settings

**Discount → Quick Sale Pipeline:**
1. Marketing Manager sets a discount on a product (e.g., `compare_at_price = 1500`, `price = 999`)
2. The system calculates the discount percentage: `(1500 - 999) / 1500 = 33.4%`
3. The Home Page Quick Sale query automatically picks the highest-discount items for that branch
4. No manual "featuring" is needed — discounts drive visibility

---

## 🔴 Redis Integration

### Redis Architecture

Redis serves as the **primary cache layer** and **session store** with a circuit breaker pattern for resilience.

### Key Patterns

| Category | Key Pattern | TTL | Purpose |
|----------|-------------|-----|---------|
| **Sessions** | `sessions:{userId}:{sessionId}` | 7-30 days | Session data with device info |
| **User Sessions** | `user:sessions:{userId}` | - | SET of active session IDs |
| **Token Blacklist** | `blacklist:token:{jti}` | 24 hours | Individual revoked tokens |
| **User Blacklist** | `blacklist:user:{userId}` | - | Global token invalidation timestamp |
| **User Profile** | `user:profile:{userId}` | 15 min | Cached profile data |
| **Rate Limit** | `rate:login:{identifier}` | 15 min | Login attempt counter |
| **Wishlist** | `watchlist:{userId}` | 7 days | SET of `{productId}:{variantId}` |
| **Product Cache** | `product:{productId}` | 1 hour | Cached product data |
| **Inventory** | `inventory:branch:{branchId}:product:{productId}` | 5 min | Branch stock cache |
| **Search Embedding** | `search:embedding:{hash}` | 24 hours | Cached Gemini query embeddings |
| **Search Results** | `search:results:{hash}` | 1 hour | Cached semantic search results |
| **Popular Searches** | `search:popular` | - | Sorted set of trending queries |
| **Search Suggestions** | `search:suggestions:{prefix}` | 15 min | Autocomplete cache |
| **Branch Context** | `session:{userId}:branch_context` | 30 days | Active branch for customer session |

### Session Management

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class SessionData:
    user_id: str
    email: str
    session_id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: int = 0
    last_activity_at: int = 0
    expires_at: int = 0
    is_remember_me: bool = False

# Redis TTL constants
REDIS_TTL = {
    "SESSION_DEFAULT": 7 * 24 * 60 * 60,      # 7 days
    "SESSION_REMEMBER_ME": 30 * 24 * 60 * 60, # 30 days
    "BLACKLIST_TOKEN": 24 * 60 * 60,          # 24 hours
    "USER_PROFILE_CACHE": 15 * 60,            # 15 minutes
}
```

### Circuit Breaker Pattern

```python
# Redis service with automatic PostgreSQL fallback
class CircuitBreaker:
    def __init__(self):
        self.failures = 0
        self.last_failure = 0
        self.is_open = False
    
    def should_attempt_redis(self) -> bool:
        import time
        if not self.is_open:
            return True
        # Half-open after 30 seconds
        if time.time() * 1000 - self.last_failure > 30000:
            return True
        return False
```

---

## 📦 Product & Variant Architecture

### Product Image Gallery (1 Thumbnail + 4 Gallery)

```sql
CREATE TABLE product_images (
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(product_id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    alt_text VARCHAR(255),
    is_primary BOOLEAN DEFAULT FALSE,  -- TRUE = thumbnail
    sort_order INTEGER DEFAULT 0,       -- Order for gallery images
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Validation Rules:**
- Exactly 1 thumbnail image (`is_primary = true`)
- Maximum 4 gallery images (`is_primary = false`)
- Total maximum 5 images per product

### Product Variants Schema

```sql
-- Variant Types (Size, Color, Weight, Pack Size)
CREATE TABLE variant_types (
    variant_type_id UUID PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,    -- 'size', 'color', 'weight', 'pack_size'
    display_name VARCHAR(100) NOT NULL,  -- 'Select Size', 'Choose Color'
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- Variant Options (values for each type)
CREATE TABLE variant_options (
    variant_option_id UUID PRIMARY KEY,
    variant_type_id UUID REFERENCES variant_types,
    value VARCHAR(100) NOT NULL,         -- 'Small', 'Red', '500g'
    display_value VARCHAR(100),          -- 'S', 'Red', '500 grams'
    color_hex VARCHAR(7),                -- '#FF0000' for color variants
    display_order INTEGER DEFAULT 0,
    UNIQUE(variant_type_id, value)
);

-- Product Variants (SKUs with price/stock)
CREATE TABLE product_variants (
    variant_id UUID PRIMARY KEY,
    product_id UUID REFERENCES products ON DELETE CASCADE,
    sku VARCHAR(100) UNIQUE,
    name VARCHAR(255),
    price DECIMAL(10, 2) NOT NULL,
    compare_at_price DECIMAL(10, 2),
    stock_quantity INTEGER DEFAULT 0,
    weight DECIMAL(10, 3),
    image_url TEXT,                      -- Variant-specific image
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Variant-Option Mapping
CREATE TABLE product_variant_options (
    variant_id UUID REFERENCES product_variants ON DELETE CASCADE,
    variant_type_id UUID REFERENCES variant_types,
    variant_option_id UUID REFERENCES variant_options,
    UNIQUE(variant_id, variant_type_id)  -- One option per type per variant
);
```

### Seeded Variant Types

| Type | Options |
|------|---------|
| `size` | XS, S, M, L, XL, XXL |
| `weight` | 100g, 250g, 500g, 1kg, 2kg, 5kg |
| `pack_size` | Single, Pack of 3, Pack of 6, Pack of 12 |
| `color` | Red, Blue, Green, Black, White, Yellow (with hex codes) |

---

## 💚 Wishlist/Watchlist Architecture

### Database Schema

```sql
CREATE TABLE wishlist_items (
    wishlist_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    product_id VARCHAR(255) NOT NULL,
    variant_id UUID REFERENCES product_variants(variant_id),
    price_at_watch DECIMAL(10, 2),       -- Price tracking for alerts
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id, variant_id)
);
```

### Redis Caching (O(1) Lookups)

```python
# Key: "watchlist:{userId}"
# Value: SET of "{productId}:{variantId|null}"

class RedisWishlistService:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def is_in_wishlist(self, user_id: str, product_id: str, variant_id: str | None) -> bool:
        key = f"watchlist:{user_id}"
        member = f"{product_id}:{variant_id or 'null'}"
        return await self.redis.sismember(key, member) == 1  # O(1)
    
    async def add_to_cache(self, user_id: str, product_id: str, variant_id: str | None) -> None:
        key = f"watchlist:{user_id}"
        member = f"{product_id}:{variant_id or 'null'}"
        await self.redis.sadd(key, member)
        await self.redis.expire(key, 7 * 24 * 60 * 60)  # 7 days
```

### Price Drop Detection

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class WishlistItemWithDetails:
    wishlist_item_id: str
    product_id: str
    variant_id: Optional[str]
    price_at_watch: float       # Price when added
    current_price: float        # Live price
    price_drop: float           # Difference
    price_drop_percentage: float
```

---

## 🖥️ React Web Admin Dashboard Architecture

### Project Structure

```
admin/
├── src/
│   ├── api/                        # API Layer
│   │   ├── client.ts               # HTTP client with interceptors
│   │   ├── auth.api.ts             # Admin authentication
│   │   ├── products.api.ts         # Products CRUD
│   │   ├── orders.api.ts           # Order management
│   │   ├── branches.api.ts         # Branch management
│   │   └── inventory.api.ts        # Branch inventory
│   │
│   ├── components/
│   │   ├── common/                 # Shared UI components
│   │   ├── layout/
│   │   │   ├── AdminLayout.tsx     # Main layout with sidebar
│   │   │   ├── Sidebar.tsx         # Role-based navigation
│   │   │   └── Header.tsx          # Top bar with user info
│   │   ├── products/
│   │   │   ├── ImageGalleryUpload.tsx   # 1 Thumbnail + 4 Gallery
│   │   │   └── VariantManager.tsx       # Dynamic variant management
│   │   ├── inventory/
│   │   │   ├── LowStockAlert.tsx
│   │   │   └── StockTransferForm.tsx
│   │   └── guards/                 # Route protection
│   │       ├── RoleGuard.tsx       # Role-based access
│   │       └── PermissionGuard.tsx # Permission-based access
│   │
│   ├── pages/
│   │   ├── Auth/Login.tsx
│   │   ├── Dashboard/
│   │   │   ├── AdminDashboard.tsx      # Super Admin view
│   │   │   ├── ManagerDashboard.tsx    # Branch Manager view
│   │   │   └── StaffDashboard.tsx      # Staff view
│   │   ├── Products/ProductList.tsx, ProductForm.tsx
│   │   ├── Orders/OrderList.tsx, OrderDetail.tsx
│   │   ├── Inventory/
│   │   │   ├── BranchInventory.tsx
│   │   │   ├── StockTransfers.tsx
│   │   │   └── LowStockReport.tsx
│   │   ├── Analytics/
│   │   │   ├── WatchlistAnalytics.tsx
│   │   │   └── BranchAnalytics.tsx
│   │   ├── Users/AdminUserList.tsx, AdminUserForm.tsx
│   │   └── Branches/BranchList.tsx
│   │
│   ├── store/                      # State management
│   │   ├── authStore.ts            # User + token + permissions
│   │   ├── uiStore.ts              # Sidebar + theme
│   │   ├── branchStore.ts          # Active branch context
│   │   └── notificationStore.ts    # Alerts
│   │
│   ├── types/                      # TypeScript types
│   │   ├── admin.types.ts          # AdminRole, permissions
│   │   ├── product.types.ts        # Product, Variant types
│   │   ├── branch.types.ts         # Branch, Transfer types
│   │   └── api.types.ts            # API response types
│   │
│   ├── hooks/
│   │   └── usePermissions.ts       # RBAC permission checks
│   │
│   └── router.tsx                  # React Router with guards
```

### Navigation by Role

| Menu Item | Super Admin | Branch Manager | Marketing Manager | Staff |
|-----------|:-----------:|:--------------:|:-----------------:|:-----:|
| Dashboard | ✅ Global | ✅ Branch | ✅ Branch | ✅ Tasks |
| Products | ✅ Full CRUD | ✅ View + Stock | ✅ View + Discounts | ✅ View |
| Orders | ✅ All Branches | ✅ Own Branch | ✅ View Branch | ✅ Process |
| Inventory | ✅ All Branches | ✅ Own Branch | ✅ View | ✅ View |
| Stock Transfers | ✅ All | ✅ Create/View | ❌ | ❌ |
| Quick Sale / Discounts | ✅ Global | ✅ Branch | ✅ Manage Branch | ❌ |
| Analytics | ✅ Global | ✅ Branch | ✅ Discount Analytics | ❌ |
| Watchlist Analytics | ✅ Full | ✅ Branch Trends | ❌ | ❌ |
| Admin Users | ✅ Manage | ❌ | ❌ | ❌ |
| Branches | ✅ Manage | ❌ | ❌ | ❌ |
| Settings | ✅ System | ✅ Branch | ❌ | ❌ |

### HTTP Client Interceptors for Branch Isolation

```typescript
// Request interceptor - inject branch header
apiClient.interceptors.request.use((config) => {
    const { user, activeBranch } = useAuthStore.getState();
    
    // Add auth token
    const token = localStorage.getItem('admin_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Inject branch filter for restricted roles
    if (user?.role !== 'super_admin' && user?.branch_id) {
        config.headers['X-Branch-ID'] = user.branch_id;
    } else if (activeBranch) {
        config.headers['X-Branch-ID'] = activeBranch;
    }
    
    return config;
});

// Response interceptor - handle 401
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            useAuthStore.getState().logout();
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);
```

---

## 📱 Flutter Mobile App Architecture

### Project Structure

```
mobile/
├── lib/
│   ├── api/                        # API Layer
│   │   ├── dio_client.dart         # Dio with auth interceptors
│   │   ├── auth_api.dart           # Customer authentication
│   │   ├── products_api.dart       # Product catalog
│   │   ├── cart_api.dart           # Cart operations
│   │   ├── orders_api.dart         # Order management
│   │   └── wishlist_api.dart       # Wishlist with variant support
│   │
│   ├── widgets/
│   │   ├── common/                 # Shared widgets
│   │   ├── products/
│   │   │   ├── product_card.dart
│   │   │   └── variant_selector.dart
│   │   ├── cart/cart_item.dart, cart_summary.dart
│   │   └── wishlist/
│   │       ├── wishlist_button.dart  # Heart icon toggle
│   │       └── watchlist_item_card.dart
│   │
│   ├── screens/
│   │   ├── auth/login_screen.dart, register_screen.dart
│   │   ├── home/home_screen.dart
│   │   ├── products/product_list_screen.dart, product_detail_screen.dart
│   │   ├── cart/cart_screen.dart, checkout_screen.dart
│   │   ├── orders/order_history_screen.dart, order_detail_screen.dart
│   │   ├── wishlist/wishlist_screen.dart
│   │   └── profile/profile_screen.dart
│   │
│   ├── providers/                  # Riverpod providers
│   │   ├── auth_provider.dart      # User + tokens
│   │   ├── cart_provider.dart      # Cart state
│   │   └── wishlist_provider.dart  # Wishlist with offline support
│   │
│   └── utils/
│       ├── secure_storage.dart     # flutter_secure_storage wrapper
│       └── analytics.dart          # Event tracking
├── android/
├── ios/
└── pubspec.yaml
```

### Wishlist Provider (Riverpod)

```dart
class WishlistState {
  final List<WishlistItemWithDetails> items;
  final bool isLoading;
  
  const WishlistState({
    this.items = const [],
    this.isLoading = false,
  });
}

class WishlistNotifier extends StateNotifier<WishlistState> {
  WishlistNotifier() : super(const WishlistState());
  
  Future<void> addToWishlist(WishlistItem product) async { ... }
  Future<void> removeFromWishlist(String productId, String? variantId) async { ... }
  bool isInWishlist(String productId, String? variantId) { ... }
  Future<void> toggleWishlist(WishlistItem product) async { ... }
  Future<void> loadWishlist() async { ... }
  Future<void> getPriceDrops({double? minDrop}) async { ... }
  Future<void> moveToCart(WishlistItemWithDetails item) async { ... }
}
```

### Dynamic Video Splash Screen

The mobile app supports a customizable video splash screen with the following architecture:

```dart
// VideoSplashScreen Configuration
class SplashConfig {
  static const int maxVideoDuration = 4000;  // 4 seconds max playback
  static const int fadeOutDuration = 500;    // 500ms smooth fade transition
  static const String apiEndpoint = '/api/v1/mobile/splash-video';
  static const String cacheKey = 'splash_video_cache';
}

// Video Requirements
class SplashVideoConfig {
  static const double maxDuration = 4.0;           // seconds (server-validated)
  static const int maxFileSize = 5 * 1024 * 1024;  // 5MB
  static const String allowedMimeType = 'video/mp4';
  static const String fallback = 'static_splash_image';
}
```

**App Startup Flow:**
```
┌─────────────────────────────────────────────────────────────┐
│                    App Launch                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│   VideoSplashScreen Widget                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ 1. Check cached video (path_provider)               │   │
│   │ 2. Fetch /api/v1/mobile/splash-video metadata       │   │
│   │ 3. Download video if URL changed                    │   │
│   │ 4. Play video (max 4 seconds)                       │   │
│   │ 5. Animated fade-out (500ms)                        │   │
│   └─────────────────────────────────────────────────────┘   │
│   Fallback: Static splash image if video unavailable        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│   Auth State Check → Navigate to Auth/Main Stack            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│   Branch Context Check                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ 1. Check Redis for session:{userId}:branch_context  │   │
│   │ 2. If found → proceed to Home Page (Quick Sale)     │   │
│   │ 3. If NOT found → redirect to Address Selection     │   │
│   │    a. User picks a saved address                    │   │
│   │    b. POST /api/v1/branch/resolve {address_id}      │   │
│   │    c. Backend maps post_office → branch_id          │   │
│   │    d. Branch context stored in Redis session        │   │
│   │    e. Redirect to Home Page (filtered by branch)    │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Admin Portal Configuration:**
- Location: Settings → App Settings → Splash Video
- Validation: Client-side duration check using HTML5 video element
- Instruction: "Please upload a 4-second MP4 video for the app splash screen"

---

## 🗄️ Database Schema (As-Built)

### PostgreSQL Tables

#### Core Tables
```sql
-- Users
users (user_id, email, password_hash, full_name, phone, is_verified, created_at)

-- Admin Users (Multi-Branch RBAC)
admin_users (admin_id, email, password_hash, full_name, role, branch_id, is_active)

-- Branches
branches (branch_id, name, code, address, city, phone, manager_id, is_active)

-- Branch Inventory
branch_inventory (inventory_id, branch_id, product_id, variant_id, stock_quantity, 
                  reserved_quantity, low_stock_threshold)

-- Stock Transfers
stock_transfers (transfer_id, from_branch_id, to_branch_id, product_id, variant_id,
                 quantity, status, requested_by_id, approved_by_id)
```

#### Product Tables
```sql
-- Products
products (product_id, name, slug, description, category_id, price, sku, 
          stock_quantity, is_active, has_variants, rating_average)

-- Product Images (1 Thumbnail + 4 Gallery)
product_images (image_id, product_id, image_url, is_primary, sort_order)

-- Variant Types
variant_types (variant_type_id, name, display_name, display_order)

-- Variant Options
variant_options (variant_option_id, variant_type_id, value, display_value, color_hex)

-- Product Variants
product_variants (variant_id, product_id, sku, price, stock_quantity, weight, image_url)

-- Variant-Option Mapping
product_variant_options (variant_id, variant_type_id, variant_option_id)
```

#### Order Tables
```sql
-- Orders
orders (order_id, user_id, branch_id, total_amount, status, payment_status,
        delivery_address_id, delivery_slot, created_at)

-- Order Items
order_items (order_item_id, order_id, product_id, variant_id, quantity, unit_price)
```

#### Wishlist Tables
```sql
-- Wishlist Items (with variant and price tracking)
wishlist_items (wishlist_item_id, user_id, product_id, variant_id, price_at_watch, added_at)
```

#### System Settings Tables
```sql
-- System Settings (App Configuration including Splash Video)
system_settings (
    setting_id UUID PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'splash_video'
    setting_value JSONB NOT NULL,               -- Configuration as JSON
    setting_type VARCHAR(50) DEFAULT 'system',  -- 'system' | 'app' | 'feature'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)

-- Example: Splash Video Setting
-- setting_key: 'splash_video'
-- setting_value: {
--     "video_url": "https://storage.example.com/splash/video.mp4",
--     "duration": 4.0,
--     "file_size": 2500000,
--     "mime_type": "video/mp4",
--     "uploaded_by": "admin-uuid",
--     "uploaded_at": "2026-01-29T10:30:00Z"
-- }
```

---

## 🔒 Security Architecture

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Redis
    participant PostgreSQL
    
    Client->>API: POST /auth/login (email, password)
    API->>PostgreSQL: Verify credentials
    PostgreSQL-->>API: User data
    API->>API: Generate JWT (access + refresh)
    API->>Redis: Store session data
    API-->>Client: {accessToken, refreshToken}
    
    Client->>API: GET /api/v1/resource (Bearer token)
    API->>API: Verify JWT signature
    API->>Redis: Check token blacklist
    API->>Redis: Validate session
    Redis-->>API: Session valid
    API-->>Client: Resource data
```

### Security Headers (Middleware)

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware

# Security headers middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom security headers via middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

### Rate Limiting

| Endpoint Type | Window | Max Requests |
|---------------|--------|--------------|
| General API | 15 min | 1000 |
| Auth Endpoints | 15 min | 5 |
| Password Reset | 1 hour | 3 |

### CORS Configuration

```python
# FastAPI CORS configuration
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if settings.ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Branch-ID"],
)
```

---

## 🚀 Deployment Architecture

### Docker Compose (Development)

```yaml
version: '3.8'
services:
  postgres_db:
    image: ankane/pgvector          # PostgreSQL 15 + pgvector
    container_name: sribees_postgres
    environment:
      POSTGRES_USER: sribees_user
      POSTGRES_PASSWORD: sribees_password_123
      POSTGRES_DB: sribeesonline
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sribees_user -d sribeesonline"]

  redis_cache:
    image: redis:7-alpine
    container_name: sribees_redis
    command: redis-server --appendonly yes --requirepass sribees_redis_password
    ports:
      - "6379:6379"

  s3-local:
    image: minio/minio               # S3-compatible object storage
    container_name: sribees_minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password123
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # MinIO Console UI

  fastapi_backend:
    build:
      context: ./fastapi_backend
      target: development            # hot-reload with uvicorn
    container_name: sribees_backend
    environment:
      DATABASE_URL: postgresql+asyncpg://sribees_user:sribees_password_123@postgres_db:5432/sribeesonline
      REDIS_URL: redis://:sribees_redis_password@redis_cache:6379/0
      S3_ENDPOINT_URL: http://s3-local:9000
      S3_PUBLIC_URL_PREFIX: http://localhost:9000/sribees-assets
      S3_EMULATOR_URL_PREFIX: http://10.0.2.2:9000/sribees-assets
    ports:
      - "8000:8000"
    depends_on:
      postgres_db: { condition: service_healthy }
      redis_cache: { condition: service_healthy }

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### Environment Variables

```bash
# Database
DATABASE_HOST=postgres_db
DATABASE_PORT=5432
DATABASE_NAME=sribeesonline
DATABASE_USER=sribees_user
DATABASE_PASSWORD=sribees_password_123

# Redis
REDIS_HOST=redis_cache
REDIS_PORT=6379
REDIS_PASSWORD=sribees_redis_password

# S3 / MinIO (local development)
AWS_ACCESS_KEY_ID=admin
AWS_SECRET_ACCESS_KEY=password123
S3_BUCKET_NAME=sribees-assets
S3_ENDPOINT_URL=http://s3-local:9000
S3_PUBLIC_URL_PREFIX=http://localhost:9000/sribees-assets
S3_EMULATOR_URL_PREFIX=http://10.0.2.2:9000/sribees-assets

# JWT
JWT_SECRET_KEY=local-dev-secret-key-change-in-production-123456
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API
API_VERSION=v1
PORT=8000
APP_ENV=development
```

---

## 📊 Monitoring & Observability

### Logging Strategy

```python
# Request logging middleware (Loguru)
from loguru import logger
import time

@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} "
        f"duration={duration:.2f}ms"
    )
    return response
```

### Admin Audit Logs

```sql
CREATE TABLE admin_audit_logs (
    log_id UUID PRIMARY KEY,
    admin_id UUID REFERENCES admin_users(admin_id),
    branch_id UUID REFERENCES branches(branch_id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🌱 Seeding System

### Available Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| `run_all_migrations.py` | Run all SQL migrations | `python scripts/run_all_migrations.py` |
| `seed_admin_system.py` | Seed branches, admins, inventory | `python scripts/seed_admin_system.py` |
| `seed_manager.py` | Seed watchlist data | `python scripts/seed_manager.py` |
| `seed-variants-images.js` | Seed product variants & images | `node seed-variants-images.js` |

### Recommended Execution Order

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Run migrations
python scripts/run_all_migrations.py

# 3. Seed admin RBAC system
python scripts/seed_admin_system.py

# 4. Seed product variants
python seed_variants_images.py
```

### Seeded Demo Data

| Entity | Count | Details |
|--------|-------|---------|
| Branches | 3 | Colombo, Kandy, Galle (Sri Lanka) |
| Admin Users | 10+ | Super admin, managers, staff per branch |
| Categories | 6 | Groceries, Produce, Dairy, etc. |
| Products | 10+ | With variants and images |
| Variant Types | 4 | Size, Color, Weight, Pack Size |

### Demo Credentials

| Email | Password | Role | Branch |
|-------|----------|------|--------|
| `superadmin@sribeesonline.lk` | `Admin@123` | super_admin | All |
| `manager.colombo@sribeesonline.lk` | `Admin@123` | branch_manager | Colombo |
| `staff1.colombo@sribeesonline.lk` | `Admin@123` | staff | Colombo |
| `inventory@sribeesonline.lk` | `Admin@123` | inventory | All |

---

## 📁 File Structure Summary

```
SRIBEESonline/
├── admin/                          # React Web Admin Dashboard
│   ├── src/
│   │   ├── api/                    # API layer (HTTP client)
│   │   ├── components/             # React components
│   │   ├── pages/                  # Route pages
│   │   ├── store/                  # State management
│   │   ├── types/                  # TypeScript types
│   │   └── hooks/                  # Custom hooks
│   ├── package.json
│   └── vite.config.ts
│
├── mobile/                         # Flutter Mobile App
│   ├── lib/
│   │   ├── api/                    # Dio HTTP layer
│   │   ├── widgets/                # Flutter widgets
│   │   ├── screens/                # Screen widgets
│   │   ├── providers/              # Riverpod providers
│   │   └── utils/                  # Utilities
│   ├── android/
│   ├── ios/
│   └── pubspec.yaml
│
├── fastapi_backend/                # Python FastAPI Backend
│   ├── app/
│   │   ├── api/                    # API routes
│   │   │   └── v1/                 # API v1 endpoints
│   │   ├── config/                 # Configuration
│   │   ├── core/                   # Core utilities (auth, security)
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/               # Business logic
│   │   └── utils/                  # Utilities
│   ├── alembic/                    # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
│
├── ARCHITECTURE.md                 # This document
├── FEATURES.md                     # Feature documentation
├── BACKEND_PLAN.md                 # Backend implementation plan
└── USER_STORIES_BREAKDOWN.md       # User stories
```

---

## 🐳 Verified Local Infrastructure (February 17, 2026)

### Container Status

| Container | Image | Port | Status |
|-----------|-------|------|--------|
| `sribees_postgres` | `ankane/pgvector` | 5432 | Healthy |
| `sribees_redis` | `redis:7-alpine` | 6379 | Healthy |
| `sribees_minio` | `minio/minio` | 9000, 9001 | Healthy |
| `sribees_backend` | `fastapi_backend:dev` | 8000 | Healthy |

### Service Endpoints

| Service | URL |
|---------|-----|
| FastAPI Swagger UI | http://localhost:8000/docs |
| FastAPI Health | http://localhost:8000/health |
| MinIO Console | http://localhost:9001 (admin / password123) |
| MinIO S3 API | http://localhost:9000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### Android Emulator Connectivity

The Flutter mobile app uses `10.0.2.2` (Android emulator's alias for host localhost):
- API: `http://10.0.2.2:8000/api/v1`
- MinIO: `http://10.0.2.2:9000/sribees-assets/...`

The `X-Client-Platform: android-emulator` header triggers URL rewriting in `storage_service.py`, converting `localhost` MinIO URLs to `10.0.2.2` for emulator access.

### Database Schema (sribees schema)

16 tables verified across `sribees` and `public` schemas:

| Schema | Tables |
|--------|--------|
| `sribees` | users, admin_users, branches, products, categories, addresses, carts, orders, wishlists, product_reviews, notifications, audit_logs, post_office_branch_mapping, branch_inventory |
| `sribees` | app_settings |

### MinIO Storage

- Bucket: `sribees-assets` (public-read)
- Splash Video: `splash/splash_video_initial.mp4` (539 KB)

*Document reflects the as-built implementation state as of February 2026.*
