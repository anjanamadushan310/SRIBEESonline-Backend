"""
Admin Branch Inventory API (Module 7.5)

Branch-scoped stock management over ``branch_inventory`` rows.

RBAC: super_admin, branch_manager, inventory_manager (enforced at router level).
Branch isolation: every route depends on ``inject_branch_filter`` — Branch
Managers and Inventory Managers only ever see/modify their own branch's rows,
while Super Admins see all branches (optionally narrowed by ``?branch_id=``).

Prefix "/admin/inventory" is applied by app/api/v1/router.py.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import BranchScope, inject_branch_filter, require_roles
from app.models.branch import Branch
from app.models.product import BranchInventory, Product
from app.schemas.inventory import InventoryUpdateRequest
from app.services.product_service import ProductService

# Stock management is limited to Super Admins, Branch Managers and Inventory Managers.
router = APIRouter(
    dependencies=[Depends(require_roles("super_admin", "branch_manager", "inventory_manager"))],
    tags=["Admin Inventory"],
)


def _format_inventory_row(inv: BranchInventory, product: Product, branch: Branch) -> dict:
    """Serialize a branch_inventory row joined with its product and branch."""
    stock = inv.stock_quantity or 0
    reserved = inv.reserved_quantity or 0
    threshold = inv.low_stock_threshold or 0
    return {
        "inventory_id": str(inv.inventory_id),
        "product_id": str(product.product_id),
        "product_name": product.name,
        "sku": product.sku,
        "branch_id": str(branch.branch_id),
        "branch_name": branch.name,
        "stock_quantity": stock,
        "reserved_quantity": reserved,
        "available_quantity": stock - reserved,
        "low_stock_threshold": threshold,
        "is_low_stock": stock <= threshold,
        "is_active": inv.is_active,
    }


@router.get("", response_model=dict)
async def list_inventory(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Match product name or SKU"),
    low_stock_only: bool = Query(False, description="Only rows at/below threshold"),
    branch_id: Optional[UUID] = Query(
        None,
        description="Super Admin only: narrow to a single branch (ignored for scoped admins)",
    ),
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(inject_branch_filter),
):
    """
    Paginated branch inventory list.

    Branch isolation is applied via ``scope.resolve()``: scoped admins always
    get their own branch; Super Admins get all branches unless they pass
    ``branch_id``.
    """
    effective_branch = scope.resolve(branch_id)
    offset = (page - 1) * limit

    rows, total = await ProductService.list_inventory(
        db,
        branch_id=effective_branch,
        limit=limit,
        offset=offset,
        search=search,
        low_stock_only=low_stock_only,
    )

    return {
        "success": True,
        "data": {
            "items": [_format_inventory_row(inv, product, branch) for inv, product, branch in rows],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit if limit else 1,
            },
            # Signals to the frontend whether to show the Branch column.
            "scope": {
                "is_super_admin": scope.is_super_admin,
                "branch_id": str(effective_branch) if effective_branch else None,
            },
        },
    }


@router.put("/{inventory_id}", response_model=dict)
async def update_inventory(
    inventory_id: UUID,
    body: InventoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    scope: BranchScope = Depends(inject_branch_filter),
):
    """
    Update stock quantity, reserved quantity and/or low-stock threshold for a
    single inventory row. Scoped admins may only touch rows in their branch.
    """
    found = await ProductService.get_inventory_by_id(db, inventory_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found",
        )

    inv, product, branch = found

    # Branch isolation: a scoped admin cannot modify another branch's stock.
    if not scope.is_super_admin and inv.branch_id != scope.branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify inventory for your own branch.",
        )

    updated = await ProductService.update_inventory_row(
        db,
        inv,
        **body.model_dump(exclude_unset=True),
    )
    logger.info(f"[admin] Inventory {inventory_id} updated in branch {inv.branch_id}")

    return {
        "success": True,
        "data": _format_inventory_row(updated, product, branch),
        "message": "Inventory updated successfully",
    }
