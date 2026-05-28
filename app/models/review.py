"""
SRIBEESonline - Product Review Model

Database models for product reviews and ratings.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, 
    ForeignKey, CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.database import Base


class ProductReview(Base):
    """Product review and rating model."""
    
    __tablename__ = "product_reviews"
    
    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Relationships
    product_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("products.product_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("orders.order_id", ondelete="SET NULL"),
        nullable=True,  # Optional: link to purchase
    )
    
    # Rating (1-5 stars)
    rating = Column(Integer, nullable=False)
    
    # Review content
    title = Column(String(200), nullable=True)
    comment = Column(Text, nullable=True)
    
    # Review images
    # images = relationship("ReviewImage", back_populates="review", cascade="all, delete-orphan")
    
    # Moderation
    is_verified_purchase = Column(Boolean, default=False)  # User actually bought the product
    is_approved = Column(Boolean, default=True)  # Moderation status
    is_featured = Column(Boolean, default=False)  # Highlighted review
    
    # Helpful votes
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    votes = relationship("ReviewVote", back_populates="review", cascade="all, delete-orphan")
    
    __table_args__ = (
        # Rating must be 1-5
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        # One review per user per product
        UniqueConstraint("product_id", "user_id", name="uq_product_user_review"),
        # Index for common queries
        Index("ix_reviews_product_rating", "product_id", "rating"),
        Index("ix_reviews_created", "created_at"),
    )


class ReviewVote(Base):
    """Tracks helpful/not helpful votes on reviews."""
    
    __tablename__ = "review_votes"
    
    vote_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    review_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_reviews.review_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    
    is_helpful = Column(Boolean, nullable=False)  # True = helpful, False = not helpful
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    review = relationship("ProductReview", back_populates="votes")
    user = relationship("User")
    
    __table_args__ = (
        # One vote per user per review
        UniqueConstraint("review_id", "user_id", name="uq_review_user_vote"),
    )


class ReviewImage(Base):
    """Images attached to reviews."""
    
    __tablename__ = "review_images"
    
    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    review_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_reviews.review_id", ondelete="CASCADE"),
        nullable=False,
    )
    
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    display_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
