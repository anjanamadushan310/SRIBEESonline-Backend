"""
Notification SQLAlchemy Models
"""
import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class NotificationType(str, enum.Enum):
    """Notification types."""
    ORDER_STATUS = "order_status"
    PAYMENT = "payment"
    PROMOTION = "promotion"
    PRICE_DROP = "price_drop"
    SYSTEM = "system"
    DELIVERY = "delivery"


class Notification(Base):
    """User notification model."""

    __tablename__ = "notifications"

    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    type = Column(String(50), default=NotificationType.SYSTEM.value)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Optional reference to related entity
    reference_type = Column(String(50), nullable=True)  # order, product, etc.
    reference_id = Column(UUID(as_uuid=True), nullable=True)

    # Additional data (JSON)
    data = Column(JSONB, nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Push notification
    push_sent = Column(Boolean, default=False)
    push_sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.notification_id}>"


class PushToken(Base):
    """User push notification token (Expo)."""

    __tablename__ = "push_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    device_type = Column(String(50), nullable=True)  # ios, android
    device_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="push_tokens")

    def __repr__(self):
        return f"<PushToken {self.token_id}>"
