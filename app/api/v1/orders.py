"""
Order API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from loguru import logger

from app.config.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.services.order_service import OrderService
from app.schemas.order import (
    CreateOrderRequest,
    UpdateOrderStatusRequest,
    UpdatePaymentStatusRequest,
    OrderStatusEnum,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


# ============================================================================
# Helper Functions
# ============================================================================

def format_order(order, include_items: bool = True) -> dict:
    """Format order for API response."""
    data = {
        "order_id": str(order.order_id),
        "order_number": order.order_number,
        "user_id": str(order.user_id),
        "subtotal": float(order.subtotal),
        "tax_amount": float(order.tax_amount),
        "shipping_amount": float(order.shipping_amount),
        "discount_amount": float(order.discount_amount),
        "total_amount": float(order.total_amount),
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "payment_id": order.payment_id,
        "delivery_slot_date": order.delivery_slot_date.isoformat() if order.delivery_slot_date else None,
        "delivery_slot_time": order.delivery_slot_time,
        "coupon_code": order.coupon_code,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
    }
    
    # Delivery address
    if order.delivery_address:
        data["delivery_address"] = {
            "address_id": str(order.delivery_address.address_id),
            "address_line1": order.delivery_address.address_line1,
            "address_line2": order.delivery_address.address_line2,
            "city": order.delivery_address.city,
            "state": order.delivery_address.state,
            "postal_code": order.delivery_address.postal_code,
            "country": order.delivery_address.country,
        }
    else:
        data["delivery_address"] = None
    
    # Items
    if include_items and order.items:
        data["items"] = [
            {
                "order_item_id": str(item.order_item_id),
                "product_id": str(item.product_id),
                "variant_id": str(item.variant_id) if item.variant_id else None,
                "product_name": item.product_name,
                "product_sku": item.product_sku,
                "product_image": item.product_image,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.subtotal),
                "tax_amount": float(item.tax_amount) if item.tax_amount else 0,
            }
            for item in order.items
        ]
        data["item_count"] = sum(item.quantity for item in order.items)
    else:
        data["items"] = []
        data["item_count"] = 0
    
    return data


def format_order_summary(order) -> dict:
    """Format order summary for list views."""
    return {
        "order_id": str(order.order_id),
        "order_number": order.order_number,
        "status": order.status,
        "payment_status": order.payment_status,
        "total_amount": float(order.total_amount),
        "item_count": sum(item.quantity for item in order.items) if order.items else 0,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


# ============================================================================
# User Endpoints
# ============================================================================

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new order from cart.
    """
    try:
        order = await OrderService.create_from_cart(
            db,
            user_id=current_user.user_id,
            data=data
        )
        
        # Reload with relationships
        order = await OrderService.get_by_id(db, order.order_id)
        
        return {
            "success": True,
            "data": format_order(order),
            "message": "Order placed successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


@router.get("", response_model=dict)
async def get_my_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get current user's orders.
    """
    try:
        offset = (page - 1) * limit
        orders, total = await OrderService.get_user_orders(
            db,
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
            status=status
        )
        
        return {
            "success": True,
            "data": {
                "orders": [format_order_summary(o) for o in orders],
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": (total + limit - 1) // limit
                }
            }
        }
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orders"
        )


@router.get("/{order_id}", response_model=dict)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get order details.
    """
    try:
        # Try by ID first, then by order number
        try:
            order_uuid = UUID(order_id)
            order = await OrderService.get_by_id(db, order_uuid, current_user.user_id)
        except ValueError:
            order = await OrderService.get_by_order_number(db, order_id, current_user.user_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return {
            "success": True,
            "data": format_order(order)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch order"
        )


@router.post("/{order_id}/cancel", response_model=dict)
async def cancel_order(
    order_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Cancel an order.
    """
    try:
        order_uuid = UUID(order_id)
        order = await OrderService.get_by_id(db, order_uuid, current_user.user_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = await OrderService.cancel_order(db, order, reason)
        
        return {
            "success": True,
            "data": format_order(order),
            "message": "Order cancelled successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order"
        )


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/admin/all", response_model=dict)
async def get_all_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Get all orders (Admin only).
    """
    try:
        offset = (page - 1) * limit
        orders, total = await OrderService.get_all_orders(
            db,
            limit=limit,
            offset=offset,
            status=status,
            payment_status=payment_status
        )
        
        return {
            "success": True,
            "data": {
                "orders": [format_order(o, include_items=False) for o in orders],
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": (total + limit - 1) // limit
                }
            }
        }
    except Exception as e:
        logger.error(f"Error fetching all orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orders"
        )


@router.put("/admin/{order_id}/status", response_model=dict)
async def update_order_status(
    order_id: str,
    data: UpdateOrderStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Update order status (Admin only).
    """
    try:
        order_uuid = UUID(order_id)
        order = await OrderService.get_by_id(db, order_uuid)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = await OrderService.update_status(db, order, data.status)
        
        return {
            "success": True,
            "data": format_order(order),
            "message": f"Order status updated to {data.status.value}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status"
        )


@router.put("/admin/{order_id}/payment", response_model=dict)
async def update_payment_status(
    order_id: str,
    data: UpdatePaymentStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Update payment status (Admin only).
    """
    try:
        order_uuid = UUID(order_id)
        order = await OrderService.get_by_id(db, order_uuid)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = await OrderService.update_payment_status(
            db, order, data.payment_status, data.payment_id
        )
        
        return {
            "success": True,
            "data": format_order(order),
            "message": f"Payment status updated to {data.payment_status.value}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment status"
        )


@router.get("/admin/stats", response_model=dict)
async def get_order_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Get order statistics (Admin only).
    """
    try:
        stats = await OrderService.get_revenue_stats(db)
        
        # Get counts by status
        pending_count = await OrderService.get_order_count(db, status="pending")
        processing_count = await OrderService.get_order_count(db, status="processing")
        shipped_count = await OrderService.get_order_count(db, status="shipped")
        delivered_count = await OrderService.get_order_count(db, status="delivered")
        
        return {
            "success": True,
            "data": {
                "revenue": stats,
                "status_counts": {
                    "pending": pending_count,
                    "processing": processing_count,
                    "shipped": shipped_count,
                    "delivered": delivered_count
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting order stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order statistics"
        )
