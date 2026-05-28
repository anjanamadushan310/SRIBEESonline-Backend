"""
SRIBEESonline FastAPI Backend - Schemas Module

Pydantic schemas for request/response validation.
"""
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RefreshTokenRequest,
    UserResponse,
    TokensResponse,
    AuthResponse,
    RegisterResponse,
    MessageResponse,
    RefreshTokenResponse,
)
from app.schemas.branch import (
    BranchCreate,
    BranchUpdate,
    BranchResponse,
    PostOfficeBranchMappingCreate,
    PostOfficeBranchMappingUpdate,
    PostOfficeBranchMappingResponse,
    PostOfficeBranchMappingListResponse,
    BranchResolveRequest,
    BranchResolveResponse,
    BranchContextResponse,
    BranchContextClearedResponse,
    ServedPostOfficesResponse,
    # Location discovery
    ProvinceItem,
    ProvinceListResponse,
    DistrictItem,
    DistrictListResponse,
    PostOfficeItem,
    PostOfficeListResponse,
    # Triplet-based resolution
    LocationResolveRequest,
    LocationResolveResponse,
    # Admin mapping management
    AdminMappingCreateRequest,
    AdminMappingUpdateRequest,
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
