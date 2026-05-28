"""
Admin Auth API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.schemas.admin_auth import (
    AdminLoginRequest,
    AdminAuthResponse,
    AdminProfileResponse,
    AdminListResponse,
    CreateAdminRequest,
    AdminResponse,
    BranchListResponse,
)
from app.schemas.auth import MessageResponse
from app.services.admin_auth_service import AdminAuthService
from app.core.dependencies import get_current_admin, require_super_admin

router = APIRouter()


@router.post(
    "/login",
    response_model=AdminAuthResponse,
    summary="Admin login",
    description="Authenticate admin user and return JWT tokens.",
)
async def admin_login(
    data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminAuthResponse:
    """
    Authenticate admin with email and password.
    """
    try:
        return await AdminAuthService.login(data.email, data.password, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get(
    "/profile",
    response_model=AdminProfileResponse,
    summary="Get admin profile",
    description="Get current admin's profile.",
)
async def get_admin_profile(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminProfileResponse:
    """
    Get current admin's profile.
    """
    try:
        return await AdminAuthService.get_profile(current_admin.admin_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/users",
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create admin user",
    description="Create a new admin user (Super Admin only).",
)
async def create_admin(
    data: CreateAdminRequest,
    current_admin = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminResponse:
    """
    Create a new admin user.
    
    Only Super Admins can create new admin users.
    """
    try:
        return await AdminAuthService.create_admin(data, current_admin.admin_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/users",
    response_model=AdminListResponse,
    summary="List admin users",
    description="List all admin users (Super Admin only).",
)
async def list_admins(
    current_admin = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminListResponse:
    """
    List all admin users.
    
    Only Super Admins can list admin users.
    """
    return await AdminAuthService.list_admins(db)


@router.get(
    "/branches",
    response_model=BranchListResponse,
    summary="List branches",
    description="List all branches.",
)
async def list_branches(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> BranchListResponse:
    """
    List all branches.
    
    Returns empty list if no branches configured.
    """
    # TODO: Implement branch model if needed
    return BranchListResponse(success=True, branches=[])


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Admin logout",
    description="Logout admin user.",
)
async def admin_logout(
    current_admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Logout current admin.
    """
    result = await AdminAuthService.logout(current_admin.admin_id, db)
    return MessageResponse(**result)
