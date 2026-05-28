"""
Category Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ============================================================================
# Request Schemas
# ============================================================================

class CategoryCreate(BaseModel):
    """Schema for creating a new category."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_category_id: Optional[UUID] = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_category_id: Optional[UUID] = None
    is_active: Optional[bool] = None


# ============================================================================
# Response Schemas
# ============================================================================

class CategoryBase(BaseModel):
    """Base category response schema."""
    category_id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_category_id: Optional[UUID] = None
    is_active: bool
    
    model_config = {"from_attributes": True}


class CategoryResponse(CategoryBase):
    """Category response with additional fields."""
    _id: Optional[str] = None  # For mobile app compatibility
    product_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def _id(self) -> str:
        return str(self.category_id)


class CategoryWithChildren(CategoryResponse):
    """Category with nested children for hierarchical display."""
    children: List["CategoryWithChildren"] = []


class CategoriesListResponse(BaseModel):
    """Response for list of categories."""
    success: bool = True
    data: dict
    
    @classmethod
    def from_categories(cls, categories: List[CategoryResponse]):
        return cls(
            success=True,
            data={"categories": categories}
        )


class CategoryDetailResponse(BaseModel):
    """Response for single category."""
    success: bool = True
    data: CategoryResponse


class CategoryCreateResponse(BaseModel):
    """Response after creating a category."""
    success: bool = True
    data: CategoryResponse
    message: str = "Category created successfully"


class CategoryUpdateResponse(BaseModel):
    """Response after updating a category."""
    success: bool = True
    data: CategoryResponse
    message: str = "Category updated successfully"


class CategoryDeleteResponse(BaseModel):
    """Response after deleting a category."""
    success: bool = True
    message: str = "Category deleted successfully"


# Allow forward references
CategoryWithChildren.model_rebuild()
