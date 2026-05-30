"""
SRIBEESonline - Marketing Manager API Endpoints

Branch-scoped endpoints for managing product discounts and the Quick Sale feed.
Uses the ``branch_inventory`` table for per-branch overrides; global values on
``products`` act as fallbacks when no override is set.

  PATCH /inventory/{product_id}  — set/clear branch overrides
  GET   /quick-sale              — preview Quick Sale products for manager's branch
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import require_roles
from app.schemas.product import BranchInventoryUpdateRequest
from app.services.product_service import ProductService

router = APIRouter()

RequireMarketingManager = Depends(
    require_roles("super_admin", "branch_manager", "marketing_manager")
)


# ============================================================================
# Helper
# ============================================================================

def _format_quick_sale_item(entry: dict) -> dict:
    """Format a quick-sale row (product + effective data) for the response."""
    p = entry["product"]
    eff = entry["effective"]
    return {
        "productId": str(p.product_id),
        "name": p.name,
        "slug": p.slug,
        "globalPrice": float(p.price) if p.price else 0,
        "effectivePrice": eff["effective_price"],
        "branchPrice": eff["branch_price"],
        "effectiveDiscount": eff["effective_discount"],
        "effectiveDiscountPrice": eff["effective_discount_price"],
        "stockQuantity": eff["stock_quantity"],
        "isOnSale": eff["is_on_sale"],
        "isActive": eff["is_active"],
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
# PATCH /inventory/{product_id}
# ============================================================================

@router.patch(
    "/inventory/{product_id}",
    response_model=dict,
    summary="Update branch-specific inventory overrides",
    description=(
        "Marketing Managers update **branch_price**, **discount_percentage**, "
        "**is_on_sale**, **is_active**, and **stock_quantity** for their "
        "assigned branch.  Setting a field to ``null`` clears the override "
        "and the system falls back to the global value on the product."
    ),
)
async def update_branch_inventory(
    product_id: UUID,
    body: BranchInventoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=RequireMarketingManager,
):
    # Determine which branch to operate on
    from app.models.admin import AdminRole

    is_super = admin.role in (AdminRole.SUPER_ADMIN.value, "super_admin", AdminRole.SUPER_ADMIN)
    branch_id = admin.branch_id

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

    if branch_id is None and is_super:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "message": (
                        "Super Admins must specify a branch_id query parameter "
                        "or be assigned to a branch"
                    ),
                    "code": "NO_BRANCH_ASSIGNED",
                },
            },
        )

    update_data = body.model_dump(exclude_unset=True)
    inv = await ProductService.update_branch_inventory(
        db,
        product_id=product_id,
        branch_id=branch_id,
        **update_data,
    )

    # Load product for effective computation
    product = await ProductService.get_by_id(db, product_id, include_inactive=True)
    eff = ProductService.compute_effective_data(product, inv)

    return {
        "success": True,
        "data": {
            "inventoryId": str(inv.inventory_id),
            "productId": str(product_id),
            "branchId": str(branch_id),
            "productName": product.name,
            **eff,
        },
        "message": "Branch inventory updated — overrides applied",
    }


# ============================================================================
# GET /quick-sale
# ============================================================================

@router.get(
    "/quick-sale",
    response_model=dict,
    summary="Preview Quick Sale products for your branch",
    description=(
        "Returns the Quick Sale product feed for the manager's branch, "
        "sorted by highest effective discount first.  Uses COALESCE "
        "fallback (branch override → global default)."
    ),
)
async def preview_quick_sale(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin=RequireMarketingManager,
):
    branch_id = admin.branch_id
    if branch_id is None:
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

    items = await ProductService.get_quick_sale_products(db, branch_id, limit)

    return {
        "success": True,
        "data": {
            "products": [_format_quick_sale_item(item) for item in items],
            "total": len(items),
            "branchId": str(branch_id),
        },
    }
