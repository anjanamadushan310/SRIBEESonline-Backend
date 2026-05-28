"""
SRIBEESonline - Review Service

Business logic for product reviews and ratings.
"""
from typing import Optional, List, Tuple, Dict
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, and_, update, case
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.review import ProductReview, ReviewVote
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewSummary


class ReviewService:
    """Service class for product review operations."""
    
    @staticmethod
    async def create_review(
        db: AsyncSession,
        user_id: UUID,
        data: ReviewCreate,
    ) -> ProductReview:
        """
        Create a new product review.
        
        Checks if user has purchased the product for verified status.
        """
        # Check if user already reviewed this product
        existing = await db.execute(
            select(ProductReview).where(
                and_(
                    ProductReview.product_id == data.product_id,
                    ProductReview.user_id == user_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("You have already reviewed this product")
        
        # Check if this is a verified purchase
        is_verified = await ReviewService._is_verified_purchase(
            db, user_id, data.product_id, data.order_id
        )
        
        # Create review
        review = ProductReview(
            product_id=data.product_id,
            user_id=user_id,
            order_id=data.order_id,
            rating=data.rating,
            title=data.title,
            comment=data.comment,
            is_verified_purchase=is_verified,
        )
        
        db.add(review)
        await db.commit()
        await db.refresh(review)
        
        # Update product average rating
        await ReviewService._update_product_rating(db, data.product_id)
        
        logger.info(f"Review created: {review.review_id} for product {data.product_id}")
        
        return review
    
    @staticmethod
    async def _is_verified_purchase(
        db: AsyncSession,
        user_id: UUID,
        product_id: UUID,
        order_id: Optional[UUID] = None,
    ) -> bool:
        """Check if user has purchased the product."""
        query = (
            select(OrderItem)
            .join(Order, Order.order_id == OrderItem.order_id)
            .where(
                and_(
                    Order.user_id == user_id,
                    OrderItem.product_id == product_id,
                    Order.status.in_(["delivered", "completed"]),
                )
            )
        )
        
        if order_id:
            query = query.where(Order.order_id == order_id)
        
        result = await db.execute(query.limit(1))
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def _update_product_rating(db: AsyncSession, product_id: UUID) -> None:
        """Update product's average rating and review count."""
        stats = await db.execute(
            select(
                func.avg(ProductReview.rating).label("avg_rating"),
                func.count(ProductReview.review_id).label("review_count"),
            )
            .where(
                and_(
                    ProductReview.product_id == product_id,
                    ProductReview.is_approved == True,
                )
            )
        )
        row = stats.first()
        
        if row:
            await db.execute(
                update(Product)
                .where(Product.product_id == product_id)
                .values(
                    average_rating=row.avg_rating or 0,
                    review_count=row.review_count or 0,
                )
            )
            await db.commit()
    
    @staticmethod
    async def get_review(db: AsyncSession, review_id: UUID) -> Optional[ProductReview]:
        """Get a single review by ID."""
        result = await db.execute(
            select(ProductReview)
            .options(selectinload(ProductReview.user))
            .where(ProductReview.review_id == review_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_product_reviews(
        db: AsyncSession,
        product_id: UUID,
        limit: int = 10,
        offset: int = 0,
        sort_by: str = "newest",
        rating_filter: Optional[int] = None,
        verified_only: bool = False,
    ) -> Tuple[List[ProductReview], int]:
        """
        Get reviews for a product with filtering and sorting.
        """
        query = (
            select(ProductReview)
            .options(selectinload(ProductReview.user))
            .where(
                and_(
                    ProductReview.product_id == product_id,
                    ProductReview.is_approved == True,
                )
            )
        )
        
        # Filters
        if rating_filter:
            query = query.where(ProductReview.rating == rating_filter)
        
        if verified_only:
            query = query.where(ProductReview.is_verified_purchase == True)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Sorting
        if sort_by == "helpful":
            query = query.order_by(ProductReview.helpful_count.desc())
        elif sort_by == "rating_high":
            query = query.order_by(ProductReview.rating.desc())
        elif sort_by == "rating_low":
            query = query.order_by(ProductReview.rating.asc())
        else:  # newest
            query = query.order_by(ProductReview.created_at.desc())
        
        # Pagination
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        reviews = result.scalars().all()
        
        return reviews, total
    
    @staticmethod
    async def get_user_reviews(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[ProductReview], int]:
        """Get all reviews by a user."""
        query = (
            select(ProductReview)
            .options(selectinload(ProductReview.product))
            .where(ProductReview.user_id == user_id)
            .order_by(ProductReview.created_at.desc())
        )
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        
        return result.scalars().all(), total
    
    @staticmethod
    async def update_review(
        db: AsyncSession,
        review_id: UUID,
        user_id: UUID,
        data: ReviewUpdate,
    ) -> Optional[ProductReview]:
        """Update a review (only by owner)."""
        result = await db.execute(
            select(ProductReview).where(
                and_(
                    ProductReview.review_id == review_id,
                    ProductReview.user_id == user_id,
                )
            )
        )
        review = result.scalar_one_or_none()
        
        if not review:
            return None
        
        # Update fields
        if data.rating is not None:
            review.rating = data.rating
        if data.title is not None:
            review.title = data.title
        if data.comment is not None:
            review.comment = data.comment
        
        review.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(review)
        
        # Update product rating
        await ReviewService._update_product_rating(db, review.product_id)
        
        return review
    
    @staticmethod
    async def delete_review(
        db: AsyncSession,
        review_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a review (only by owner)."""
        result = await db.execute(
            select(ProductReview).where(
                and_(
                    ProductReview.review_id == review_id,
                    ProductReview.user_id == user_id,
                )
            )
        )
        review = result.scalar_one_or_none()
        
        if not review:
            return False
        
        product_id = review.product_id
        
        await db.delete(review)
        await db.commit()
        
        # Update product rating
        await ReviewService._update_product_rating(db, product_id)
        
        return True
    
    @staticmethod
    async def vote_review(
        db: AsyncSession,
        review_id: UUID,
        user_id: UUID,
        is_helpful: bool,
    ) -> Tuple[int, int, Optional[bool]]:
        """
        Vote on a review's helpfulness.
        
        Returns: (helpful_count, not_helpful_count, user_vote)
        """
        # Check existing vote
        result = await db.execute(
            select(ReviewVote).where(
                and_(
                    ReviewVote.review_id == review_id,
                    ReviewVote.user_id == user_id,
                )
            )
        )
        existing_vote = result.scalar_one_or_none()
        
        # Get review
        review_result = await db.execute(
            select(ProductReview).where(ProductReview.review_id == review_id)
        )
        review = review_result.scalar_one_or_none()
        
        if not review:
            raise ValueError("Review not found")
        
        if existing_vote:
            if existing_vote.is_helpful == is_helpful:
                # Same vote - remove it (toggle off)
                if is_helpful:
                    review.helpful_count = max(0, review.helpful_count - 1)
                else:
                    review.not_helpful_count = max(0, review.not_helpful_count - 1)
                
                await db.delete(existing_vote)
                user_vote = None
            else:
                # Different vote - update
                if is_helpful:
                    review.helpful_count += 1
                    review.not_helpful_count = max(0, review.not_helpful_count - 1)
                else:
                    review.not_helpful_count += 1
                    review.helpful_count = max(0, review.helpful_count - 1)
                
                existing_vote.is_helpful = is_helpful
                user_vote = is_helpful
        else:
            # New vote
            vote = ReviewVote(
                review_id=review_id,
                user_id=user_id,
                is_helpful=is_helpful,
            )
            db.add(vote)
            
            if is_helpful:
                review.helpful_count += 1
            else:
                review.not_helpful_count += 1
            
            user_vote = is_helpful
        
        await db.commit()
        
        return review.helpful_count, review.not_helpful_count, user_vote
    
    @staticmethod
    async def get_review_summary(
        db: AsyncSession,
        product_id: UUID,
    ) -> ReviewSummary:
        """Get review statistics for a product."""
        # Get rating distribution
        dist_query = (
            select(
                ProductReview.rating,
                func.count(ProductReview.review_id).label("count"),
            )
            .where(
                and_(
                    ProductReview.product_id == product_id,
                    ProductReview.is_approved == True,
                )
            )
            .group_by(ProductReview.rating)
        )
        
        dist_result = await db.execute(dist_query)
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for row in dist_result:
            rating_dist[row.rating] = row.count
        
        # Get aggregate stats
        stats_query = select(
            func.count(ProductReview.review_id).label("total"),
            func.avg(ProductReview.rating).label("avg_rating"),
            func.sum(
                case((ProductReview.is_verified_purchase == True, 1), else_=0)
            ).label("verified_count"),
            func.sum(
                case((ProductReview.comment.isnot(None), 1), else_=0)
            ).label("with_comments"),
        ).where(
            and_(
                ProductReview.product_id == product_id,
                ProductReview.is_approved == True,
            )
        )
        
        stats_result = await db.execute(stats_query)
        stats = stats_result.first()
        
        return ReviewSummary(
            product_id=product_id,
            total_reviews=stats.total or 0,
            average_rating=float(stats.avg_rating or 0),
            rating_distribution=rating_dist,
            verified_purchase_count=stats.verified_count or 0,
            with_comments_count=stats.with_comments or 0,
        )
