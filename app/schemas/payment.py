"""
Payment Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ============================================================================
# Request Schemas
# ============================================================================

class CreatePaymentIntentRequest(BaseModel):
    """Request to create a payment intent."""
    order_id: str
    payment_method: str = "card"  # card, upi, netbanking


class ConfirmPaymentRequest(BaseModel):
    """Request to confirm a payment."""
    payment_intent_id: str
    payment_method_id: Optional[str] = None


class RefundRequest(BaseModel):
    """Request to create a refund."""
    order_id: str
    amount: Optional[float] = None  # None = full refund
    reason: Optional[str] = None


# ============================================================================
# Response Schemas
# ============================================================================

class PaymentIntentResponse(BaseModel):
    """Payment intent response."""
    payment_intent_id: str
    client_secret: str
    amount: float
    currency: str = "inr"
    status: str


class PaymentResponse(BaseModel):
    """Payment confirmation response."""
    success: bool = True
    data: dict
    message: str


class RefundResponse(BaseModel):
    """Refund response."""
    refund_id: str
    amount: float
    status: str
    created_at: datetime


# ============================================================================
# Saved Cards Schemas
# ============================================================================

class SaveCardRequest(BaseModel):
    """Request to save a card."""
    payment_method_id: str = Field(..., description="Stripe payment method ID")
    set_default: bool = Field(False, description="Set as default payment method")


class SavedCardResponse(BaseModel):
    """Saved card response."""
    card_id: str = Field(..., alias="cardId")
    brand: str  # visa, mastercard, amex, etc.
    last4: str
    exp_month: int = Field(..., alias="expMonth")
    exp_year: int = Field(..., alias="expYear")
    is_default: bool = Field(False, alias="isDefault")
    created_at: datetime = Field(..., alias="createdAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class SavedCardsListResponse(BaseModel):
    """List of saved cards response."""
    success: bool = True
    cards: list[SavedCardResponse]


class PaymentHistoryItem(BaseModel):
    """Payment history item."""
    payment_id: str = Field(..., alias="paymentId")
    order_id: str = Field(..., alias="orderId")
    amount: float
    currency: str = "inr"
    status: str
    payment_method: str = Field(..., alias="paymentMethod")
    created_at: datetime = Field(..., alias="createdAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True


class PaymentHistoryResponse(BaseModel):
    """Payment history response."""
    success: bool = True
    payments: list[PaymentHistoryItem]
    total: int
