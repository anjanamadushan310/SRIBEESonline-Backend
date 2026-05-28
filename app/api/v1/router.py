"""
FreshCart FastAPI Backend - API v1 Router

Main router that aggregates all API v1 endpoints.
"""
from fastapi import APIRouter

from app.api.v1 import auth
from app.api.v1 import categories
from app.api.v1 import products
from app.api.v1 import cart
from app.api.v1 import wishlist
from app.api.v1 import orders
from app.api.v1 import payments
from app.api.v1 import notifications
from app.api.v1 import admin
from app.api.v1 import admin_auth
from app.api.v1 import admin_locations
from app.api.v1 import admin_settings
from app.api.v1 import app_public
from app.api.v1 import branch
from app.api.v1 import inventory
from app.api.v1 import locations
from app.api.v1 import marketing
from app.api.v1 import search

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include module routers
router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

router.include_router(
    categories.router,
    prefix="/categories",
    tags=["Categories"],
)

router.include_router(
    products.router,
    prefix="/products",
    tags=["Products"],
)

router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"],
)

router.include_router(
    cart.router,
    prefix="/cart",
    tags=["Cart"],
)

router.include_router(
    wishlist.router,
    prefix="/wishlist",
    tags=["Wishlist"],
)

router.include_router(
    orders.router,
    prefix="/orders",
    tags=["Orders"],
)

router.include_router(
    payments.router,
    prefix="/payments",
    tags=["Payments"],
)

router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notifications"],
)

router.include_router(
    branch.router,
    prefix="/branch",
    tags=["Branch Routing"],
)

router.include_router(
    locations.router,
    prefix="/locations",
    tags=["Location Discovery"],
)

router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"],
)

router.include_router(
    admin_auth.router,
    prefix="/admin/auth",
    tags=["Admin Authentication"],
)

router.include_router(
    admin_locations.router,
    prefix="/admin/locations",
    tags=["Admin Location Management"],
)

router.include_router(
    inventory.router,
    prefix="/inventory",
    tags=["Inventory Management"],
)

router.include_router(
    admin_settings.router,
    prefix="/admin/settings",
    tags=["Admin Settings"],
)

router.include_router(
    marketing.router,
    prefix="/admin/marketing",
    tags=["Marketing Management"],
)

router.include_router(
    app_public.router,
    prefix="/app",
    tags=["App Configuration"],
)
