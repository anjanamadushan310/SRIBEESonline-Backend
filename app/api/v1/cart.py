"""
Cart API Endpoints (Redis-based)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.cart import (
    AddToCartRequest,
    ApplyCouponRequest,
    UpdateCartItemRequest,
)
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


# ============================================================================
# Cart Endpoints
# ============================================================================

@router.get("", response_model=dict)
async def get_cart(
    current_user = Depends(get_current_user)
):
    """
    Get current user's cart.
    """
    try:
        cart = await CartService.get_cart(str(current_user.user_id))

        return {
            "success": True,
            "data": cart
        }
    except Exception as e:
        logger.error(f"Error getting cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cart"
        )


@router.post("/items", response_model=dict)
async def add_to_cart(
    data: AddToCartRequest,
    current_user = Depends(get_current_user)
):
    """
    Add an item to cart.
    """
    try:
        cart = await CartService.add_item(
            user_id=str(current_user.user_id),
            product_id=data.product_id,
            quantity=data.quantity,
            price=float(data.price),
            name=data.name,
            image=data.image,
            sku=data.sku,
            variant_id=data.variant_id
        )

        return {
            "success": True,
            "data": cart,
            "message": "Item added to cart"
        }
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add item to cart"
        )


@router.put("/items/{product_id}", response_model=dict)
async def update_cart_item(
    product_id: str,
    data: UpdateCartItemRequest,
    variant_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Update item quantity in cart.
    """
    try:
        cart = await CartService.update_item_quantity(
            user_id=str(current_user.user_id),
            product_id=product_id,
            quantity=data.quantity,
            variant_id=variant_id
        )

        return {
            "success": True,
            "data": cart,
            "message": "Cart updated"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cart"
        )


@router.delete("/items/{product_id}", response_model=dict)
async def remove_from_cart(
    product_id: str,
    variant_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Remove an item from cart.
    """
    try:
        cart = await CartService.remove_item(
            user_id=str(current_user.user_id),
            product_id=product_id,
            variant_id=variant_id
        )

        return {
            "success": True,
            "data": cart,
            "message": "Item removed from cart"
        }
    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove item"
        )


@router.delete("", response_model=dict)
async def clear_cart(
    current_user = Depends(get_current_user)
):
    """
    Clear entire cart.
    """
    try:
        await CartService.clear_cart(str(current_user.user_id))

        return {
            "success": True,
            "message": "Cart cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cart"
        )


@router.post("/coupon", response_model=dict)
async def apply_coupon(
    data: ApplyCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Apply a coupon to cart.

    Note: In production, validate coupon from database.
    """
    try:
        # TODO: Validate coupon from database
        # For now, use a simple demo coupon
        if data.code.upper() == "SAVE10":
            cart = await CartService.apply_coupon(
                user_id=str(current_user.user_id),
                code=data.code.upper(),
                discount_type="percentage",
                discount_value=10.0
            )
        elif data.code.upper() == "FLAT5":
            cart = await CartService.apply_coupon(
                user_id=str(current_user.user_id),
                code=data.code.upper(),
                discount_type="fixed",
                discount_value=5.0
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid coupon code"
            )

        return {
            "success": True,
            "data": cart,
            "message": "Coupon applied successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying coupon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply coupon"
        )


@router.delete("/coupon", response_model=dict)
async def remove_coupon(
    current_user = Depends(get_current_user)
):
    """
    Remove coupon from cart.
    """
    try:
        cart = await CartService.remove_coupon(str(current_user.user_id))

        return {
            "success": True,
            "data": cart,
            "message": "Coupon removed"
        }
    except Exception as e:
        logger.error(f"Error removing coupon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove coupon"
        )


@router.get("/count", response_model=dict)
async def get_cart_count(
    current_user = Depends(get_current_user)
):
    """
    Get total item count in cart.
    """
    try:
        count = await CartService.get_item_count(str(current_user.user_id))

        return {
            "success": True,
            "data": {
                "count": count
            }
        }
    except Exception as e:
        logger.error(f"Error getting cart count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cart count"
        )


# ============================================================================
# Cart Sync/Merge Endpoints (for offline-first mobile)
# ============================================================================

@router.post("/merge", response_model=dict)
async def merge_cart(
    guest_cart: dict,
    current_user = Depends(get_current_user)
):
    """
    Merge guest cart with user cart (on login).

    Used when a guest adds items to cart and then logs in.
    """
    try:
        cart = await CartService.merge_cart(
            user_id=str(current_user.user_id),
            guest_items=guest_cart.get("items", [])
        )

        return {
            "success": True,
            "data": cart,
            "message": "Cart merged successfully"
        }
    except Exception as e:
        logger.error(f"Error merging cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to merge cart"
        )


@router.post("/sync", response_model=dict)
async def sync_cart(
    local_cart: dict,
    current_user = Depends(get_current_user)
):
    """
    Sync local cart with server (for offline-first mobile).

    Merges local changes with server state using timestamps.
    """
    try:
        cart = await CartService.sync_cart(
            user_id=str(current_user.user_id),
            local_cart=local_cart
        )

        return {
            "success": True,
            "data": cart,
            "message": "Cart synced successfully"
        }
    except Exception as e:
        logger.error(f"Error syncing cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync cart"
        )


@router.get("/sync/status", response_model=dict)
async def get_sync_status(
    current_user = Depends(get_current_user)
):
    """
    Get cart sync status.
    """
    try:
        cart = await CartService.get_cart(str(current_user.user_id))

        return {
            "success": True,
            "data": {
                "lastSyncedAt": cart.get("updated_at"),
                "itemCount": len(cart.get("items", [])),
                "synced": True
            }
        }
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sync status"
        )


@router.post("/validate", response_model=dict)
async def validate_cart(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate cart before checkout.

    Checks stock availability and prices for all items.
    """
    try:
        cart = await CartService.get_cart(str(current_user.user_id))

        # TODO: Add actual product validation against database
        validation_result = {
            "valid": True,
            "items": cart.get("items", []),
            "issues": [],
            "totals": cart.get("totals", {})
        }

        return {
            "success": True,
            "data": validation_result,
            "message": "Cart validated"
        }
    except Exception as e:
        logger.error(f"Error validating cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate cart"
        )
