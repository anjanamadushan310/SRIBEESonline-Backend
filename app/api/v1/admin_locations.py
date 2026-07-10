"""
SRIBEESonline - Admin Location Management API Endpoints

Super-Admin-only CRUD for the **Post Office master directory** ("Delivery
Zones") — the source-of-truth list of every Post Office tagged with its
District and Province. The Branch form reads from here to offer coverage-area
options; assigning coverage on a Branch writes PostOfficeBranchMapping rows
(handled by the branch endpoints, not here).

  GET    /admin/locations           — list directory entries (filterable)
  POST   /admin/locations           — add a Post Office
  PUT    /admin/locations/{id}      — edit a Post Office
  DELETE /admin/locations/{id}      — remove a Post Office

Prefix "/admin/locations" is applied by app/api/v1/router.py.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import require_roles
from app.schemas.branch import (
    PostOfficeDirectoryCreate,
    PostOfficeDirectoryUpdate,
)
from app.services import branch_service

router = APIRouter(
    dependencies=[Depends(require_roles("super_admin"))],
    tags=["Admin Location Management"],
)


# ============================================================================
# GET / — list directory entries (filterable)
# ============================================================================

@router.get(
    "",
    response_model=dict,
    summary="List master Post Office directory entries",
    description=(
        "Returns every Post Office in the master directory, optionally filtered "
        "by province and/or district. Powers the Branch form's coverage-area "
        "picker and the Delivery Zones settings tab. Super Admin only."
    ),
)
async def list_locations(
    province: Optional[str] = Query(None, description="Filter by province"),
    district: Optional[str] = Query(None, description="Filter by district"),
    active_only: bool = Query(False, description="Only return active post offices"),
    db: AsyncSession = Depends(get_db),
):
    entries = await branch_service.list_directory(
        db,
        province=province,
        district=district,
        active_only=active_only,
    )
    return {
        "success": True,
        "data": {"post_offices": [e.to_dict() for e in entries]},
        "total": len(entries),
    }


# ============================================================================
# POST / — create directory entry
# ============================================================================

@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Add a Post Office to the master directory",
    description=(
        "Post office names are unique across Sri Lanka. Province and district "
        "are mandatory so the cascading dropdowns stay complete. Super Admin only."
    ),
)
async def create_location(
    body: PostOfficeDirectoryCreate,
    db: AsyncSession = Depends(get_db),
):
    entry = await branch_service.create_directory_entry(
        db,
        post_office=body.post_office,
        district=body.district,
        province=body.province,
        is_active=body.is_active,
    )
    return {
        "success": True,
        "data": entry.to_dict(),
        "message": f"Post Office '{entry.post_office}' added",
    }


# ============================================================================
# PUT /{location_id} — update directory entry
# ============================================================================

@router.put(
    "/{location_id}",
    response_model=dict,
    summary="Edit a Post Office directory entry",
    description="Partially update any field. Super Admin only.",
)
async def update_location(
    location_id: UUID,
    body: PostOfficeDirectoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    entry = await branch_service.update_directory_entry(
        db,
        location_id,
        **body.model_dump(exclude_unset=True),
    )
    return {
        "success": True,
        "data": entry.to_dict(),
        "message": "Post Office updated successfully",
    }


# ============================================================================
# DELETE /{location_id} — delete directory entry
# ============================================================================

@router.delete(
    "/{location_id}",
    response_model=dict,
    summary="Remove a Post Office from the directory",
    description="Permanently deletes the directory entry. Super Admin only.",
)
async def delete_location(
    location_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    await branch_service.delete_directory_entry(db, location_id)
    return {
        "success": True,
        "message": "Post Office removed successfully",
    }
