"""
Order Pydantic Schemas
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Enums
# ============================================================================


class PaymentMethodEnum(str, Enum):
    """Payment methods supported for the MVP (COD + internal wallet)."""
    COD = "COD"
    WALLET = "WALLET"

class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURN_REQUESTED = "return_requested"
    RETURN_APPROVED = "return_approved"
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


class OrderStatusStep(BaseModel):
    """A single step in the order status timeline."""
    status: str
    label: str
    timestamp: Optional[datetime] = None
    completed: bool = False
    current: bool = False


# ============================================================================
# Order Request Schemas
# ============================================================================

class CreateOrderRequest(BaseModel):
    """Request to create an order."""
    delivery_address_id: str
    delivery_slot_date: Optional[datetime] = None
    delivery_slot_time: Optional[str] = None
    # MVP payment methods: COD (Cash on Delivery) or WALLET. Card/UPI are on hold.
    payment_method: str = "COD"
    coupon_code: Optional[str] = None
    # When true, the available wallet balance is applied to reduce the total.
    use_wallet: bool = False
    notes: Optional[str] = None

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        """Accept only COD/WALLET (case-insensitive); reject anything else."""
        normalized = (v or "").strip().upper()
        allowed = {m.value for m in PaymentMethodEnum}
        if normalized not in allowed:
            raise ValueError(
                f"payment_method must be one of {sorted(allowed)} (got '{v}')"
            )
        return normalized


class QuoteOrderRequest(BaseModel):
    """
    Request to preview order totals without persisting anything.

    Mirrors the pricing-relevant fields of CreateOrderRequest. The coupon and
    cart contents are read from the user's server-side cart; `coupon_code` is
    accepted for API symmetry/forward-compat but the applied cart coupon is
    authoritative.
    """
    delivery_address_id: Optional[str] = None
    use_wallet: bool = False
    coupon_code: Optional[str] = None


class ReturnItemSchema(BaseModel):
    """A single order item being returned."""
    order_item_id: str
    quantity: int = Field(..., ge=1)


class ReturnRequest(BaseModel):
    """Customer request to return a delivered order (Module 5.5)."""
    reason: str = Field(..., min_length=1, max_length=255)
    comments: Optional[str] = None
    # Optional item-level selection; empty means a full-order return.
    items: List[ReturnItemSchema] = Field(default_factory=list)


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
    wallet_deduction: float = 0
    cashback_earned: float = 0
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
    item_count: int = 0

    # Status timeline (derived from status + timestamps)
    status_timeline: List[OrderStatusStep] = []

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


class OrderQuoteBreakdown(BaseModel):
    """Authoritative, server-calculated financial breakdown (no persistence)."""
    subtotal: float
    delivery_fee: float
    discount: float
    tax: float
    wallet_deduction: float
    cashback_earned: float
    total: float
    # Context so the client can render wallet UI without a second call.
    currency: str = "LKR"
    cashback_rate: float
    wallet_balance: float
    wallet_applied: bool
    item_count: int


class OrderQuoteResponse(BaseModel):
    """Response wrapper for POST /orders/quote."""
    success: bool = True
    data: OrderQuoteBreakdown
