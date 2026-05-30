"""
Wishlist Model
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class WishlistItem(Base):
    """Wishlist item model."""

    __tablename__ = "wishlist_items"

    wishlist_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.variant_id", ondelete="SET NULL"), nullable=True)
    price_at_watch = Column(Numeric(10, 2), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="wishlist_items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', 'variant_id', name='uq_wishlist_user_product_variant'),
    )

    def __repr__(self):
        return f"<WishlistItem {self.wishlist_item_id}>"
