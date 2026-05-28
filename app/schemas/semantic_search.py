"""
SRIBEESonline - Semantic Search Schemas

Pydantic models for semantic search API request/response validation.
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Request Schemas
# ============================================================================

class SearchFiltersRequest(BaseModel):
    """Search filter parameters."""
    
    category_id: Optional[UUID] = Field(
        None,
        description="Filter by category ID"
    )
    min_price: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Minimum price filter"
    )
    max_price: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Maximum price filter"
    )
    in_stock_only: bool = Field(
        True,
        description="Only show products in stock"
    )
    similarity_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0)"
    )
    
    @field_validator('max_price')
    @classmethod
    def validate_price_range(cls, v, info):
        """Validate max_price is greater than min_price."""
        if v is not None and info.data.get('min_price') is not None:
            if v < info.data['min_price']:
                raise ValueError('max_price must be greater than min_price')
        return v


class SearchPaginationRequest(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(
        1,
        ge=1,
        description="Page number (1-indexed)"
    )
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Results per page (max 100)"
    )
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class SearchOptionsRequest(BaseModel):
    """Additional search options."""
    
    include_facets: bool = Field(
        False,
        description="Include faceted aggregations"
    )
    track_analytics: bool = Field(
        True,
        description="Track this search for analytics"
    )


class SemanticSearchRequest(BaseModel):
    """
    Semantic search request.
    
    Supports multilingual queries in:
    - English
    - Sinhala (සිංහල)
    - Tamil (தமிழ்)
    - Singlish
    """
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query (multilingual supported)"
    )
    filters: Optional[SearchFiltersRequest] = Field(
        None,
        description="Optional search filters"
    )
    pagination: Optional[SearchPaginationRequest] = Field(
        None,
        description="Pagination parameters"
    )
    options: Optional[SearchOptionsRequest] = Field(
        None,
        description="Additional search options"
    )
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Clean and validate query string."""
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "fresh red apples",
                    "filters": {
                        "in_stock_only": True,
                        "min_price": 0,
                        "max_price": 500
                    },
                    "pagination": {
                        "page": 1,
                        "page_size": 20
                    }
                },
                {
                    "query": "රතු ඇපල් ගෙඩි",
                    "filters": {
                        "category_id": "550e8400-e29b-41d4-a716-446655440000"
                    }
                },
                {
                    "query": "சிவப்பு ஆப்பிள்"
                }
            ]
        }
    }


# ============================================================================
# Response Schemas
# ============================================================================

class CategoryInfo(BaseModel):
    """Category information in search results."""
    
    id: Optional[str] = None
    name: Optional[str] = None


class ProductSearchResultResponse(BaseModel):
    """Individual product in search results."""
    
    product_id: str = Field(..., description="Product UUID")
    name: str = Field(..., description="Product name")
    slug: str = Field(..., description="URL-friendly slug")
    description: Optional[str] = Field(None, description="Full description")
    short_description: Optional[str] = Field(None, description="Brief description")
    price: float = Field(..., description="Current price")
    compare_at_price: Optional[float] = Field(None, description="Original price")
    discount_percentage: Optional[float] = Field(None, description="Discount percentage")
    stock_quantity: int = Field(..., description="Available stock")
    in_stock: bool = Field(..., description="Whether product is in stock")
    image_url: Optional[str] = Field(None, description="Primary image URL")
    category: Optional[CategoryInfo] = Field(None, description="Category information")
    similarity_score: Optional[float] = Field(
        None,
        description="Semantic similarity score (0.0-1.0)"
    )
    relevance_score: Optional[float] = Field(
        None,
        description="Keyword relevance score (for fallback search)"
    )


class PaginationResponse(BaseModel):
    """Pagination metadata."""
    
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Results per page")
    total_results: int = Field(..., description="Total matching results")
    total_pages: int = Field(..., description="Total pages")
    has_next: bool = Field(..., description="Has next page")
    has_previous: bool = Field(..., description="Has previous page")


class SearchMetadataResponse(BaseModel):
    """Search metadata."""
    
    query: str = Field(..., description="Original search query")
    search_type: str = Field(
        ...,
        description="Type of search performed (semantic/keyword/hybrid)"
    )
    took_ms: int = Field(..., description="Search duration in milliseconds")
    cached: bool = Field(..., description="Whether results were from cache")


class FacetBucket(BaseModel):
    """Individual facet bucket."""
    
    key: str
    count: int
    label: Optional[str] = None


class FacetsResponse(BaseModel):
    """Faceted search aggregations."""
    
    categories: Optional[List[FacetBucket]] = None
    price_ranges: Optional[List[Dict[str, Any]]] = None
    stock_status: Optional[List[FacetBucket]] = None


class SemanticSearchResponse(BaseModel):
    """
    Semantic search response.
    
    Contains search results with metadata, pagination, and optional facets.
    """
    
    results: List[ProductSearchResultResponse] = Field(
        ...,
        description="List of matching products"
    )
    pagination: PaginationResponse = Field(
        ...,
        description="Pagination information"
    )
    search_metadata: SearchMetadataResponse = Field(
        ...,
        description="Search execution metadata"
    )
    facets: Optional[FacetsResponse] = Field(
        None,
        description="Faceted aggregations (if requested)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "product_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "Fresh Red Apples",
                        "slug": "fresh-red-apples",
                        "short_description": "Crispy and sweet red apples",
                        "price": 350.00,
                        "compare_at_price": 400.00,
                        "discount_percentage": 12.5,
                        "stock_quantity": 100,
                        "in_stock": True,
                        "image_url": "https://example.com/apples.jpg",
                        "category": {
                            "id": "category-uuid",
                            "name": "Fruits"
                        },
                        "similarity_score": 0.92
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_results": 45,
                    "total_pages": 3,
                    "has_next": True,
                    "has_previous": False
                },
                "search_metadata": {
                    "query": "red apples",
                    "search_type": "semantic",
                    "took_ms": 45,
                    "cached": False
                }
            }
        }
    }


# ============================================================================
# Suggestion Schemas
# ============================================================================

class SearchSuggestionsRequest(BaseModel):
    """Request for search suggestions/autocomplete."""
    
    query: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Partial query for autocomplete"
    )
    limit: int = Field(
        5,
        ge=1,
        le=10,
        description="Maximum suggestions to return"
    )


class SearchSuggestionsResponse(BaseModel):
    """Response with search suggestions."""
    
    suggestions: List[str] = Field(
        ...,
        description="List of suggested search queries"
    )
    query: str = Field(
        ...,
        description="Original partial query"
    )


# ============================================================================
# Popular Searches Schema
# ============================================================================

class PopularSearchItem(BaseModel):
    """Individual popular search item."""
    
    query: str = Field(..., description="Search query")
    count: int = Field(..., description="Number of searches")


class PopularSearchesResponse(BaseModel):
    """Response with popular searches."""
    
    searches: List[PopularSearchItem] = Field(
        ...,
        description="List of popular searches"
    )


# ============================================================================
# Error Response Schema
# ============================================================================

class SearchErrorResponse(BaseModel):
    """Error response for search failures."""
    
    success: bool = Field(False)
    message: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for client handling")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "message": "Search query must be between 1 and 500 characters",
                "error_code": "INVALID_QUERY"
            }
        }
    }
