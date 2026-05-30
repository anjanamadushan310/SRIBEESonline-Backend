"""
SRIBEESonline - S3 Storage Service

Handles file uploads to AWS S3 (or S3-compatible storage like MinIO,
DigitalOcean Spaces).

Features:
  - Async-friendly upload from file-like objects and local paths
  - Automatic content-type detection
  - Public URL generation
  - Folder-based key organisation (e.g. splash/, products/, etc.)
  - Android emulator URL rewriting (localhost -> 10.0.2.2)
"""
import mimetypes
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger

from app.config.settings import settings


class StorageService:
    """Service for uploading / deleting files on S3."""

    _client = None

    @classmethod
    def _get_client(cls):
        """Lazily create and cache the boto3 S3 client."""
        if cls._client is None:
            kwargs = {
                "service_name": "s3",
                "region_name": settings.aws_region,
                "config": BotoConfig(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"},
                ),
            }
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                kwargs["aws_access_key_id"] = settings.aws_access_key_id
                kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
            if settings.s3_endpoint_url:
                kwargs["endpoint_url"] = settings.s3_endpoint_url

            cls._client = boto3.client(**kwargs)
            logger.info(
                f"S3 client initialised — bucket={settings.s3_bucket_name}, "
                f"region={settings.aws_region}, "
                f"endpoint={settings.s3_endpoint_url or 'AWS default'}"
            )
        return cls._client

    # ------------------------------------------------------------------
    # Public URL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_key(folder: str, filename: str) -> str:
        """Generate a unique S3 object key preserving the file extension."""
        ext = Path(filename).suffix.lower() or ""
        unique = uuid.uuid4().hex[:12]
        safe_name = Path(filename).stem.replace(" ", "_")[:60]
        return f"{folder.strip('/')}/{safe_name}_{unique}{ext}"

    @staticmethod
    def _guess_content_type(filename: str) -> str:
        """Return MIME type for *filename*, falling back to binary stream."""
        ct, _ = mimetypes.guess_type(filename)
        return ct or "application/octet-stream"

    @classmethod
    def public_url(cls, key: str) -> str:
        """
        Return the full public URL for an S3 key.

        This is the *canonical* URL stored in the database.  It uses the
        ``S3_PUBLIC_URL_PREFIX`` (e.g. ``http://localhost:9000/sribees-assets``)
        so that browsers and the admin panel on the host machine can reach it.
        """
        return f"{settings.s3_public_base_url}/{key}"

    @classmethod
    def rewrite_url_for_client(cls, url: Optional[str], client_platform: Optional[str] = None) -> Optional[str]:
        """
        Rewrite an S3 URL so it is reachable from the requesting client.

        **Problem**: In local Docker development the canonical URL uses
        ``localhost:9000`` which is unreachable from the Android emulator
        (it has its own loopback).  The emulator can reach the host via
        the magic IP ``10.0.2.2``.

        **Solution**: When ``S3_EMULATOR_URL_PREFIX`` is configured and the
        client identifies itself as an Android emulator (via the header
        ``X-Client-Platform: android-emulator``), replace the public
        prefix with the emulator prefix.

        For production (real AWS S3) both prefixes are the same or
        ``S3_EMULATOR_URL_PREFIX`` is unset, so this is a no-op.
        """
        if url is None:
            return None

        emulator_prefix = settings.s3_emulator_url_prefix
        if not emulator_prefix:
            return url

        public_prefix = settings.s3_public_base_url

        is_emulator = (
            client_platform
            and client_platform.lower() in ("android-emulator", "android_emulator")
        )

        if is_emulator and url.startswith(public_prefix):
            rewritten = url.replace(public_prefix, emulator_prefix.rstrip("/"), 1)
            return rewritten

        return url

    # ------------------------------------------------------------------
    # Upload methods
    # ------------------------------------------------------------------

    @classmethod
    def upload_fileobj(
        cls,
        fileobj: BinaryIO,
        filename: str,
        folder: str = "uploads",
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file-like object to S3.

        Returns the **canonical public URL** of the uploaded object.
        """
        client = cls._get_client()
        key = cls._generate_key(folder, filename)
        ct = content_type or cls._guess_content_type(filename)

        try:
            client.upload_fileobj(
                Fileobj=fileobj,
                Bucket=settings.s3_bucket_name,
                Key=key,
                ExtraArgs={
                    "ContentType": ct,
                    "CacheControl": "public, max-age=31536000",
                },
            )
            url = cls.public_url(key)
            logger.info(f"S3 upload OK: {key} ({ct})")
            return url
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"S3 upload failed for {key}: {exc}")
            raise RuntimeError(f"Failed to upload file to S3: {exc}") from exc

    @classmethod
    def upload_local_file(
        cls,
        local_path: str,
        folder: str = "uploads",
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file from the local filesystem to S3.

        Returns the **canonical public URL** of the uploaded object.
        """
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        client = cls._get_client()
        key = cls._generate_key(folder, path.name)
        ct = content_type or cls._guess_content_type(path.name)

        try:
            client.upload_file(
                Filename=str(path),
                Bucket=settings.s3_bucket_name,
                Key=key,
                ExtraArgs={
                    "ContentType": ct,
                    "CacheControl": "public, max-age=31536000",
                },
            )
            url = cls.public_url(key)
            logger.info(f"S3 upload (local file) OK: {key} ({ct}) size={path.stat().st_size}")
            return url
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"S3 upload failed for {key}: {exc}")
            raise RuntimeError(f"Failed to upload file to S3: {exc}") from exc

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    @classmethod
    def delete_object(cls, key: str) -> bool:
        """Delete a single object from S3 by key. Returns True on success."""
        client = cls._get_client()
        try:
            client.delete_object(Bucket=settings.s3_bucket_name, Key=key)
            logger.info(f"S3 delete OK: {key}")
            return True
        except (ClientError, BotoCoreError) as exc:
            logger.error(f"S3 delete failed for {key}: {exc}")
            return False

    @classmethod
    def delete_by_url(cls, url: str) -> bool:
        """
        Delete an S3 object given its public URL.

        Extracts the key from the URL using the configured base URL prefix.
        """
        base = settings.s3_public_base_url
        if not url.startswith(base):
            logger.warning(f"URL does not match S3 base — cannot delete: {url}")
            return False
        key = url[len(base):].lstrip("/")
        return cls.delete_object(key)
