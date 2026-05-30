"""
SRIBEESonline - Branch Inventory Management API

Endpoints for Inventory Managers (and Marketing Managers) to view and
manage the branch-specific product catalog.

  GET  /my-branch                     — list all global products with branch overrides
  PUT  /update-stock/{product_id}     — update stock_quantity and is_active
  PUT  /update-pricing/{product_id}   — set branch_price and branch_discount

All endpoints are branch-scoped: the manager can only operate on the
branch assigned to their admin account.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import require_roles
from app.schemas.product import (
    PricingUpdateRequest,
    StockUpdateRequest,
)
from app.services.product_service import ProductService

router = APIRouter()

RequireInventoryManager = Depends(
    require_roles(
        "super_admin",
        "branch_manager",
        "marketing_manager",
        "inventory_manager",
    )
)


# ============================================================================
# Helpers
# ============================================================================

def _extract_branch_id(admin):
    """
    Extract and validate the branch_id from the authenticated admin.

    Raises 400 if the admin has no assigned branch.
    """
    from app.models.admin import AdminRole

    branch_id = admin.branch_id
    is_super = admin.role in (
        AdminRole.SUPER_ADMIN.value, "super_admin", AdminRole.SUPER_ADMIN,
    )

    if branch_id is None and not is_super:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "message": "Your admin account is not assigned to a branch",
                    "code": "NO_BRANCH_ASSIGNED",
                },
            },
        )

    if branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "message": (
                        "Super Admins must be assigned to a branch or specify "
                        "one via a query parameter to use inventory management."
                    ),
                    "code": "NO_BRANCH_ASSIGNED",
                },
            },
        )

    return branch_id


def _format_inventory_item(entry: dict) -> dict:
    """Format a product + effective-data pair for the inventory list."""
    p = entry["product"]
    eff = entry["effective"]
    return {
        "productId": str(p.product_id),
        "inventoryId": str(eff["inventory_id"]) if eff.get("inventory_id") else None,
        "name": p.name,
        "slug": p.slug,
        "sku": p.sku,
        "globalPrice": eff["global_price"],
        "branchPrice": eff["branch_price"],
        "effectivePrice": eff["effective_price"],
        "globalDiscount": eff["global_discount"],
        "branchDiscount": eff["branch_discount"],
        "effectiveDiscount": eff["effective_discount"],
        "effectiveDiscountPrice": eff["effective_discount_price"],
        "stockQuantity": eff["stock_quantity"],
        "isOnSale": eff["is_on_sale"],
        "isActive": eff["is_active"],
        "hasOverride": eff.get("inventory_id") is not None,
        "category": (
            {"categoryId": str(p.category.category_id), "name": p.category.name}
            if p.category else None
        ),
        "images": [
            {"imageUrl": img.image_url, "isPrimary": img.is_primary}
            for img in (p.images or [])[:1]
        ],
    }


# ============================================================================
# GET /my-branch — list all products with branch overrides
# ============================================================================

@router.get(
    "/my-branch",
    response_model=dict,
    summary="List all global products with branch-specific overrides",
    description=(
        "Returns every active global product together with the branch-specific "
        "overrides (price, stock, discount, active status) for the manager's "
        "assigned branch. Products without an override row show global defaults."
    ),
)
async def list_my_branch_inventory(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin=RequireInventoryManager,
):
    branch_id = _extract_branch_id(admin)
    offset = (page - 1) * limit

    items, total = await ProductService.list_branch_inventory(
        db, branch_id, limit=limit, offset=offset,
    )

    return {
        "success": True,
        "data": {
            "products": [_format_inventory_item(item) for item in items],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit if limit else 1,
            },
            "branchId": str(branch_id),
        },
    }


# ============================================================================
# PUT /update-stock/{product_id}
# ============================================================================

@router.put(
    "/update-stock/{product_id}",
    response_model=dict,
    summary="Update branch stock and active status",
    description=(
        "Allows an Inventory Manager to update the ``stock_quantity`` and "
        "``is_active`` flag for a product in their branch. Creates a "
        "``branch_inventory`` row if one doesn't exist yet (upsert)."
    ),
)
async def update_stock(
    product_id: UUID,
    body: StockUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=RequireInventoryManager,
):
    branch_id = _extract_branch_id(admin)

    fields = {"stock_quantity": body.stock_quantity}
    if body.is_active is not None:
        fields["is_active"] = body.is_active

    inv = await ProductService.update_branch_inventory(
        db, product_id=product_id, branch_id=branch_id, **fields,
    )

    product = await ProductService.get_by_id(db, product_id, include_inactive=True)
    eff = ProductService.compute_effective_data(product, inv)

    logger.info(
        f"Inventory stock updated: product={product_id} branch={branch_id} "
        f"stock={body.stock_quantity} is_active={body.is_active}"
    )

    return {
        "success": True,
        "data": {
            "inventoryId": str(inv.inventory_id),
            "productId": str(product_id),
            "branchId": str(branch_id),
            "productName": product.name,
            **eff,
        },
        "message": "Stock updated successfully",
    }


# ============================================================================
# PUT /update-pricing/{product_id}
# ============================================================================

@router.put(
    "/update-pricing/{product_id}",
    response_model=dict,
    summary="Set branch-specific pricing overrides",
    description=(
        "Allows an Inventory Manager to set ``branch_price`` and "
        "``discount_percentage`` for a product in their branch. "
        "Setting a field to ``null`` clears the override and falls "
        "back to the global value."
    ),
)
async def update_pricing(
    product_id: UUID,
    body: PricingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=RequireInventoryManager,
):
    branch_id = _extract_branch_id(admin)

    fields = body.model_dump(exclude_unset=True)

    inv = await ProductService.update_branch_inventory(
        db, product_id=product_id, branch_id=branch_id, **fields,
    )

    product = await ProductService.get_by_id(db, product_id, include_inactive=True)
    eff = ProductService.compute_effective_data(product, inv)

    logger.info(
        f"Inventory pricing updated: product={product_id} branch={branch_id} "
        f"fields={list(fields.keys())}"
    )

    return {
        "success": True,
        "data": {
            "inventoryId": str(inv.inventory_id),
            "productId": str(product_id),
            "branchId": str(branch_id),
            "productName": product.name,
            **eff,
        },
        "message": "Branch pricing updated successfully",
    }
