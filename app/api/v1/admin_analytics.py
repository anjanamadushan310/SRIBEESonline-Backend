"""
Admin Analytics API (Module 7.1)

Branch-scoped dashboard metrics. Restricted to super_admin and branch_manager
(enforced at the router level). Branch isolation via ``inject_branch_filter``:
a Branch Manager only sees their branch's revenue/orders/stock; a Super Admin
sees global figures unless they pass ``?branch_id=``.

Prefix "/admin/analytics" is applied by app/api/v1/router.py.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import BranchScope, inject_branch_filter, require_roles
from app.models.order import Order, PaymentStatus
from app.models.product import BranchInventory

router = APIRouter(
    dependencies=[Depends(require_roles("super_admin", "branch_manager"))],
    tags=["Admin Analytics"],
)

_PAID = PaymentStatus.PAID.value


@router.get("/summary", response_model=dict)
async def analytics_summary(
    branch_id: Optional[UUID] = Query(
        None, description="Super Admin only: scope to a branch (ignored for Branch Managers)"
    ),
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(inject_branch_filter),
):
    """
    Top-level KPIs: total revenue (paid orders), total orders, active customers
    (distinct customers who ordered in the last 30 days) and low-stock alerts.
    """
    effective_branch = scope.resolve(branch_id)
    since_30d = datetime.utcnow() - timedelta(days=30)

    def scope_orders(stmt):
        return stmt.where(Order.branch_id == effective_branch) if effective_branch else stmt

    # Total revenue — paid orders only.
    revenue_q = scope_orders(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.payment_status == _PAID
        )
    )
    total_revenue = float((await db.execute(revenue_q)).scalar() or 0)

    # Total orders — all statuses.
    total_orders = int(
        (await db.execute(scope_orders(select(func.count(Order.order_id))))).scalar() or 0
    )

    # Active customers — distinct buyers in the last 30 days.
    active_q = scope_orders(
        select(func.count(distinct(Order.user_id))).where(Order.created_at >= since_30d)
    )
    active_customers = int((await db.execute(active_q)).scalar() or 0)

    # Low-stock alerts — branch_inventory rows at/below threshold.
    low_stock_q = select(func.count(BranchInventory.inventory_id)).where(
        BranchInventory.stock_quantity <= BranchInventory.low_stock_threshold
    )
    if effective_branch:
        low_stock_q = low_stock_q.where(BranchInventory.branch_id == effective_branch)
    low_stock_alerts = int((await db.execute(low_stock_q)).scalar() or 0)

    return {
        "success": True,
        "data": {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "active_customers": active_customers,
            "low_stock_alerts": low_stock_alerts,
            "scope": {
                "is_super_admin": scope.is_super_admin,
                "branch_id": str(effective_branch) if effective_branch else None,
            },
        },
    }


@router.get("/sales", response_model=dict)
async def analytics_sales(
    days: int = Query(30, ge=1, le=365, description="Window size in days"),
    branch_id: Optional[UUID] = Query(
        None, description="Super Admin only: scope to a branch (ignored for Branch Managers)"
    ),
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(inject_branch_filter),
):
    """
    Daily time-series for the last ``days`` days: revenue (paid orders) and
    order counts. Missing days are zero-filled so the series is continuous.
    """
    effective_branch = scope.resolve(branch_id)
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, datetime.min.time())

    order_date = func.date(Order.created_at).label("day")
    query = (
        select(
            order_date,
            func.count(Order.order_id).label("orders"),
            func.coalesce(
                func.sum(
                    case((Order.payment_status == _PAID, Order.total_amount), else_=0)
                ),
                0,
            ).label("revenue"),
        )
        .where(Order.created_at >= start_dt)
        .group_by(order_date)
        .order_by(order_date)
    )
    if effective_branch:
        query = query.where(Order.branch_id == effective_branch)

    rows = (await db.execute(query)).all()

    # Index results by ISO date string (func.date may yield date or str).
    by_day: dict[str, dict] = {}
    for day, orders, revenue in rows:
        key = day.isoformat() if hasattr(day, "isoformat") else str(day)
        by_day[key] = {"orders": int(orders or 0), "revenue": float(revenue or 0)}

    series = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).isoformat()
        entry = by_day.get(d, {"orders": 0, "revenue": 0.0})
        series.append({"date": d, "orders": entry["orders"], "revenue": entry["revenue"]})

    return {
        "success": True,
        "data": {
            "series": series,
            "days": days,
            "scope": {
                "is_super_admin": scope.is_super_admin,
                "branch_id": str(effective_branch) if effective_branch else None,
            },
        },
    }
