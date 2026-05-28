"""
SRIBEESonline - AppSettings Service

CRUD operations for the ``app_settings`` table.
Provides specialised helpers for the splash-video use-case.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.app_settings import AppSetting


# Well-known setting keys
SPLASH_VIDEO_KEY = "splash_video_url"


class AppSettingsService:
    """Service for runtime application settings."""

    # ------------------------------------------------------------------
    # Generic key/value CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def get_by_key(db: AsyncSession, key: str) -> Optional[AppSetting]:
        """Fetch a single setting by key."""
        result = await db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert(
        db: AsyncSession,
        key: str,
        value: Optional[str],
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> AppSetting:
        """Create or update a setting by key."""
        setting = await AppSettingsService.get_by_key(db, key)
        if setting is None:
            setting = AppSetting(
                key=key,
                value=value,
                description=description,
                is_active=is_active,
            )
            db.add(setting)
        else:
            setting.value = value
            if description is not None:
                setting.description = description
            setting.is_active = is_active

        await db.commit()
        await db.refresh(setting)
        logger.info(f"AppSetting upserted: {key}")
        return setting

    # ------------------------------------------------------------------
    # Splash video helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def get_splash_video(db: AsyncSession) -> Optional[AppSetting]:
        """Get the splash video setting."""
        return await AppSettingsService.get_by_key(db, SPLASH_VIDEO_KEY)

    @staticmethod
    async def set_splash_video_url(
        db: AsyncSession,
        url: str,
        is_active: bool = True,
    ) -> AppSetting:
        """Set (or update) the splash video URL."""
        return await AppSettingsService.upsert(
            db,
            key=SPLASH_VIDEO_KEY,
            value=url,
            description="URL of the splash-screen animation video shown when the Flutter app opens",
            is_active=is_active,
        )
