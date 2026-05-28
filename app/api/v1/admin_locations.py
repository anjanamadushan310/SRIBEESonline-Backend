"""
SRIBEESonline - Admin Location Management API Endpoints

Super-Admin-only CRUD for Post Office → Branch mappings:
  GET    /                      — list all mappings (with optional filters)
  GET    /mapping/{mapping_id}  — get single mapping
  POST   /mapping               — create a new mapping
  PUT    /mapping/{mapping_id}  — update an existing mapping
  DELETE /mapping/{mapping_id}  — delete a mapping
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import require_roles
from app.schemas.branch import (
    AdminMappingCreateRequest,
    AdminMappingUpdateRequest,
)
from app.services import branch_service

router = APIRouter()

# Only super_admin can manage location mappings
RequireLocationAdmin = Depends(require_roles("super_admin"))


# ============================================================================
# GET / — list all mappings (filterable)
# ============================================================================

@router.get(
    "",
    response_model=dict,
    summary="List all Post Office → Branch mappings",
    description=(
        "Returns every mapping in the system, optionally filtered by "
        "province and/or district.  Super Admin only."
    ),
)
async def list_mappings(
    province: Optional[str] = Query(None, description="Filter by province"),
    district: Optional[str] = Query(None, description="Filter by district"),
    active_only: bool = Query(False, description="Only return active mappings"),
    db: AsyncSession = Depends(get_db),
    admin=RequireLocationAdmin,
):
    mappings = await branch_service.list_all_mappings(
        db,
        province=province,
        district=district,
        active_only=active_only,
    )

    return {
        "success": True,
        "data": [m.to_dict() for m in mappings],
        "total": len(mappings),
    }


# ============================================================================
# GET /mapping/{mapping_id} — get single mapping
# ============================================================================

@router.get(
    "/mapping/{mapping_id}",
    response_model=dict,
    summary="Get a single mapping by ID",
)
async def get_mapping(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=RequireLocationAdmin,
):
    from app.core.exceptions import NotFoundError

    mapping = await branch_service.get_mapping_by_id(db, mapping_id)
    if mapping is None:
        raise NotFoundError(resource="Mapping", identifier=str(mapping_id))

    return {
        "success": True,
        "data": mapping.to_dict(),
    }


# ============================================================================
# POST /mapping — create new mapping
# ============================================================================

@router.post(
    "/mapping",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Post Office → Branch mapping",
    description=(
        "Defines which branch serves a given Post Office.  Province and "
        "district are mandatory so that the cascading dropdown hierarchy is "
        "complete.  Super Admin only."
    ),
)
async def create_mapping(
    body: AdminMappingCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin=RequireLocationAdmin,
):
    mapping = await branch_service.create_mapping(
        db,
        post_office=body.post_office,
        branch_id=body.branch_id,
        branch_name=body.branch_name,
        district=body.district,
        province=body.province,
        is_active=body.is_active,
    )

    return {
        "success": True,
        "data": mapping.to_dict(),
        "message": f"Mapping created: {mapping.post_office} → {mapping.branch_name}",
    }


# ============================================================================
# PUT /mapping/{mapping_id} — update mapping
# ============================================================================

@router.put(
    "/mapping/{mapping_id}",
    response_model=dict,
    summary="Update an existing mapping",
    description="Partially update any field on the mapping.  Super Admin only.",
)
async def update_mapping(
    mapping_id: UUID,
    body: AdminMappingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin=RequireLocationAdmin,
):
    update_data = body.model_dump(exclude_unset=True)

    mapping = await branch_service.update_mapping(
        db,
        mapping_id,
        **update_data,
    )

    return {
        "success": True,
        "data": mapping.to_dict(),
        "message": "Mapping updated successfully",
    }


# ============================================================================
# DELETE /mapping/{mapping_id} — delete mapping
# ============================================================================

@router.delete(
    "/mapping/{mapping_id}",
    response_model=dict,
    summary="Delete a mapping",
    description="Permanently removes a Post Office → Branch mapping.  Super Admin only.",
)
async def delete_mapping(
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin=RequireLocationAdmin,
):
    await branch_service.delete_mapping(db, mapping_id)

    return {
        "success": True,
        "message": "Mapping deleted successfully",
    }
