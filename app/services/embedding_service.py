"""
SRIBEESonline - Gemini Embedding Service

Generates text embeddings using Google's Gemini API (text-embedding-004).
Supports multilingual input (English, Sinhala, Tamil, Singlish).

Features:
- Async embedding generation
- Batch processing for bulk operations
- Circuit breaker pattern for fault tolerance
- Embedding caching in Redis
"""
import asyncio
import hashlib
import json
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, List, Optional, Tuple

import httpx
from loguru import logger

from app.config.settings import settings
from app.config.redis import get_redis


# ============================================================================
# Configuration
# ============================================================================

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_EMBEDDING_MODEL = "text-embedding-004"
GEMINI_EMBEDDING_DIMENSION = 768

# Rate limiting and retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 10.0
REQUEST_TIMEOUT = 30.0

# Batch processing
BATCH_SIZE = 100
BATCH_DELAY_SECONDS = 0.1  # Delay between batch items to respect rate limits

# Cache configuration
EMBEDDING_CACHE_TTL = 86400  # 24 hours


# ============================================================================
# Circuit Breaker State Management
# ============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # API failing, use fallback
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerState:
    """Circuit breaker state container."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    success_count_in_half_open: int = 0


class GeminiCircuitBreaker:
    """
    Circuit breaker for Gemini API calls.
    
    Prevents cascading failures when the API is down by failing fast
    and periodically testing if the API has recovered.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()
    
    @property
    def is_closed(self) -> bool:
        return self._state.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self._state.state == CircuitState.OPEN
    
    async def can_execute(self) -> bool:
        """Check if a request can proceed."""
        async with self._lock:
            if self._state.state == CircuitState.CLOSED:
                return True
            
            if self._state.state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if self._state.last_failure_time:
                    elapsed = datetime.utcnow() - self._state.last_failure_time
                    if elapsed.total_seconds() > self.recovery_timeout:
                        self._state.state = CircuitState.HALF_OPEN
                        self._state.success_count_in_half_open = 0
                        logger.info("Circuit breaker transitioning to HALF_OPEN")
                        return True
                return False
            
            # HALF_OPEN state: allow limited requests
            return True
    
    async def record_success(self):
        """Record a successful API call."""
        async with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count_in_half_open += 1
                if self._state.success_count_in_half_open >= self.half_open_max_requests:
                    self._state.state = CircuitState.CLOSED
                    self._state.failure_count = 0
                    logger.info("Circuit breaker CLOSED - API recovered")
            else:
                self._state.failure_count = 0
    
    async def record_failure(self):
        """Record a failed API call."""
        async with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = datetime.utcnow()
            
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.state = CircuitState.OPEN
                logger.warning("Circuit breaker OPEN - API still failing")
            elif self._state.failure_count >= self.failure_threshold:
                self._state.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker OPEN - {self._state.failure_count} failures"
                )


# ============================================================================
# Embedding Service
# ============================================================================

class GeminiEmbeddingService:
    """
    Service for generating text embeddings using Google's Gemini API.
    
    Handles:
    - Text preprocessing and normalization
    - Async API calls with retries
    - Caching embeddings in Redis
    - Circuit breaker for fault tolerance
    - Batch processing for bulk operations
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'gemini_api_key', None)
        self.model = GEMINI_EMBEDDING_MODEL
        self.dimension = GEMINI_EMBEDDING_DIMENSION
        self.circuit_breaker = GeminiCircuitBreaker()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for embedding generation.
        
        - Normalize Unicode (NFC form for consistent encoding)
        - Handle mixed-script queries (English/Sinhala/Tamil)
        - Remove excessive whitespace
        - Truncate to model limit
        """
        if not text:
            return ""
        
        # Normalize to NFC (canonical composition)
        normalized = unicodedata.normalize('NFC', text)
        
        # Remove control characters except newlines/tabs
        cleaned = ''.join(
            char for char in normalized 
            if unicodedata.category(char) != 'Cc' or char in '\n\t'
        )
        
        # Collapse multiple whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Truncate to Gemini's limit (2048 tokens ≈ 8000 chars for safety)
        max_chars = 8000
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars]
        
        return cleaned.strip()
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for embedding."""
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
        return f"embedding:{self.model}:{text_hash}"
    
    async def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Retrieve cached embedding from Redis."""
        try:
            redis = await get_redis()
            if redis is None:
                return None
            
            cache_key = self._get_cache_key(text)
            cached = await redis.get(cache_key)
            
            if cached:
                logger.debug(f"Embedding cache hit for key: {cache_key[:20]}...")
                return json.loads(cached)
            
            return None
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
            return None
    
    async def _cache_embedding(self, text: str, embedding: List[float]):
        """Store embedding in Redis cache."""
        try:
            redis = await get_redis()
            if redis is None:
                return
            
            cache_key = self._get_cache_key(text)
            await redis.setex(
                cache_key,
                EMBEDDING_CACHE_TTL,
                json.dumps(embedding)
            )
            logger.debug(f"Cached embedding for key: {cache_key[:20]}...")
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    async def _call_gemini_api(self, text: str) -> List[float]:
        """
        Call Gemini API to generate embedding.
        
        Raises:
            GeminiAPIError: If API call fails after retries
        """
        if not self.api_key:
            raise GeminiAPIError("GEMINI_API_KEY not configured")
        
        url = f"{GEMINI_API_BASE_URL}/models/{self.model}:embedContent"
        
        payload = {
            "model": f"models/{self.model}",
            "content": {
                "parts": [{"text": text}]
            }
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # Add API key as query parameter
        params = {"key": self.api_key}
        
        client = await self._get_client()
        
        last_exception = None
        delay = INITIAL_RETRY_DELAY
        
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding", {}).get("values", [])
                    
                    if len(embedding) != self.dimension:
                        raise GeminiAPIError(
                            f"Unexpected embedding dimension: {len(embedding)}"
                        )
                    
                    return embedding
                
                # Handle retryable errors
                if response.status_code in (429, 500, 502, 503, 504):
                    error_msg = response.text
                    logger.warning(
                        f"Gemini API error (attempt {attempt + 1}/{MAX_RETRIES}): "
                        f"{response.status_code} - {error_msg[:100]}"
                    )
                    last_exception = GeminiAPIError(
                        f"API returned {response.status_code}",
                        status_code=response.status_code,
                        retryable=True
                    )
                else:
                    # Non-retryable error
                    error_msg = response.text
                    raise GeminiAPIError(
                        f"API returned {response.status_code}: {error_msg[:200]}",
                        status_code=response.status_code,
                        retryable=False
                    )
                    
            except httpx.TimeoutException as e:
                logger.warning(f"Gemini API timeout (attempt {attempt + 1}): {e}")
                last_exception = GeminiAPIError(
                    "Request timeout", 
                    retryable=True
                )
            except httpx.RequestError as e:
                logger.warning(f"Gemini API request error (attempt {attempt + 1}): {e}")
                last_exception = GeminiAPIError(
                    f"Request error: {str(e)}", 
                    retryable=True
                )
            
            # Exponential backoff with jitter
            if attempt < MAX_RETRIES - 1:
                jitter = delay * 0.1 * (2 * asyncio.get_event_loop().time() % 1 - 1)
                await asyncio.sleep(delay + jitter)
                delay = min(delay * 2, MAX_RETRY_DELAY)
        
        # All retries exhausted
        raise last_exception or GeminiAPIError("Unknown error after retries")
    
    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> Tuple[List[float], bool]:
        """
        Generate embedding for the given text.
        
        Args:
            text: Input text (can be multilingual)
            use_cache: Whether to use Redis cache
            
        Returns:
            Tuple of (embedding vector, was_cached)
            
        Raises:
            GeminiAPIError: If embedding generation fails
            CircuitOpenError: If circuit breaker is open
        """
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        if not processed_text:
            raise ValueError("Empty text after preprocessing")
        
        # Check cache first
        if use_cache:
            cached = await self._get_cached_embedding(processed_text)
            if cached:
                return cached, True
        
        # Check circuit breaker
        if not await self.circuit_breaker.can_execute():
            raise CircuitOpenError(
                "Circuit breaker is open - Gemini API unavailable"
            )
        
        try:
            # Call API
            start_time = time.perf_counter()
            embedding = await self._call_gemini_api(processed_text)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            logger.info(f"Generated embedding in {elapsed_ms:.1f}ms")
            
            # Record success and cache
            await self.circuit_breaker.record_success()
            
            if use_cache:
                await self._cache_embedding(processed_text, embedding)
            
            return embedding, False
            
        except GeminiAPIError as e:
            if e.retryable:
                await self.circuit_breaker.record_failure()
            raise
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
        on_progress: Optional[callable] = None
    ) -> List[Tuple[Optional[List[float]], Optional[Exception]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            use_cache: Whether to use Redis cache
            on_progress: Optional callback(processed, total) for progress updates
            
        Returns:
            List of (embedding, error) tuples for each input text
        """
        results = []
        total = len(texts)
        
        for i, text in enumerate(texts):
            try:
                embedding, _ = await self.generate_embedding(text, use_cache)
                results.append((embedding, None))
            except Exception as e:
                logger.error(f"Batch embedding error for text {i}: {e}")
                results.append((None, e))
            
            # Progress callback
            if on_progress:
                on_progress(i + 1, total)
            
            # Small delay to respect rate limits
            if i < total - 1:
                await asyncio.sleep(BATCH_DELAY_SECONDS)
        
        return results
    
    async def generate_product_embedding(
        self,
        name: str,
        description: Optional[str] = None,
        short_description: Optional[str] = None,
        category_name: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> Tuple[List[float], bool]:
        """
        Generate embedding for a product using combined text fields.
        
        Args:
            name: Product name
            description: Full description
            short_description: Brief description
            category_name: Category for context
            keywords: Additional keywords
            
        Returns:
            Tuple of (embedding vector, was_cached)
        """
        # Combine product fields into searchable text
        parts = [name]
        
        if short_description:
            parts.append(short_description)
        
        if description:
            # Truncate long descriptions
            parts.append(description[:500])
        
        if category_name:
            parts.append(f"Category: {category_name}")
        
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}")
        
        combined_text = " | ".join(parts)
        
        return await self.generate_embedding(combined_text)


# ============================================================================
# Custom Exceptions
# ============================================================================

class GeminiAPIError(Exception):
    """Exception raised for Gemini API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class CircuitOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# ============================================================================
# Singleton Instance
# ============================================================================

_embedding_service: Optional[GeminiEmbeddingService] = None


async def get_embedding_service() -> GeminiEmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = GeminiEmbeddingService()
    return _embedding_service


async def close_embedding_service():
    """Close the embedding service and release resources."""
    global _embedding_service
    if _embedding_service:
        await _embedding_service.close()
        _embedding_service = None
