"""
Coupon Service — authoritative coupon validation & redemption.

All discount values come from the ``coupons`` table; client-supplied discounts
are never trusted. Used by the cart apply-coupon endpoint (validate only) and
by order creation (validate + atomically increment ``used_count``).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon import Coupon


class CouponValidationError(ValueError):
    """Raised when a coupon is invalid or cannot be applied.

    Subclasses ``ValueError`` so existing endpoint handlers map it to a
    400 with the (user-friendly) message.
    """


def _as_aware_utc(dt: datetime) -> datetime:
    """Coerce a possibly-naive datetime to timezone-aware UTC for comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class CouponService:
    """Business logic for validating and redeeming coupons."""

    @staticmethod
    async def get_by_code(db: AsyncSession, code: str) -> Optional[Coupon]:
        """Look up a coupon by code (case-insensitive)."""
        result = await db.execute(
            select(Coupon).where(func.lower(Coupon.code) == code.strip().lower())
        )
        return result.scalar_one_or_none()

    @staticmethod
    def validate(coupon: Coupon, subtotal: Decimal, now: Optional[datetime] = None) -> None:
        """
        Enforce all coupon rules. Raises :class:`CouponValidationError` with a
        user-friendly message on the first failure.
        """
        now = now or datetime.now(timezone.utc)
        now = _as_aware_utc(now)

        if not coupon.is_active:
            raise CouponValidationError("This coupon is no longer active.")

        if coupon.valid_from and now < _as_aware_utc(coupon.valid_from):
            raise CouponValidationError("This coupon is not valid yet.")

        if coupon.valid_until and now > _as_aware_utc(coupon.valid_until):
            raise CouponValidationError("This coupon has expired.")

        if (
            coupon.usage_limit is not None
            and (coupon.used_count or 0) >= coupon.usage_limit
        ):
            raise CouponValidationError("This coupon has reached its usage limit.")

        min_order = Decimal(str(coupon.min_order_value or 0))
        if min_order > 0 and subtotal < min_order:
            raise CouponValidationError(
                f"This coupon requires a minimum order of Rs {min_order:.2f}."
            )

    @staticmethod
    async def atomic_increment_usage(db: AsyncSession, coupon_id: UUID) -> bool:
        """
        Atomically bump ``used_count`` iff the coupon is not already maxed out.

        The ``used_count < usage_limit`` guard lives in the WHERE clause, so
        Postgres re-checks it under a row lock — concurrent redemptions of the
        last slot cannot both succeed. Returns True if incremented, False if the
        coupon was already at its limit. Does NOT commit (caller owns the txn).
        """
        stmt = (
            update(Coupon)
            .where(Coupon.coupon_id == coupon_id)
            .where(
                or_(
                    Coupon.usage_limit.is_(None),
                    Coupon.used_count < Coupon.usage_limit,
                )
            )
            .values(used_count=Coupon.used_count + 1)
        )
        result = await db.execute(stmt)
        return (result.rowcount or 0) == 1

    @staticmethod
    async def atomic_decrement_usage(db: AsyncSession, coupon_id: UUID) -> bool:
        """
        Atomically release a redemption slot: ``used_count = used_count - 1``,
        guarded by ``used_count > 0`` so it can never go negative. Used when a
        redeeming order is cancelled. Returns True if a slot was released.
        Does NOT commit (caller owns the txn).
        """
        stmt = (
            update(Coupon)
            .where(Coupon.coupon_id == coupon_id)
            .where(Coupon.used_count > 0)
            .values(used_count=Coupon.used_count - 1)
        )
        result = await db.execute(stmt)
        return (result.rowcount or 0) == 1
