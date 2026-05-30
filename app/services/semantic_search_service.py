"""
SRIBEESonline - Semantic Search Service

Multilingual semantic product search using:
- Gemini embeddings (text-embedding-004)
- PostgreSQL pgvector for similarity search
- Redis caching for performance
- Fallback to keyword search on AI failure

Supports: English, Sinhala (සිංහල), Tamil (தமிழ்), Singlish
"""
import hashlib
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.redis import get_redis
from app.services.embedding_service import (
    CircuitOpenError,
    GeminiAPIError,
    GeminiEmbeddingService,
    get_embedding_service,
)

# ============================================================================
# Configuration
# ============================================================================

# Search parameters
DEFAULT_SIMILARITY_THRESHOLD = 0.65
DEFAULT_MAX_RESULTS = 20
MIN_QUERY_LENGTH = 1
MAX_QUERY_LENGTH = 500

# Cache configuration
SEARCH_RESULTS_CACHE_TTL = 3600  # 1 hour
POPULAR_QUERIES_KEY = "search:popular"
POPULAR_QUERIES_TTL = 86400  # 24 hours


# ============================================================================
# Data Models
# ============================================================================

class SearchType(str, Enum):
    """Type of search performed."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass
class SemanticSearchFilters:
    """Filters for semantic search."""
    category_id: Optional[UUID] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    in_stock_only: bool = True
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    branch_id: Optional[UUID] = None


@dataclass
class SemanticSearchOptions:
    """Options for semantic search."""
    max_results: int = DEFAULT_MAX_RESULTS
    offset: int = 0
    include_facets: bool = False
    track_analytics: bool = True


@dataclass
class ProductSearchResult:
    """Individual product search result."""
    product_id: UUID
    name: str
    slug: str
    description: Optional[str]
    short_description: Optional[str]
    price: Decimal
    compare_at_price: Optional[Decimal]
    stock_quantity: int
    image_url: Optional[str]
    category_id: Optional[UUID]
    category_name: Optional[str]
    similarity_score: Optional[float]
    relevance_score: Optional[float]

    @property
    def in_stock(self) -> bool:
        return self.stock_quantity > 0

    @property
    def discount_percentage(self) -> Optional[float]:
        if self.compare_at_price and self.compare_at_price > self.price:
            return float(
                (self.compare_at_price - self.price) / self.compare_at_price * 100
            )
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "product_id": str(self.product_id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "short_description": self.short_description,
            "price": float(self.price),
            "compare_at_price": float(self.compare_at_price) if self.compare_at_price else None,
            "discount_percentage": self.discount_percentage,
            "stock_quantity": self.stock_quantity,
            "in_stock": self.in_stock,
            "image_url": self.image_url,
            "category_id": str(self.category_id) if self.category_id else None,
            "category_name": self.category_name,
            "similarity_score": self.similarity_score,
            "relevance_score": self.relevance_score,
        }


@dataclass
class SemanticSearchResult:
    """Complete search result with metadata."""
    results: List[ProductSearchResult]
    total_count: int
    search_type: SearchType
    query: str
    took_ms: int
    from_cache: bool
    facets: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "search_metadata": {
                "query": self.query,
                "search_type": self.search_type.value,
                "took_ms": self.took_ms,
                "cached": self.from_cache,
            },
            "facets": self.facets,
        }


# ============================================================================
# Semantic Search Service
# ============================================================================

class SemanticSearchService:
    """
    Service for semantic product search.

    Combines:
    - Gemini embeddings for semantic understanding
    - pgvector for efficient similarity search
    - Redis caching for performance
    - Fallback keyword search for resilience
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._embedding_service: Optional[GeminiEmbeddingService] = None

    async def _get_embedding_service(self) -> GeminiEmbeddingService:
        """Get embedding service instance."""
        if self._embedding_service is None:
            self._embedding_service = await get_embedding_service()
        return self._embedding_service

    def _generate_cache_key(
        self,
        query: str,
        filters: SemanticSearchFilters,
        options: SemanticSearchOptions
    ) -> str:
        """Generate deterministic cache key for search."""
        key_data = {
            "q": query.lower().strip(),
            "cat": str(filters.category_id) if filters.category_id else None,
            "min_p": str(filters.min_price) if filters.min_price else None,
            "max_p": str(filters.max_price) if filters.max_price else None,
            "stock": filters.in_stock_only,
            "thresh": filters.similarity_threshold,
            "limit": options.max_results,
            "offset": options.offset,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        hash_value = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        return f"search:semantic:{hash_value}"

    async def _get_cached_results(
        self,
        cache_key: str
    ) -> Optional[SemanticSearchResult]:
        """Retrieve cached search results."""
        try:
            redis = await get_redis()
            if redis is None:
                return None

            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return self._deserialize_search_result(data)

            return None
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
            return None

    async def _cache_results(
        self,
        cache_key: str,
        result: SemanticSearchResult
    ):
        """Cache search results."""
        try:
            redis = await get_redis()
            if redis is None:
                return

            data = self._serialize_search_result(result)
            await redis.setex(
                cache_key,
                SEARCH_RESULTS_CACHE_TTL,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")

    def _serialize_search_result(
        self,
        result: SemanticSearchResult
    ) -> Dict[str, Any]:
        """Serialize search result for caching."""
        return {
            "results": [r.to_dict() for r in result.results],
            "total_count": result.total_count,
            "search_type": result.search_type.value,
            "query": result.query,
            "took_ms": result.took_ms,
            "facets": result.facets,
        }

    def _deserialize_search_result(
        self,
        data: Dict[str, Any]
    ) -> SemanticSearchResult:
        """Deserialize search result from cache."""
        results = []
        for r in data["results"]:
            results.append(ProductSearchResult(
                product_id=UUID(r["product_id"]),
                name=r["name"],
                slug=r["slug"],
                description=r.get("description"),
                short_description=r.get("short_description"),
                price=Decimal(str(r["price"])),
                compare_at_price=Decimal(str(r["compare_at_price"])) if r.get("compare_at_price") else None,
                stock_quantity=r["stock_quantity"],
                image_url=r.get("image_url"),
                category_id=UUID(r["category_id"]) if r.get("category_id") else None,
                category_name=r.get("category_name"),
                similarity_score=r.get("similarity_score"),
                relevance_score=r.get("relevance_score"),
            ))

        return SemanticSearchResult(
            results=results,
            total_count=data["total_count"],
            search_type=SearchType(data["search_type"]),
            query=data["query"],
            took_ms=data["took_ms"],
            from_cache=True,
            facets=data.get("facets"),
        )

    async def _track_popular_query(self, query: str):
        """Track query in popular searches."""
        try:
            redis = await get_redis()
            if redis is None:
                return

            normalized = query.lower().strip()
            await redis.zincrby(POPULAR_QUERIES_KEY, 1, normalized)
            await redis.expire(POPULAR_QUERIES_KEY, POPULAR_QUERIES_TTL)
        except Exception as e:
            logger.debug(f"Popular query tracking error: {e}")

    async def _execute_semantic_search(
        self,
        embedding: List[float],
        filters: SemanticSearchFilters,
        options: SemanticSearchOptions
    ) -> Tuple[List[ProductSearchResult], int]:
        """Execute semantic search using pgvector."""
        # Convert embedding to PostgreSQL vector format
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        # Build the query using the stored procedure
        query = text("""
            SELECT
                product_id,
                name,
                slug,
                description,
                short_description,
                price,
                compare_at_price,
                stock_quantity,
                image_url,
                category_id,
                category_name,
                similarity_score
            FROM semantic_search(
                :embedding::vector(768),
                :threshold,
                :limit,
                :category_id,
                :min_price,
                :max_price,
                :in_stock
            )
            OFFSET :offset
        """)

        params = {
            "embedding": embedding_str,
            "threshold": filters.similarity_threshold,
            "limit": options.max_results + options.offset,  # Get enough for offset
            "category_id": str(filters.category_id) if filters.category_id else None,
            "min_price": float(filters.min_price) if filters.min_price else None,
            "max_price": float(filters.max_price) if filters.max_price else None,
            "in_stock": filters.in_stock_only,
            "offset": options.offset,
        }

        result = await self.db.execute(query, params)
        rows = result.fetchall()

        # Convert to ProductSearchResult objects
        products = []
        for row in rows:
            products.append(ProductSearchResult(
                product_id=row.product_id,
                name=row.name,
                slug=row.slug,
                description=row.description,
                short_description=row.short_description,
                price=row.price,
                compare_at_price=row.compare_at_price,
                stock_quantity=row.stock_quantity,
                image_url=row.image_url,
                category_id=row.category_id,
                category_name=row.category_name,
                similarity_score=row.similarity_score,
                relevance_score=None,
            ))

        # Get total count (simplified - could be optimized)
        count_query = text("""
            SELECT COUNT(*) FROM products
            WHERE is_active = TRUE
            AND embedding IS NOT NULL
            AND (1 - (embedding <=> :embedding::vector(768))) > :threshold
            AND (:category_id IS NULL OR category_id = :category_id::uuid)
            AND (:min_price IS NULL OR price >= :min_price)
            AND (:max_price IS NULL OR price <= :max_price)
            AND (:in_stock = FALSE OR stock_quantity > 0)
        """)

        count_result = await self.db.execute(count_query, params)
        total_count = count_result.scalar() or 0

        return products, total_count

    async def _execute_keyword_search(
        self,
        query: str,
        filters: SemanticSearchFilters,
        options: SemanticSearchOptions
    ) -> Tuple[List[ProductSearchResult], int]:
        """Execute fallback keyword search."""
        # Use the stored procedure for keyword search
        search_query = text("""
            SELECT
                product_id,
                name,
                slug,
                description,
                short_description,
                price,
                compare_at_price,
                stock_quantity,
                image_url,
                category_id,
                category_name,
                relevance_score
            FROM keyword_search_fallback(
                :query,
                :limit,
                :category_id,
                :min_price,
                :max_price,
                :in_stock
            )
            OFFSET :offset
        """)

        params = {
            "query": query,
            "limit": options.max_results + options.offset,
            "category_id": str(filters.category_id) if filters.category_id else None,
            "min_price": float(filters.min_price) if filters.min_price else None,
            "max_price": float(filters.max_price) if filters.max_price else None,
            "in_stock": filters.in_stock_only,
            "offset": options.offset,
        }

        result = await self.db.execute(search_query, params)
        rows = result.fetchall()

        products = []
        for row in rows:
            products.append(ProductSearchResult(
                product_id=row.product_id,
                name=row.name,
                slug=row.slug,
                description=row.description,
                short_description=row.short_description,
                price=row.price,
                compare_at_price=row.compare_at_price,
                stock_quantity=row.stock_quantity,
                image_url=row.image_url,
                category_id=row.category_id,
                category_name=row.category_name,
                similarity_score=None,
                relevance_score=row.relevance_score,
            ))

        # Simplified count for keyword search
        total_count = len(products)

        return products, total_count

    async def _filter_by_branch_inventory(
        self,
        products: List[ProductSearchResult],
        branch_id: UUID,
    ) -> List[ProductSearchResult]:
        """
        Post-filter search results against ``branch_inventory``.

        Removes products that do not have an active, in-stock row in
        ``branch_inventory`` for the given branch.  This ensures that
        even vector-search / keyword-search results honour the strict
        branch-visibility rules.
        """
        if not products:
            return products

        product_ids = [str(p.product_id) for p in products]
        placeholders = ", ".join(f":pid_{i}" for i in range(len(product_ids)))

        filter_query = text(f"""
            SELECT bi.product_id::text
            FROM branch_inventory bi
            WHERE bi.branch_id = :branch_id
              AND bi.is_active = TRUE
              AND bi.stock_quantity > 0
              AND bi.product_id::text IN ({placeholders})
        """)

        params: dict = {"branch_id": str(branch_id)}
        for i, pid in enumerate(product_ids):
            params[f"pid_{i}"] = pid

        result = await self.db.execute(filter_query, params)
        visible_ids = {row[0] for row in result.fetchall()}

        return [p for p in products if str(p.product_id) in visible_ids]

    async def search(
        self,
        query: str,
        filters: Optional[SemanticSearchFilters] = None,
        options: Optional[SemanticSearchOptions] = None,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> SemanticSearchResult:
        """
        Perform semantic product search.

        Args:
            query: Search query (multilingual supported)
            filters: Optional search filters
            options: Optional search options
            user_id: Optional user ID for analytics
            session_id: Optional session ID for analytics

        Returns:
            SemanticSearchResult with products and metadata
        """
        start_time = time.perf_counter()

        # Validate query
        query = query.strip()
        if len(query) < MIN_QUERY_LENGTH:
            raise ValueError(f"Query must be at least {MIN_QUERY_LENGTH} characters")
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query must be at most {MAX_QUERY_LENGTH} characters")

        # Apply defaults
        filters = filters or SemanticSearchFilters()
        options = options or SemanticSearchOptions()

        # Check cache
        cache_key = self._generate_cache_key(query, filters, options)
        cached_result = await self._get_cached_results(cache_key)

        if cached_result:
            logger.info(f"Search cache hit for query: {query[:50]}...")
            if options.track_analytics:
                await self._track_popular_query(query)
            return cached_result

        # Try semantic search
        search_type = SearchType.SEMANTIC
        products = []
        total_count = 0

        try:
            # Generate query embedding
            embedding_service = await self._get_embedding_service()
            embedding, was_cached = await embedding_service.generate_embedding(query)

            logger.info(
                f"Query embedding {'from cache' if was_cached else 'generated'} "
                f"for: {query[:50]}..."
            )

            # Execute semantic search
            products, total_count = await self._execute_semantic_search(
                embedding, filters, options
            )

        except (GeminiAPIError, CircuitOpenError) as e:
            # Fallback to keyword search
            logger.warning(f"Semantic search failed, using keyword fallback: {e}")
            search_type = SearchType.KEYWORD

            products, total_count = await self._execute_keyword_search(
                query, filters, options
            )

        # Branch-inventory post-filter: drop results not visible in the branch
        if filters.branch_id is not None:
            products = await self._filter_by_branch_inventory(
                products, filters.branch_id,
            )
            total_count = len(products)

        # Calculate elapsed time
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Build result
        result = SemanticSearchResult(
            results=products[:options.max_results],
            total_count=total_count,
            search_type=search_type,
            query=query,
            took_ms=elapsed_ms,
            from_cache=False,
            facets=None,  # Could add facet aggregation here
        )

        # Cache results
        await self._cache_results(cache_key, result)

        # Track analytics
        if options.track_analytics:
            await self._track_popular_query(query)
            await self._log_search_analytics(
                query=query,
                search_type=search_type,
                results_count=len(products),
                took_ms=elapsed_ms,
                user_id=user_id,
                session_id=session_id,
                filters=filters,
            )

        logger.info(
            f"Search completed: query='{query[:30]}...', "
            f"type={search_type.value}, results={len(products)}, "
            f"took={elapsed_ms}ms"
        )

        return result

    async def _log_search_analytics(
        self,
        query: str,
        search_type: SearchType,
        results_count: int,
        took_ms: int,
        user_id: Optional[UUID],
        session_id: Optional[str],
        filters: SemanticSearchFilters,
    ):
        """Log search analytics to database."""
        try:
            analytics_query = text("""
                INSERT INTO search_analytics (
                    query, query_normalized, user_id, session_id,
                    results_count, search_type, response_time_ms, filters_used
                ) VALUES (
                    :query, :query_normalized, :user_id, :session_id,
                    :results_count, :search_type, :response_time_ms, :filters_used
                )
            """)

            await self.db.execute(analytics_query, {
                "query": query,
                "query_normalized": query.lower().strip(),
                "user_id": str(user_id) if user_id else None,
                "session_id": session_id,
                "results_count": results_count,
                "search_type": search_type.value,
                "response_time_ms": took_ms,
                "filters_used": json.dumps({
                    "category_id": str(filters.category_id) if filters.category_id else None,
                    "min_price": str(filters.min_price) if filters.min_price else None,
                    "max_price": str(filters.max_price) if filters.max_price else None,
                    "in_stock_only": filters.in_stock_only,
                }),
            })
            await self.db.commit()
        except Exception as e:
            logger.debug(f"Search analytics logging error: {e}")

    async def get_popular_searches(
        self,
        limit: int = 10
    ) -> List[Tuple[str, int]]:
        """Get popular search queries."""
        try:
            redis = await get_redis()
            if redis is None:
                return []

            results = await redis.zrevrange(
                POPULAR_QUERIES_KEY,
                0,
                limit - 1,
                withscores=True
            )

            return [(query.decode() if isinstance(query, bytes) else query, int(score))
                    for query, score in results]
        except Exception as e:
            logger.warning(f"Error getting popular searches: {e}")
            return []

    async def get_search_suggestions(
        self,
        partial_query: str,
        limit: int = 5
    ) -> List[str]:
        """Get autocomplete suggestions based on popular searches."""
        if len(partial_query) < 2:
            return []

        popular = await self.get_popular_searches(limit=50)
        partial_lower = partial_query.lower()

        suggestions = [
            query for query, _ in popular
            if query.startswith(partial_lower) and query != partial_lower
        ]

        return suggestions[:limit]


# ============================================================================
# Factory Function
# ============================================================================

def get_semantic_search_service(db: AsyncSession) -> SemanticSearchService:
    """Create a new semantic search service instance."""
    return SemanticSearchService(db)
