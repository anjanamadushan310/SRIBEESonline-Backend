"""
SRIBEESonline FastAPI Backend - Schemas Module

Pydantic schemas for request/response validation.
"""
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokensResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.schemas.branch import (
    # Admin mapping management
    AdminMappingCreateRequest,
    AdminMappingUpdateRequest,
    BranchContextClearedResponse,
    BranchContextResponse,
    BranchCreate,
    BranchResolveRequest,
    BranchResolveResponse,
    BranchResponse,
    BranchUpdate,
    DistrictItem,
    DistrictListResponse,
    # Triplet-based resolution
    LocationResolveRequest,
    LocationResolveResponse,
    PostOfficeBranchMappingCreate,
    PostOfficeBranchMappingListResponse,
    PostOfficeBranchMappingResponse,
    PostOfficeBranchMappingUpdate,
    PostOfficeItem,
    PostOfficeListResponse,
    # Location discovery
    ProvinceItem,
    ProvinceListResponse,
    ServedPostOfficesResponse,
)

__all__ = [
    # Auth requests
    "RegisterRequest",
    "LoginRequest",
    "VerifyEmailRequest",
    "ResendVerificationRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "RefreshTokenRequest",
    # Auth responses
    "UserResponse",
    "TokensResponse",
    "AuthResponse",
    "RegisterResponse",
    "MessageResponse",
    "RefreshTokenResponse",
    # Branch schemas
    "BranchCreate",
    "BranchUpdate",
    "BranchResponse",
    # Post Office mapping schemas
    "PostOfficeBranchMappingCreate",
    "PostOfficeBranchMappingUpdate",
    "PostOfficeBranchMappingResponse",
    "PostOfficeBranchMappingListResponse",
    # Branch resolution schemas
    "BranchResolveRequest",
    "BranchResolveResponse",
    "BranchContextResponse",
    "BranchContextClearedResponse",
    "ServedPostOfficesResponse",
    # Location discovery schemas
    "ProvinceItem",
    "ProvinceListResponse",
    "DistrictItem",
    "DistrictListResponse",
    "PostOfficeItem",
    "PostOfficeListResponse",
    # Triplet-based resolution schemas
    "LocationResolveRequest",
    "LocationResolveResponse",
    # Admin mapping management schemas
    "AdminMappingCreateRequest",
    "AdminMappingUpdateRequest",
]
