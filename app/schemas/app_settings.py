"""
Pydantic Schemas for AppSettings / Splash Video Management
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Admin — Splash Video
# ============================================================================

class SplashVideoResponse(BaseModel):
    """Response showing current splash video configuration."""
    setting_id: Optional[UUID] = None
    key: str = "splash_video_url"
    video_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SplashVideoUploadResponse(BaseModel):
    """Response after uploading a new splash video."""
    success: bool = True
    data: SplashVideoResponse
    message: str = "Splash video uploaded successfully"


# ============================================================================
# Admin — Platform Settings (checkout pricing + mobile app config)
# ============================================================================

class PlatformSettings(BaseModel):
    """Human-facing platform configuration values."""
    flat_delivery_fee: float = Field(..., ge=0, description="Flat delivery fee (currency units)")
    order_tax_rate_percent: float = Field(
        ..., ge=0, le=100, description="Order tax rate as a percentage (15 = 15%)"
    )
    splash_video_url: Optional[str] = Field(None, description="Splash-screen video URL")


class PlatformSettingsResponse(BaseModel):
    """GET /admin/settings response."""
    success: bool = True
    data: PlatformSettings


class PlatformSettingsUpdate(BaseModel):
    """PATCH /admin/settings — all fields optional (partial update)."""
    flat_delivery_fee: Optional[float] = Field(None, ge=0)
    order_tax_rate_percent: Optional[float] = Field(None, ge=0, le=100)
    splash_video_url: Optional[str] = Field(None, max_length=500)


# ============================================================================
# Public — Splash Config (Flutter client)
# ============================================================================

class SplashConfigResponse(BaseModel):
    """
    Minimal payload returned to the Flutter app on startup.

    Cached aggressively in Redis since every app launch hits this endpoint.
    """
    splash_video_url: Optional[str] = Field(
        None,
        description="URL of the splash animation video. Null means no video.",
    )
    is_active: bool = Field(
        True,
        description="Whether the splash video should be shown.",
    )
