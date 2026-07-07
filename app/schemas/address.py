"""
User Address Pydantic Schemas

Request/response models for the /user/addresses CRUD endpoints.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Request Schemas
# ============================================================================

class AddressCreateRequest(BaseModel):
    """Request to create a delivery address."""

    title: Optional[str] = Field(None, max_length=100, description="Label e.g. Home, Office")
    recipient_name: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=30)
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    post_office: str = Field(..., min_length=1, max_length=100)
    district: str = Field(..., min_length=1, max_length=100)
    province: str = Field(..., min_length=1, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    is_default: bool = False

    @field_validator("address_line1", "post_office", "district", "province")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "address_line1": "42/A, Flower Road",
                "address_line2": "Welipenna",
                "post_office": "Welipenna",
                "district": "Kalutara",
                "province": "Western Province",
                "postal_code": "12000",
                "is_default": True,
            }
        }


class AddressUpdateRequest(BaseModel):
    """Request to update a delivery address (partial)."""

    title: Optional[str] = Field(None, max_length=100)
    recipient_name: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=30)
    address_line1: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    post_office: Optional[str] = Field(None, min_length=1, max_length=100)
    district: Optional[str] = Field(None, min_length=1, max_length=100)
    province: Optional[str] = Field(None, min_length=1, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    is_default: Optional[bool] = None


# ============================================================================
# Response Schemas
# ============================================================================

class AddressResponse(BaseModel):
    """Address in API responses (snake_case, per mobile contract)."""

    address_id: str
    title: Optional[str] = None
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    post_office: str
    district: str
    province: str
    postal_code: Optional[str] = None
    is_default: bool = False
    # Resolved delivery branch for this address (via post_office mapping).
    # branch_id is null / is_serviceable false when no branch serves the area.
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    is_serviceable: bool = False


class AddressListResponse(BaseModel):
    """List of addresses wrapped in `data` (per mobile contract)."""

    success: bool = True
    data: List[AddressResponse]


class AddressDetailResponse(BaseModel):
    """Single address wrapped in `data`."""

    success: bool = True
    data: AddressResponse
    message: Optional[str] = None
