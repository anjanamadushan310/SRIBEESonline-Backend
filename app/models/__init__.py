"""
SRIBEESonline FastAPI Backend - Models Module

SQLAlchemy ORM models for all database tables.
"""
from app.models.user import (
    User,
    EmailVerification,
    PasswordReset,
    Session,
    Address,
)
from app.models.category import Category
from app.models.product import (
    BranchInventory,
    Product,
    ProductImage,
    ProductVariant,
    VariantType,
    VariantOption,
    Review,
)
from app.models.wishlist import WishlistItem
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.notification import Notification, PushToken, NotificationType
from app.models.admin import Admin, AdminSession, AdminRole
from app.models.branch import Branch, PostOfficeBranchMapping
from app.models.app_settings import AppSetting

__all__ = [
    # User models
    "User",
    "EmailVerification",
    "PasswordReset",
    "Session",
    "Address",
    # Category
    "Category",
    # Product models
    "BranchInventory",
    "Product",
    "ProductImage",
    "ProductVariant",
    "VariantType",
    "VariantOption",
    "Review",
    # Wishlist
    "WishlistItem",
    # Order models
    "Order",
    "OrderItem",
    "OrderStatus",
    "PaymentStatus",
    # Notification models
    "Notification",
    "PushToken",
    "NotificationType",
    # Admin & RBAC models
    "Admin",
    "AdminSession",
    "AdminRole",
    # Branch models
    "Branch",
    "PostOfficeBranchMapping",
    # App settings
    "AppSetting",
]
