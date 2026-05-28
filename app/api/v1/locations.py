"""
SRIBEESonline - Location Discovery API Endpoints

Public / customer-facing endpoints for cascading address selection:
  GET /provinces           — all provinces with coverage metadata
  GET /districts           — districts within a province
  GET /post-offices        — post offices within a district
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_user_optional
from app.services import branch_service

router = APIRouter()


# ============================================================================
# GET /provinces
# ============================================================================

@router.get(
    "/provinces",
    response_model=dict,
    summary="List all served provinces",
    description=(
        "Returns every province that has at least one active branch mapping, "
        "along with AI-friendly coverage metadata (district count, post-office "
        "count, branch count, and a plain-English coverage summary). "
        "Works for both authenticated and guest users."
    ),
)
async def list_provinces(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    provinces = await branch_service.list_provinces(db)

    return {
        "success": True,
        "data": provinces,
        "total": len(provinces),
    }


# ============================================================================
# GET /districts?province=
# ============================================================================

@router.get(
    "/districts",
    response_model=dict,
    summary="List districts for a province",
    description=(
        "Given a province name, returns the districts within it that have "
        "active branch mappings.  Each district includes the serving branch "
        "names and an AI-readable coverage summary."
    ),
)
async def list_districts(
    province: str = Query(
        ...,
        min_length=1,
        description="Province name (title-case normalised automatically)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    districts = await branch_service.list_districts(db, province)

    return {
        "success": True,
        "data": districts,
        "total": len(districts),
    }


# ============================================================================
# GET /post-offices?district=
# ============================================================================

@router.get(
    "/post-offices",
    response_model=dict,
    summary="List post offices for a district",
    description=(
        "Given a district name, returns every active post office within it "
        "together with the mapped branch ID and name — ready for the final "
        "step of the cascading dropdown."
    ),
)
async def list_post_offices(
    district: str = Query(
        ...,
        min_length=1,
        description="District name (title-case normalised automatically)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    post_offices = await branch_service.list_post_offices_for_district(db, district)

    return {
        "success": True,
        "data": post_offices,
        "total": len(post_offices),
    }
