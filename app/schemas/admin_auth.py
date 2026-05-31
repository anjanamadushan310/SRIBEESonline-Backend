"""
Admin Auth Schemas
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AdminRole(str, Enum):
    """Admin role types."""
    SUPER_ADMIN = "super_admin"
    BRANCH_MANAGER = "branch_manager"
    MARKETING_MANAGER = "marketing_manager"
    INVENTORY_MANAGER = "inventory_manager"
    CUSTOMER_SUPPORT = "customer_support"


# Request Schemas
class AdminLoginRequest(BaseModel):
    """Admin login request."""
    email: EmailStr
    password: str


class CreateAdminRequest(BaseModel):
    """Create admin user request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: AdminRole
    branch_id: Optional[UUID] = None


# Response Schemas
class AdminResponse(BaseModel):
    """Admin user response."""
    admin_id: UUID = Field(..., alias="adminId")
    email: EmailStr
    full_name: str = Field(..., alias="fullName")
    role: AdminRole
    branch_id: Optional[UUID] = Field(None, alias="branchId")
    is_active: bool = Field(..., alias="isActive")
    last_login: Optional[datetime] = Field(None, alias="lastLogin")
    created_at: datetime = Field(..., alias="createdAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class AdminTokensResponse(BaseModel):
    """Admin JWT tokens response."""
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")

    class Config:
        populate_by_name = True


class AdminAuthData(BaseModel):
    admin: AdminResponse
    token: str

class AdminAuthResponse(BaseModel):
    """Admin authentication response."""
    success: bool = True
    message: str
    data: AdminAuthData


class AdminProfileResponse(BaseModel):
    """Admin profile response."""
    success: bool = True
    admin: AdminResponse


class AdminListResponse(BaseModel):
    """List of admins response."""
    success: bool = True
    admins: list[AdminResponse]
    total: int


class BranchResponse(BaseModel):
    """Branch info response."""
    branch_id: UUID = Field(..., alias="branchId")
    name: str
    address: Optional[str] = None
    is_active: bool = Field(..., alias="isActive")

    class Config:
        from_attributes = True
        populate_by_name = True


class BranchListResponse(BaseModel):
    """List of branches response."""
    success: bool = True
    branches: list[BranchResponse]
