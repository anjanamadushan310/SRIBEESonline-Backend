"""
SRIBEESonline - Wishlist API Endpoints

API routes for user wishlist operations.
"""
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.config.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.wishlist_service import WishlistService
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationTypeEnum


router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


# ============================================================================
# Schemas
# ============================================================================

class WishlistItemCreate(BaseModel):
    """Schema for adding item to wishlist."""
    product_id: UUID
    variant_id: Optional[UUID] = None
    price_at_watch: Optional[Decimal] = None  # Current price for price drop alerts


class WishlistItemResponse(BaseModel):
    """Schema for wishlist item response."""
    wishlist_item_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    price_at_watch: Optional[Decimal] = None
    added_at: str
    
    # Product details (populated)
    product_name: Optional[str] = None
    product_image: Optional[str] = None
    current_price: Optional[Decimal] = None
    is_in_stock: bool = True
    has_price_drop: bool = False
    
    class Config:
        from_attributes = True


class WishlistResponse(BaseModel):
    """Schema for full wishlist response."""
    items: List[WishlistItemResponse]
    total_items: int


class WishlistBulkRequest(BaseModel):
    """Schema for bulk wishlist operations."""
    product_ids: List[UUID]


class WishlistCheckResponse(BaseModel):
    """Schema for checking if products are in wishlist."""
    product_id: UUID
    in_wishlist: bool


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=WishlistResponse)
async def get_wishlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the current user's wishlist.
    
    Returns all wishlist items with product details.
    """
    items = await WishlistService.get_by_user_id(db, current_user.user_id)
    
    response_items = []
    for item in items:
        product = item.product
        
        # Calculate if there's a price drop
        has_price_drop = False
        current_price = product.sale_price or product.price if product else None
        
        if item.price_at_watch and current_price:
            has_price_drop = current_price < item.price_at_watch
        
        response_items.append(WishlistItemResponse(
            wishlist_item_id=item.wishlist_item_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            price_at_watch=item.price_at_watch,
            added_at=item.added_at.isoformat() if item.added_at else "",
            product_name=product.name if product else None,
            product_image=product.images[0].image_url if product and product.images else None,
            current_price=current_price,
            is_in_stock=product.stock_quantity > 0 if product else False,
            has_price_drop=has_price_drop,
        ))
    
    return WishlistResponse(
        items=response_items,
        total_items=len(response_items),
    )


@router.post("", response_model=WishlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_wishlist(
    data: WishlistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a product to the wishlist.
    
    If product already exists, updates the price_at_watch.
    """
    item = await WishlistService.add_item(
        db,
        user_id=current_user.user_id,
        product_id=data.product_id,
        variant_id=data.variant_id,
        price_at_watch=data.price_at_watch,
    )
    
    # Refresh to get product details
    await db.refresh(item)
    product = item.product
    
    return WishlistItemResponse(
        wishlist_item_id=item.wishlist_item_id,
        product_id=item.product_id,
        variant_id=item.variant_id,
        price_at_watch=item.price_at_watch,
        added_at=item.added_at.isoformat() if item.added_at else "",
        product_name=product.name if product else None,
        product_image=product.images[0].image_url if product and product.images else None,
        current_price=product.sale_price or product.price if product else None,
        is_in_stock=product.stock_quantity > 0 if product else False,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    product_id: UUID,
    variant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a product from the wishlist."""
    removed = await WishlistService.remove_item(
        db,
        user_id=current_user.user_id,
        product_id=product_id,
        variant_id=variant_id,
    )
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in wishlist",
        )


@router.post("/check", response_model=List[WishlistCheckResponse])
async def check_wishlist_status(
    data: WishlistBulkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if multiple products are in the wishlist.
    
    Useful for displaying wishlist status on product listings.
    """
    wishlist_items = await WishlistService.get_by_user_id(db, current_user.user_id)
    wishlist_product_ids = {item.product_id for item in wishlist_items}
    
    return [
        WishlistCheckResponse(
            product_id=pid,
            in_wishlist=pid in wishlist_product_ids,
        )
        for pid in data.product_ids
    ]


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_wishlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear all items from the wishlist."""
    await WishlistService.clear_wishlist(db, current_user.user_id)


@router.post("/move-to-cart/{product_id}")
async def move_to_cart(
    product_id: UUID,
    variant_id: Optional[UUID] = Query(None),
    quantity: int = Query(1, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Move an item from wishlist to cart.
    
    Adds to cart and removes from wishlist.
    """
    from app.services.cart_service import CartService
    
    # Add to cart
    cart = await CartService.add_item(
        db,
        user_id=current_user.user_id,
        product_id=product_id,
        variant_id=variant_id,
        quantity=quantity,
    )
    
    # Remove from wishlist
    await WishlistService.remove_item(
        db,
        user_id=current_user.user_id,
        product_id=product_id,
        variant_id=variant_id,
    )
    
    return {"message": "Item moved to cart", "cart_item_count": len(cart.items) if cart else 0}
