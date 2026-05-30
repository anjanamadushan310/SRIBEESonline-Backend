"""
AppSettings SQLAlchemy Model

Key-value store for application-wide configuration that can be
managed at runtime by Super Admins.  Used for splash screen video
URL, feature flags, and other dynamic configuration.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.config.database import Base


class AppSetting(Base):
    """
    Runtime application settings (key/value store).

    Each row represents a single configuration entry.  The ``key``
    column is unique and acts as the lookup identifier.

    Examples:
        key='splash_video_url'  value='https://s3.../video.mp4'
        key='maintenance_mode'  value='false'
    """

    __tablename__ = "app_settings"

    setting_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique setting identifier (e.g. splash_video_url)",
    )
    value = Column(
        Text,
        nullable=True,
        comment="Setting value (URL, JSON string, plain text, etc.)",
    )
    description = Column(
        String(500),
        nullable=True,
        comment="Human-readable description of this setting",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="Whether this setting is currently active",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<AppSetting {self.key}={self.value[:30] if self.value else None}>"
