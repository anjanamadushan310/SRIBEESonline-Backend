"""
SRIBEESonline FastAPI Backend - Semantic Search API

Multilingual semantic search endpoint using Gemini embeddings and pgvector.
Supports English, Sinhala, Tamil, and Singlish queries.

Branch visibility is enforced: results are post-filtered against
``branch_inventory`` when the user has an active branch session.
"""
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config.database import get_db
from app.config.redis import get_redis
from app.config.settings import get_settings
from app.core.dependencies import get_current_user
from app.schemas.semantic_search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    ProductSearchResultResponse,
    PaginationResponse,
    SearchMetadataResponse,
    SearchSuggestionsRequest,
    SearchSuggestionsResponse,
    PopularSearchesResponse,
    PopularSearchItem,
    SearchErrorResponse,
    CategoryInfo,
)
from app.services.semantic_search_service import (
    SemanticSearchService,
    SemanticSearchFilters,
)
from app.services import branch_service

router = APIRouter()
settings = get_settings()


# ============================================================================
# Dependencies
# ============================================================================

async def get_search_service(
    db: AsyncSession = Depends(get_db),
) -> SemanticSearchService:
    """Get semantic search service instance with database session."""
    return SemanticSearchService(db)


# ============================================================================
# Search Endpoints
# ============================================================================

@router.post(
    "",
    response_model=SemanticSearchResponse,
    responses={
        200: {
            "description": "Search completed successfully",
            "model": SemanticSearchResponse,
        },
        400: {
            "description": "Invalid search parameters",
            "model": SearchErrorResponse,
        },
        503: {
            "description": "Search service unavailable",
            "model": SearchErrorResponse,
        },
    },
    summary="Semantic Product Search",
    description="""
    Search for products using natural language queries.
    
    **Multilingual Support:**
    - English: "fresh red apples"
    - Sinhala: "රතු ඇපල් ගෙඩි"  
    - Tamil: "சிவப்பு ஆப்பிள்"
    - Singlish: "rata apple gedi"
    
    **Search Features:**
    - AI-powered semantic understanding via Gemini embeddings
    - Automatic fallback to keyword search if AI unavailable
    - Filtering by category, price range, and stock status
    - Results ranked by relevance/similarity score
    
    **Caching:**
    - Search results cached for 1 hour
    - Embeddings cached for 24 hours
    """,
)
async def search_products(
    request: SemanticSearchRequest,
    search_service: SemanticSearchService = Depends(get_search_service),
    redis: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> SemanticSearchResponse:
    """
    Search products using multilingual semantic search.

    Uses Gemini text-embedding-004 for query embedding and pgvector
    for vector similarity search. Falls back to keyword search
    if AI service is unavailable.

    Results are post-filtered against ``branch_inventory`` when
    the user has an active branch session (strict visibility).
    """
    start_time = time.time()

    try:
        # Resolve branch context (optional but recommended)
        branch_id: Optional[UUID] = None
        context = await branch_service.get_branch_context(redis, current_user.user_id)
        if context:
            branch_id = UUID(context["branch_id"])

        # Build filters from request
        filters = None
        if request.filters:
            filters = SemanticSearchFilters(
                category_id=str(request.filters.category_id) if request.filters.category_id else None,
                min_price=float(request.filters.min_price) if request.filters.min_price else None,
                max_price=float(request.filters.max_price) if request.filters.max_price else None,
                in_stock_only=request.filters.in_stock_only,
                similarity_threshold=request.filters.similarity_threshold or settings.semantic_search_similarity_threshold,
                branch_id=branch_id,
            )
        else:
            filters = SemanticSearchFilters(
                similarity_threshold=settings.semantic_search_similarity_threshold,
                branch_id=branch_id,
            )
        
        # Get pagination parameters
        page = request.pagination.page if request.pagination else 1
        page_size = request.pagination.page_size if request.pagination else 20
        offset = (page - 1) * page_size
        
        # Perform search
        search_result = await search_service.search(
            query=request.query,
            filters=filters,
            limit=page_size,
            offset=offset,
        )
        
        # Calculate timing
        took_ms = int((time.time() - start_time) * 1000)
        
        # Track analytics if enabled
        if request.options is None or request.options.track_analytics:
            try:
                await search_service.track_search_analytics(
                    query=request.query,
                    search_type=search_result.search_type,
                    total_results=search_result.total_count,
                )
            except Exception as e:
                logger.warning(f"Failed to track analytics: {e}")
        
        # Build response
        results = []
        for product in search_result.products:
            # Build category info
            category_info = None
            if product.category_name:
                category_info = CategoryInfo(
                    id=product.category_id,
                    name=product.category_name,
                )
            
            # Calculate discount percentage
            discount_percentage = None
            if product.compare_at_price and product.price < product.compare_at_price:
                discount_percentage = round(
                    (1 - product.price / product.compare_at_price) * 100, 1
                )
            
            results.append(
                ProductSearchResultResponse(
                    product_id=product.product_id,
                    name=product.name,
                    slug=product.slug,
                    description=product.description,
                    short_description=product.short_description,
                    price=product.price,
                    compare_at_price=product.compare_at_price,
                    discount_percentage=discount_percentage,
                    stock_quantity=product.stock_quantity,
                    in_stock=product.stock_quantity > 0,
                    image_url=product.image_url,
                    category=category_info,
                    similarity_score=product.similarity_score,
                    relevance_score=product.relevance_score,
                )
            )
        
        # Calculate pagination
        total_pages = (search_result.total_count + page_size - 1) // page_size if page_size > 0 else 0
        
        return SemanticSearchResponse(
            results=results,
            pagination=PaginationResponse(
                page=page,
                page_size=page_size,
                total_results=search_result.total_count,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
            search_metadata=SearchMetadataResponse(
                query=request.query,
                search_type=search_result.search_type,
                took_ms=took_ms,
                cached=search_result.cached,
            ),
            facets=None,  # TODO: Implement faceted search
        )
        
    except ValueError as e:
        logger.warning(f"Invalid search request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": str(e),
                "error_code": "INVALID_REQUEST",
            },
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "message": "Search service temporarily unavailable",
                "error_code": "SERVICE_UNAVAILABLE",
            },
        )


@router.get(
    "/suggestions",
    response_model=SearchSuggestionsResponse,
    summary="Search Suggestions",
    description="Get autocomplete suggestions based on popular searches.",
)
async def get_search_suggestions(
    query: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Partial search query"
    ),
    limit: int = Query(
        5,
        ge=1,
        le=10,
        description="Maximum suggestions"
    ),
    search_service: SemanticSearchService = Depends(get_search_service),
) -> SearchSuggestionsResponse:
    """
    Get search suggestions based on popular past searches.
    
    Returns suggestions that start with the provided query prefix,
    sorted by popularity.
    """
    try:
        suggestions = await search_service.get_search_suggestions(
            query=query,
            limit=limit,
        )
        
        return SearchSuggestionsResponse(
            suggestions=suggestions,
            query=query,
        )
        
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return SearchSuggestionsResponse(
            suggestions=[],
            query=query,
        )


@router.get(
    "/popular",
    response_model=PopularSearchesResponse,
    summary="Popular Searches",
    description="Get list of popular search queries.",
)
async def get_popular_searches(
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Number of popular searches to return"
    ),
    search_service: SemanticSearchService = Depends(get_search_service),
) -> PopularSearchesResponse:
    """
    Get the most popular search queries.
    
    Returns popular searches sorted by frequency, useful for
    displaying trending searches on the homepage.
    """
    try:
        popular = await search_service.get_popular_searches(limit=limit)
        
        return PopularSearchesResponse(
            searches=[
                PopularSearchItem(query=q, count=c)
                for q, c in popular
            ]
        )
        
    except Exception as e:
        logger.error(f"Popular searches error: {e}")
        return PopularSearchesResponse(searches=[])


# ============================================================================
# Health Check
# ============================================================================

@router.get(
    "/health",
    summary="Search Service Health",
    description="Check if the semantic search service is operational.",
)
async def search_health_check(
    search_service: SemanticSearchService = Depends(get_search_service),
):
    """
    Check semantic search service health.
    
    Returns status of:
    - Embedding service (Gemini API)
    - Vector database (pgvector)
    - Cache (Redis)
    """
    health = {
        "status": "healthy",
        "components": {
            "embedding_service": "unknown",
            "vector_database": "unknown",
            "cache": "unknown",
        },
    }
    
    try:
        # Check embedding service
        embedding_service = search_service.embedding_service
        if embedding_service:
            circuit_state = embedding_service.circuit_breaker.state.value
            health["components"]["embedding_service"] = circuit_state
            if circuit_state == "open":
                health["status"] = "degraded"
        
        # Check database (simple query)
        from sqlalchemy import text
        await search_service.db.execute(text("SELECT 1"))
        health["components"]["vector_database"] = "healthy"
        
        # Check Redis
        from app.config.redis import get_redis_client
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            health["components"]["cache"] = "healthy"
        else:
            health["components"]["cache"] = "not_configured"
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        health["status"] = "unhealthy"
        health["error"] = str(e)
    
    return health
