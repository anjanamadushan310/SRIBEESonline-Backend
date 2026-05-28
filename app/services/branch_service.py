"""
SRIBEESonline - Branch Resolution & Location Management Service

Handles:
  1. Hierarchical location discovery  (province → district → post_office)
  2. Branch resolution via saved address  OR  location triplet
  3. Redis branch-context session management
  4. Admin CRUD for PostOfficeBranchMapping
"""
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import delete, distinct, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config.redis import RedisKeys, RedisTTL
from app.core.exceptions import (
    DuplicateError,
    LocationNotServedError,
    NotFoundError,
)
from app.models.branch import Branch, PostOfficeBranchMapping
from app.models.user import Address
from app.utils.logger import logger


# ============================================================================
# Hierarchical Location Discovery  (for cascading dropdowns)
# ============================================================================

async def list_provinces(db: AsyncSession) -> list[dict]:
    """
    Return every province that has at least one active mapping,
    together with AI-friendly coverage metadata.
    """
    rows = await db.execute(
        select(
            PostOfficeBranchMapping.province,
            func.count(distinct(PostOfficeBranchMapping.district)).label("district_count"),
            func.count(PostOfficeBranchMapping.post_office).label("po_count"),
            func.count(distinct(PostOfficeBranchMapping.branch_id)).label("branch_count"),
        )
        .where(
            PostOfficeBranchMapping.is_active.is_(True),
            PostOfficeBranchMapping.province.isnot(None),
        )
        .group_by(PostOfficeBranchMapping.province)
        .order_by(PostOfficeBranchMapping.province)
    )

    result = []
    for row in rows.all():
        province, dist_ct, po_ct, br_ct = row
        result.append({
            "province": province,
            "districtCount": dist_ct,
            "postOfficeCount": po_ct,
            "branchCount": br_ct,
            "coverageSummary": (
                f"{province} is served by {br_ct} branch(es) covering "
                f"{dist_ct} district(s) and {po_ct} post office(s)."
            ),
        })
    return result


async def list_districts(db: AsyncSession, province: str) -> list[dict]:
    """
    Return districts within a province together with coverage metadata.
    """
    normalized = province.strip().title()

    # Sub-query for branch names aggregated per district
    rows = await db.execute(
        select(
            PostOfficeBranchMapping.district,
            PostOfficeBranchMapping.province,
            func.count(PostOfficeBranchMapping.post_office).label("po_count"),
            func.array_agg(distinct(PostOfficeBranchMapping.branch_name)).label("branch_names"),
        )
        .where(
            PostOfficeBranchMapping.is_active.is_(True),
            PostOfficeBranchMapping.province == normalized,
            PostOfficeBranchMapping.district.isnot(None),
        )
        .group_by(PostOfficeBranchMapping.district, PostOfficeBranchMapping.province)
        .order_by(PostOfficeBranchMapping.district)
    )

    result = []
    for row in rows.all():
        district, prov, po_ct, branch_names = row
        names_list = sorted(branch_names) if branch_names else []
        result.append({
            "district": district,
            "province": prov,
            "postOfficeCount": po_ct,
            "branchNames": names_list,
            "coverageSummary": (
                f"{district} district in {prov} has {po_ct} post office(s) "
                f"served by: {', '.join(names_list)}."
            ),
        })
    return result


async def list_post_offices_for_district(
    db: AsyncSession,
    district: str,
) -> list[dict]:
    """
    Return post offices within a district with branch details.
    Uses ``joinedload`` on Branch for optimized fetching.
    """
    normalized = district.strip().title()

    result = await db.execute(
        select(PostOfficeBranchMapping)
        .options(joinedload(PostOfficeBranchMapping.branch))
        .where(
            PostOfficeBranchMapping.is_active.is_(True),
            PostOfficeBranchMapping.district == normalized,
        )
        .order_by(PostOfficeBranchMapping.post_office)
    )

    mappings = result.unique().scalars().all()
    return [
        {
            "postOffice": m.post_office,
            "district": m.district,
            "province": m.province,
            "branchId": str(m.branch_id),
            "branchName": m.branch_name,
            "isActive": m.is_active,
        }
        for m in mappings
    ]


# ============================================================================
# Data-layer look-ups
# ============================================================================

async def get_address_for_user(
    db: AsyncSession,
    address_id: UUID,
    user_id: UUID,
) -> Optional[Address]:
    """Fetch an address that belongs to the given user."""
    result = await db.execute(
        select(Address).where(
            Address.address_id == address_id,
            Address.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def resolve_branch_by_post_office(
    db: AsyncSession,
    post_office_name: str,
) -> Optional[PostOfficeBranchMapping]:
    """Look up which branch serves the given Post Office (active only)."""
    normalized = post_office_name.strip().title()
    result = await db.execute(
        select(PostOfficeBranchMapping)
        .options(joinedload(PostOfficeBranchMapping.branch))
        .where(
            PostOfficeBranchMapping.post_office == normalized,
            PostOfficeBranchMapping.is_active.is_(True),
        )
    )
    return result.unique().scalar_one_or_none()


async def resolve_branch_by_location_triplet(
    db: AsyncSession,
    province: str,
    district: str,
    post_office: str,
) -> Optional[PostOfficeBranchMapping]:
    """
    Resolve a branch using the full ``{province, district, post_office}`` triplet.

    Leverages the composite B-tree index ``idx_po_branch_mapping_location_triplet``.
    """
    result = await db.execute(
        select(PostOfficeBranchMapping)
        .options(joinedload(PostOfficeBranchMapping.branch))
        .where(
            PostOfficeBranchMapping.province == province.strip().title(),
            PostOfficeBranchMapping.district == district.strip().title(),
            PostOfficeBranchMapping.post_office == post_office.strip().title(),
            PostOfficeBranchMapping.is_active.is_(True),
        )
    )
    return result.unique().scalar_one_or_none()


async def list_served_post_offices(db: AsyncSession) -> list[str]:
    """Return a sorted list of all actively-served Post Office names."""
    result = await db.execute(
        select(PostOfficeBranchMapping.post_office)
        .where(PostOfficeBranchMapping.is_active.is_(True))
        .order_by(PostOfficeBranchMapping.post_office)
    )
    return [row[0] for row in result.all()]


# ============================================================================
# Redis branch-context helpers
# ============================================================================

def _branch_session_id(user_id: UUID) -> str:
    """Normalise user_id to Redis session id."""
    return str(user_id)


async def set_branch_context(
    redis: Redis,
    user_id: UUID,
    branch_id: UUID,
    branch_name: str,
    post_office: str,
    delivery_info: Optional[dict] = None,
) -> dict:
    """
    Store the resolved branch context in the user's Redis session.

    Key pattern: ``session:{session_id}:branch_context``
    TTL: 30 days

    The ``delivery_info`` dict may contain ``province``, ``district``,
    and any other address metadata useful for the frontend.
    """
    return await set_branch_context_for_session(
        redis,
        session_id=_branch_session_id(user_id),
        branch_id=branch_id,
        branch_name=branch_name,
        post_office=post_office,
        delivery_info=delivery_info,
    )


def _build_branch_context(
    branch_id: UUID,
    branch_name: str,
    post_office: str,
    delivery_info: Optional[dict] = None,
) -> dict:
    """Build the branch context dict (same shape as stored in Redis)."""
    now = datetime.now(timezone.utc)
    return {
        "branch_id": str(branch_id),
        "branch_name": branch_name,
        "post_office": post_office,
        "delivery_info": delivery_info or {},
        "resolved_at": now.isoformat(),
    }


async def set_branch_context_for_session(
    redis: Redis,
    session_id: str,
    branch_id: UUID,
    branch_name: str,
    post_office: str,
    delivery_info: Optional[dict] = None,
) -> dict:
    """
    Store branch context by session id (str(user_id) or "guest:{device_id}").
    Key: session:{session_id}:branch_context
    """
    context = _build_branch_context(
        branch_id=branch_id,
        branch_name=branch_name,
        post_office=post_office,
        delivery_info=delivery_info,
    )
    key = RedisKeys.branch_context(session_id)
    await redis.set(key, json.dumps(context), ex=RedisTTL.BRANCH_CONTEXT)
    logger.info(
        f"Branch context set for session {session_id}: "
        f"{post_office} → {branch_name} ({branch_id})"
    )
    return context


async def get_branch_context(
    redis: Redis,
    user_id: UUID,
) -> Optional[dict]:
    """Retrieve the current branch context from Redis."""
    key = RedisKeys.branch_context(str(user_id))
    raw = await redis.get(key)
    if raw is None:
        return None

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Corrupt branch context for user {user_id}, clearing key")
        await redis.delete(key)
        return None


async def clear_branch_context(
    redis: Redis,
    user_id: UUID,
) -> bool:
    """Remove the branch context from Redis, forcing re-selection."""
    key = RedisKeys.branch_context(str(user_id))
    deleted = await redis.delete(key)
    if deleted:
        logger.info(f"Branch context cleared for user {user_id}")
    return bool(deleted)


# ============================================================================
# High-level orchestration — address-based
# ============================================================================

async def resolve_address_to_branch(
    db: AsyncSession,
    redis: Redis,
    address_id: UUID,
    user_id: UUID,
) -> dict:
    """
    Full resolution flow via saved address:
      1. Validate address ownership.
      2. Extract ``post_office`` (+ district, province).
      3. Look up ``PostOfficeBranchMapping``.
      4. Store branch context (with delivery_info) in Redis.
    """
    address = await get_address_for_user(db, address_id, user_id)
    if address is None:
        raise NotFoundError(
            resource="Address",
            identifier=str(address_id),
            message="Address not found or does not belong to this user",
        )

    post_office = address.post_office
    if not post_office:
        raise NotFoundError(
            resource="Post Office",
            message="The selected address does not have a Post Office field set",
        )

    mapping = await resolve_branch_by_post_office(db, post_office)
    if mapping is None:
        raise LocationNotServedError(
            post_office=post_office,
            district=getattr(address, "district", None),
            province=getattr(address, "province", None),
        )

    delivery_info = {
        "province": mapping.province,
        "district": mapping.district,
        "post_office": mapping.post_office,
    }

    context = await set_branch_context(
        redis,
        user_id=user_id,
        branch_id=mapping.branch_id,
        branch_name=mapping.branch_name,
        post_office=mapping.post_office,
        delivery_info=delivery_info,
    )
    return context


# ============================================================================
# High-level orchestration — triplet-based
# ============================================================================

async def resolve_location_to_branch(
    db: AsyncSession,
    redis: Optional[Redis],
    user_id: UUID,
    province: str,
    district: str,
    post_office: str,
) -> dict:
    """Resolve location triplet and optionally store branch context for a user."""
    return await resolve_location_to_branch_for_session(
        db, redis, _branch_session_id(user_id), province, district, post_office,
    )


async def resolve_location_to_branch_for_session(
    db: AsyncSession,
    redis: Optional[Redis],
    session_id: str,
    province: str,
    district: str,
    post_office: str,
) -> dict:
    """
    Resolve a branch using a manually-selected location triplet
    (from the cascading dropdown UI) and optionally store the context in Redis.
    session_id: str(user_id) for authenticated users, or "guest:{device_id}" for guests.
    If Redis is None or storage fails, still returns the resolved context (no 500).
    """
    mapping = await resolve_branch_by_location_triplet(
        db, province, district, post_office,
    )
    if mapping is None:
        raise LocationNotServedError(
            post_office=post_office,
            district=district,
            province=province,
        )

    delivery_info = {
        "province": mapping.province,
        "district": mapping.district,
        "post_office": mapping.post_office,
    }

    context = _build_branch_context(
        branch_id=mapping.branch_id,
        branch_name=mapping.branch_name,
        post_office=mapping.post_office,
        delivery_info=delivery_info,
    )

    if redis is not None:
        try:
            await set_branch_context_for_session(
                redis,
                session_id=session_id,
                branch_id=mapping.branch_id,
                branch_name=mapping.branch_name,
                post_office=mapping.post_office,
                delivery_info=delivery_info,
            )
        except Exception as e:
            logger.warning(
                "Failed to store branch context in Redis for session %s: %s",
                session_id,
                e,
                exc_info=True,
            )

    return context


# ============================================================================
# Admin CRUD for PostOfficeBranchMapping
# ============================================================================

async def get_mapping_by_id(
    db: AsyncSession,
    mapping_id: UUID,
) -> Optional[PostOfficeBranchMapping]:
    """Fetch a single mapping by its primary key (with branch eager-loaded)."""
    result = await db.execute(
        select(PostOfficeBranchMapping)
        .options(joinedload(PostOfficeBranchMapping.branch))
        .where(PostOfficeBranchMapping.mapping_id == mapping_id)
    )
    return result.unique().scalar_one_or_none()


async def list_all_mappings(
    db: AsyncSession,
    province: Optional[str] = None,
    district: Optional[str] = None,
    active_only: bool = False,
) -> list[PostOfficeBranchMapping]:
    """Return mappings with optional province/district filters (admin use)."""
    stmt = (
        select(PostOfficeBranchMapping)
        .options(joinedload(PostOfficeBranchMapping.branch))
        .order_by(
            PostOfficeBranchMapping.province,
            PostOfficeBranchMapping.district,
            PostOfficeBranchMapping.post_office,
        )
    )

    if province:
        stmt = stmt.where(PostOfficeBranchMapping.province == province.strip().title())
    if district:
        stmt = stmt.where(PostOfficeBranchMapping.district == district.strip().title())
    if active_only:
        stmt = stmt.where(PostOfficeBranchMapping.is_active.is_(True))

    result = await db.execute(stmt)
    return list(result.unique().scalars().all())


async def create_mapping(
    db: AsyncSession,
    *,
    post_office: str,
    branch_id: UUID,
    branch_name: str,
    district: str,
    province: str,
    is_active: bool = True,
) -> PostOfficeBranchMapping:
    """
    Create a new PostOfficeBranchMapping.

    Raises ``DuplicateError`` if the post_office already exists.
    Raises ``NotFoundError`` if the referenced branch doesn't exist.
    """
    # Validate branch exists
    branch_result = await db.execute(
        select(Branch).where(Branch.branch_id == branch_id)
    )
    if branch_result.scalar_one_or_none() is None:
        raise NotFoundError(resource="Branch", identifier=str(branch_id))

    # Check for duplicate post office
    dup = await db.execute(
        select(PostOfficeBranchMapping.mapping_id).where(
            PostOfficeBranchMapping.post_office == post_office.strip().title()
        )
    )
    if dup.scalar_one_or_none() is not None:
        raise DuplicateError(
            field="post_office",
            message=f"A mapping for Post Office '{post_office}' already exists",
        )

    mapping = PostOfficeBranchMapping(
        post_office=post_office.strip().title(),
        branch_id=branch_id,
        branch_name=branch_name,
        district=district.strip().title(),
        province=province.strip().title(),
        is_active=is_active,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)

    logger.info(f"Mapping created: {mapping.post_office} → {mapping.branch_name}")
    return mapping


async def update_mapping(
    db: AsyncSession,
    mapping_id: UUID,
    **fields,
) -> PostOfficeBranchMapping:
    """
    Update an existing mapping.

    Only non-``None`` values in *fields* are applied.
    """
    mapping = await get_mapping_by_id(db, mapping_id)
    if mapping is None:
        raise NotFoundError(resource="Mapping", identifier=str(mapping_id))

    for key, value in fields.items():
        if value is not None and hasattr(mapping, key):
            setattr(mapping, key, value)

    await db.commit()
    await db.refresh(mapping)

    logger.info(f"Mapping updated: {mapping.mapping_id}")
    return mapping


async def delete_mapping(
    db: AsyncSession,
    mapping_id: UUID,
) -> bool:
    """
    Hard-delete a mapping.  Returns ``True`` if a row was actually removed.
    """
    mapping = await get_mapping_by_id(db, mapping_id)
    if mapping is None:
        raise NotFoundError(resource="Mapping", identifier=str(mapping_id))

    await db.delete(mapping)
    await db.commit()

    logger.info(f"Mapping deleted: {mapping_id}")
    return True
