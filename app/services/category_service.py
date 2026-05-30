"""
Category Service - Business Logic
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    """Service class for category operations."""

    @staticmethod
    async def get_all(
        db: AsyncSession,
        include_inactive: bool = False
    ) -> List[dict]:
        """Get all categories with product counts."""
        query = (
            select(
                Category,
                func.count(func.distinct(Category.products)).label("product_count")
            )
            .outerjoin(Category.products)
            .group_by(Category.category_id)
            .order_by(Category.name)
        )

        if not include_inactive:
            query = query.where(Category.is_active == True)

        result = await db.execute(query)
        categories = result.all()

        return [
            {
                **cat[0].__dict__,
                "product_count": cat[1] or 0
            }
            for cat in categories
        ]

    @staticmethod
    async def get_all_simple(
        db: AsyncSession,
        include_inactive: bool = False
    ) -> List[Category]:
        """Get all categories without product counts (simpler query)."""
        query = select(Category).order_by(Category.name)

        if not include_inactive:
            query = query.where(Category.is_active == True)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_hierarchical(db: AsyncSession) -> List[dict]:
        """Get categories in hierarchical structure (parent-child)."""
        categories = await CategoryService.get_all_simple(db)

        # Build hierarchy
        category_map = {}
        root_categories = []

        # First pass: create map with children array
        for cat in categories:
            category_map[str(cat.category_id)] = {
                "category_id": cat.category_id,
                "_id": str(cat.category_id),
                "name": cat.name,
                "slug": cat.slug,
                "description": cat.description,
                "image_url": cat.image_url,
                "parent_category_id": cat.parent_category_id,
                "is_active": cat.is_active,
                "product_count": 0,
                "children": []
            }

        # Second pass: build tree
        for cat in categories:
            cat_dict = category_map[str(cat.category_id)]
            if cat.parent_category_id and str(cat.parent_category_id) in category_map:
                parent = category_map[str(cat.parent_category_id)]
                parent["children"].append(cat_dict)
            else:
                root_categories.append(cat_dict)

        return root_categories

    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: UUID) -> Optional[Category]:
        """Get category by ID."""
        result = await db.execute(
            select(Category).where(Category.category_id == category_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug: str) -> Optional[Category]:
        """Get category by slug."""
        result = await db.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id_or_slug(
        db: AsyncSession,
        identifier: str
    ) -> Optional[Category]:
        """Get category by ID or slug."""
        # Try UUID first
        try:
            category_uuid = UUID(identifier)
            category = await CategoryService.get_by_id(db, category_uuid)
            if category:
                return category
        except ValueError:
            pass

        # Try slug
        return await CategoryService.get_by_slug(db, identifier)

    @staticmethod
    async def create(
        db: AsyncSession,
        data: CategoryCreate
    ) -> Category:
        """Create a new category."""
        category = Category(
            name=data.name,
            slug=data.slug,
            description=data.description,
            image_url=data.image_url,
            parent_category_id=data.parent_category_id,
            is_active=data.is_active
        )

        db.add(category)
        await db.commit()
        await db.refresh(category)

        return category

    @staticmethod
    async def update(
        db: AsyncSession,
        category: Category,
        data: CategoryUpdate
    ) -> Category:
        """Update an existing category."""
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(category, field, value)

        await db.commit()
        await db.refresh(category)

        return category

    @staticmethod
    async def delete(db: AsyncSession, category: Category) -> None:
        """Delete a category."""
        await db.delete(category)
        await db.commit()

    @staticmethod
    async def has_products(db: AsyncSession, category_id: UUID) -> bool:
        """Check if category has any products."""
        # Import here to avoid circular imports
        from app.models.product import Product

        result = await db.execute(
            select(func.count(Product.product_id))
            .where(Product.category_id == category_id)
        )
        count = result.scalar()
        return count > 0
