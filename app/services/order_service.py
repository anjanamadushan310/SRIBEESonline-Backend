"""
Order Service - Business Logic
"""
from typing import Optional, List, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime
import random
import string
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.user import Address
from app.services.cart_service import CartService
from app.schemas.order import CreateOrderRequest, OrderStatusEnum, PaymentStatusEnum


class OrderService:
    """Service class for order operations."""
    
    @staticmethod
    def generate_order_number() -> str:
        """Generate unique order number."""
        timestamp = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"FC-{timestamp}-{random_part}"
    
    @staticmethod
    async def create_from_cart(
        db: AsyncSession,
        user_id: UUID,
        data: CreateOrderRequest
    ) -> Order:
        """Create order from user's cart."""
        # Get cart
        cart = await CartService.get_cart(str(user_id))
        
        if not cart["items"]:
            raise ValueError("Cart is empty")
        
        # Verify address exists
        address_result = await db.execute(
            select(Address).where(
                and_(
                    Address.address_id == UUID(data.delivery_address_id),
                    Address.user_id == user_id
                )
            )
        )
        address = address_result.scalar_one_or_none()
        
        if not address:
            raise ValueError("Invalid delivery address")
        
        # Calculate totals
        totals = cart["totals"]
        
        # Create order
        order = Order(
            user_id=user_id,
            order_number=OrderService.generate_order_number(),
            subtotal=Decimal(str(totals["subtotal"])),
            tax_amount=Decimal(str(totals["tax"])),
            shipping_amount=Decimal(str(totals["shipping"])),
            discount_amount=Decimal(str(totals["discount"])),
            total_amount=Decimal(str(totals["total"])),
            delivery_address_id=UUID(data.delivery_address_id),
            delivery_slot_date=data.delivery_slot_date,
            delivery_slot_time=data.delivery_slot_time,
            payment_method=data.payment_method,
            coupon_code=cart.get("coupon", {}).get("code") if cart.get("coupon") else data.coupon_code,
            notes=data.notes,
            status=OrderStatus.PENDING.value,
            payment_status=PaymentStatus.PENDING.value
        )
        
        db.add(order)
        await db.flush()  # Get order_id
        
        # Create order items
        for item in cart["items"]:
            order_item = OrderItem(
                order_id=order.order_id,
                product_id=UUID(item["product_id"]),
                variant_id=UUID(item["variant_id"]) if item.get("variant_id") else None,
                product_name=item["name"],
                product_sku=item.get("sku"),
                product_image=item.get("image"),
                quantity=item["quantity"],
                unit_price=Decimal(str(item["price"])),
                subtotal=Decimal(str(item["price"] * item["quantity"]))
            )
            db.add(order_item)
        
        await db.commit()
        await db.refresh(order)
        
        # Clear cart after successful order
        await CartService.clear_cart(str(user_id))
        
        logger.info(f"Order created: {order.order_number} for user {user_id}")
        
        return order
    
    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        order_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[Order]:
        """Get order by ID."""
        query = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.delivery_address)
            )
            .where(Order.order_id == order_id)
        )
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_order_number(
        db: AsyncSession,
        order_number: str,
        user_id: Optional[UUID] = None
    ) -> Optional[Order]:
        """Get order by order number."""
        query = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.delivery_address)
            )
            .where(Order.order_number == order_number)
        )
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_orders(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Tuple[List[Order], int]:
        """Get user's orders."""
        query = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
        )
        
        if status:
            query = query.where(Order.status == status)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get orders
        query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        orders = result.scalars().all()
        
        return orders, total
    
    @staticmethod
    async def get_all_orders(
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
        payment_status: Optional[str] = None
    ) -> Tuple[List[Order], int]:
        """Get all orders (admin)."""
        query = select(Order).options(
            selectinload(Order.items),
            selectinload(Order.user)
        )
        
        if status:
            query = query.where(Order.status == status)
        
        if payment_status:
            query = query.where(Order.payment_status == payment_status)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get orders
        query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        orders = result.scalars().all()
        
        return orders, total
    
    @staticmethod
    async def update_status(
        db: AsyncSession,
        order: Order,
        status: OrderStatusEnum
    ) -> Order:
        """Update order status."""
        order.status = status.value
        
        # Set timestamps based on status
        now = datetime.utcnow()
        if status == OrderStatusEnum.SHIPPED:
            order.shipped_at = now
        elif status == OrderStatusEnum.DELIVERED:
            order.delivered_at = now
        elif status == OrderStatusEnum.CANCELLED:
            order.cancelled_at = now
        
        await db.commit()
        await db.refresh(order)
        
        logger.info(f"Order {order.order_number} status updated to {status.value}")
        
        return order
    
    @staticmethod
    async def update_payment_status(
        db: AsyncSession,
        order: Order,
        payment_status: PaymentStatusEnum,
        payment_id: Optional[str] = None
    ) -> Order:
        """Update payment status."""
        order.payment_status = payment_status.value
        
        if payment_id:
            order.payment_id = payment_id
        
        # If payment successful, confirm order
        if payment_status == PaymentStatusEnum.PAID and order.status == OrderStatus.PENDING.value:
            order.status = OrderStatus.CONFIRMED.value
        
        await db.commit()
        await db.refresh(order)
        
        logger.info(f"Order {order.order_number} payment status updated to {payment_status.value}")
        
        return order
    
    @staticmethod
    async def cancel_order(
        db: AsyncSession,
        order: Order,
        reason: Optional[str] = None
    ) -> Order:
        """Cancel an order."""
        # Check if order can be cancelled
        non_cancellable = [
            OrderStatus.SHIPPED.value,
            OrderStatus.OUT_FOR_DELIVERY.value,
            OrderStatus.DELIVERED.value,
            OrderStatus.CANCELLED.value
        ]
        
        if order.status in non_cancellable:
            raise ValueError(f"Order cannot be cancelled in {order.status} status")
        
        order.status = OrderStatus.CANCELLED.value
        order.cancelled_at = datetime.utcnow()
        
        if reason:
            order.notes = f"{order.notes or ''}\nCancellation reason: {reason}".strip()
        
        # TODO: Handle refund if payment was made
        
        await db.commit()
        await db.refresh(order)
        
        logger.info(f"Order {order.order_number} cancelled")
        
        return order
    
    @staticmethod
    async def get_order_count(
        db: AsyncSession,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None
    ) -> int:
        """Get order count."""
        query = select(func.count(Order.order_id))
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        if status:
            query = query.where(Order.status == status)
        
        result = await db.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    async def get_revenue_stats(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get revenue statistics (admin)."""
        query = select(
            func.count(Order.order_id).label("total_orders"),
            func.sum(Order.total_amount).label("total_revenue"),
            func.avg(Order.total_amount).label("average_order_value")
        ).where(Order.payment_status == PaymentStatus.PAID.value)
        
        if start_date:
            query = query.where(Order.created_at >= start_date)
        
        if end_date:
            query = query.where(Order.created_at <= end_date)
        
        result = await db.execute(query)
        row = result.one()
        
        return {
            "total_orders": row.total_orders or 0,
            "total_revenue": float(row.total_revenue or 0),
            "average_order_value": float(row.average_order_value or 0)
        }
