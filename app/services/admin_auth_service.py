"""
Admin Auth Service
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_token_pair
from app.models.admin import Admin, AdminSession, AdminRole
from app.schemas.admin_auth import (
    AdminAuthResponse,
    AdminResponse,
    AdminTokensResponse,
    AdminProfileResponse,
    AdminListResponse,
    CreateAdminRequest,
)
from app.utils.logger import logger


class AdminAuthService:
    """Admin authentication service."""
    
    @staticmethod
    async def login(email: str, password: str, db: AsyncSession) -> AdminAuthResponse:
        """
        Authenticate admin user.
        """
        # Find admin by email
        result = await db.execute(
            select(Admin).where(Admin.email == email.lower())
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            raise ValueError("Invalid email or password")
        
        if not admin.is_active:
            raise ValueError("Account is disabled")
        
        # Verify password
        if not verify_password(password, admin.password_hash):
            raise ValueError("Invalid email or password")
        
        # Create session
        session_id = uuid4()
        refresh_token = secrets.token_urlsafe(64)
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        session = AdminSession(
            session_id=session_id,
            admin_id=admin.admin_id,
            refresh_token_hash=hash_password(refresh_token),
            expires_at=expires_at,
        )
        db.add(session)
        
        # Update last login
        admin.last_login = datetime.utcnow()
        
        await db.commit()
        await db.refresh(admin)
        
        # Generate tokens
        tokens = create_token_pair(
            user_id=admin.admin_id,
            email=admin.email,
            session_id=session_id,
            is_admin=True,
            role=admin.role.value,
        )
        
        logger.info(f"Admin logged in: {admin.email}")
        
        return AdminAuthResponse(
            success=True,
            message="Login successful",
            admin=AdminResponse(
                admin_id=admin.admin_id,
                email=admin.email,
                full_name=admin.full_name,
                role=admin.role,
                branch_id=admin.branch_id,
                is_active=admin.is_active,
                last_login=admin.last_login,
                created_at=admin.created_at,
            ),
            tokens=AdminTokensResponse(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
            ),
        )
    
    @staticmethod
    async def get_profile(admin_id: UUID, db: AsyncSession) -> AdminProfileResponse:
        """
        Get admin profile.
        """
        result = await db.execute(
            select(Admin).where(Admin.admin_id == admin_id)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            raise ValueError("Admin not found")
        
        return AdminProfileResponse(
            success=True,
            admin=AdminResponse(
                admin_id=admin.admin_id,
                email=admin.email,
                full_name=admin.full_name,
                role=admin.role,
                branch_id=admin.branch_id,
                is_active=admin.is_active,
                last_login=admin.last_login,
                created_at=admin.created_at,
            ),
        )
    
    @staticmethod
    async def create_admin(
        data: CreateAdminRequest,
        created_by: UUID,
        db: AsyncSession
    ) -> AdminResponse:
        """
        Create new admin user.
        """
        # Check if email exists
        result = await db.execute(
            select(Admin).where(Admin.email == data.email.lower())
        )
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        # Create admin
        admin = Admin(
            admin_id=uuid4(),
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=AdminRole(data.role.value),
            branch_id=data.branch_id,
            is_active=True,
        )
        
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        
        logger.info(f"Admin created: {admin.email} by admin {created_by}")
        
        return AdminResponse(
            admin_id=admin.admin_id,
            email=admin.email,
            full_name=admin.full_name,
            role=admin.role,
            branch_id=admin.branch_id,
            is_active=admin.is_active,
            last_login=admin.last_login,
            created_at=admin.created_at,
        )
    
    @staticmethod
    async def list_admins(db: AsyncSession) -> AdminListResponse:
        """
        List all admin users.
        """
        result = await db.execute(
            select(Admin).order_by(Admin.created_at.desc())
        )
        admins = result.scalars().all()
        
        return AdminListResponse(
            success=True,
            admins=[
                AdminResponse(
                    admin_id=a.admin_id,
                    email=a.email,
                    full_name=a.full_name,
                    role=a.role,
                    branch_id=a.branch_id,
                    is_active=a.is_active,
                    last_login=a.last_login,
                    created_at=a.created_at,
                )
                for a in admins
            ],
            total=len(admins),
        )
    
    @staticmethod
    async def logout(admin_id: UUID, db: AsyncSession) -> dict:
        """
        Logout admin by invalidating sessions.
        """
        await db.execute(
            delete(AdminSession).where(AdminSession.admin_id == admin_id)
        )
        await db.commit()
        
        return {"success": True, "message": "Logged out successfully"}
