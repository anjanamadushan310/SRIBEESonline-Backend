"""
Notification Pydantic Schemas
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================

class NotificationTypeEnum(str, Enum):
    ORDER_STATUS = "order_status"
    PAYMENT = "payment"
    PROMOTION = "promotion"
    PRICE_DROP = "price_drop"
    SYSTEM = "system"
    DELIVERY = "delivery"


# ============================================================================
# Request Schemas
# ============================================================================

class CreateNotificationRequest(BaseModel):
    """Request to create a notification (admin)."""
    user_id: str
    type: NotificationTypeEnum = NotificationTypeEnum.SYSTEM
    title: str = Field(..., min_length=1, max_length=255)
    message: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    data: Optional[dict] = None
    send_push: bool = True


class BroadcastNotificationRequest(BaseModel):
    """Request to broadcast notification to all users (admin)."""
    type: NotificationTypeEnum = NotificationTypeEnum.PROMOTION
    title: str = Field(..., min_length=1, max_length=255)
    message: str
    data: Optional[dict] = None
    send_push: bool = True


class RegisterPushTokenRequest(BaseModel):
    """Request to register push notification token."""
    token: str
    device_type: Optional[str] = None  # ios, android
    device_name: Optional[str] = None


# ============================================================================
# Response Schemas
# ============================================================================

class NotificationResponse(BaseModel):
    """Notification response."""
    notification_id: str
    type: str
    title: str
    message: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    data: Optional[dict] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Notification list response."""
    success: bool = True
    data: dict


class NotificationCountResponse(BaseModel):
    """Unread notification count."""
    success: bool = True
    data: dict


class PushTokenResponse(BaseModel):
    """Push token response."""
    token_id: str
    token: str
    device_type: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
