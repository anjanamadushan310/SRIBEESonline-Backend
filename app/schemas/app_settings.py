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
