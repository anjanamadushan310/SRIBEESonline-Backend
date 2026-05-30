"""
Order Pydantic Schemas
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================

class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


# ============================================================================
# Order Item Schemas
# ============================================================================

class OrderItemCreate(BaseModel):
    """Schema for order item during creation."""
    product_id: str
    variant_id: Optional[str] = None
    product_name: str
    product_sku: Optional[str] = None
    product_image: Optional[str] = None
    quantity: int = Field(..., ge=1)
    unit_price: Decimal


class OrderItemResponse(BaseModel):
    """Order item in response."""
    order_item_id: str
    product_id: str
    variant_id: Optional[str] = None
    product_name: str
    product_sku: Optional[str] = None
    product_image: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float
    tax_amount: float = 0

    model_config = {"from_attributes": True}


# ============================================================================
# Address Schemas
# ============================================================================

class DeliveryAddressSchema(BaseModel):
    """Delivery address in order response."""
    address_id: str
    address_line1: str
    address_line2: Optional[str] = None
    post_office: str
    district: str
    postal_code: str
    province: str


# ============================================================================
# Order Request Schemas
# ============================================================================

class CreateOrderRequest(BaseModel):
    """Request to create an order."""
    delivery_address_id: str
    delivery_slot_date: Optional[datetime] = None
    delivery_slot_time: Optional[str] = None
    payment_method: str = "cod"  # cod, card, upi
    coupon_code: Optional[str] = None
    notes: Optional[str] = None


class UpdateOrderStatusRequest(BaseModel):
    """Request to update order status."""
    status: OrderStatusEnum


class UpdatePaymentStatusRequest(BaseModel):
    """Request to update payment status."""
    payment_status: PaymentStatusEnum
    payment_id: Optional[str] = None


# ============================================================================
# Order Response Schemas
# ============================================================================

class OrderSummary(BaseModel):
    """Order summary for list views."""
    order_id: str
    order_number: str
    status: str
    payment_status: str
    total_amount: float
    item_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    """Full order response."""
    order_id: str
    order_number: str
    user_id: str

    # Amounts
    subtotal: float
    tax_amount: float
    shipping_amount: float
    discount_amount: float
    total_amount: float

    # Status
    status: str
    payment_status: str
    payment_method: Optional[str] = None
    payment_id: Optional[str] = None

    # Delivery
    delivery_address: Optional[DeliveryAddressSchema] = None
    delivery_slot_date: Optional[datetime] = None
    delivery_slot_time: Optional[str] = None

    # Additional
    coupon_code: Optional[str] = None
    notes: Optional[str] = None

    # Items
    items: List[OrderItemResponse] = []

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrdersListResponse(BaseModel):
    """Response for orders list."""
    success: bool = True
    data: dict


class OrderDetailResponse(BaseModel):
    """Response for single order."""
    success: bool = True
    data: OrderResponse


class OrderCreateResponse(BaseModel):
    """Response after creating an order."""
    success: bool = True
    data: OrderResponse
    message: str = "Order placed successfully"
