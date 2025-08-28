"""HTTP client utilities and factories."""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
from urllib.parse import urljoin


logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for HTTP retry behavior."""
    
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_on_status: List[int] = None
    retry_on_exceptions: List[type] = None
    
    def __post_init__(self):
        if self.retry_on_status is None:
            self.retry_on_status = [429, 502, 503, 504]
        
        if self.retry_on_exceptions is None:
            self.retry_on_exceptions = [
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.NetworkError
            ]


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: int = 60
    expected_exception: type = Exception


class CircuitBreaker:
    """Circuit breaker for HTTP requests."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if request execution is allowed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful execution."""
        self.failure_count = 0
        
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = "CLOSED"
                self.success_count = 0
        
        logger.debug(f"Circuit breaker success recorded, state: {self.state}")
    
    def record_failure(self, exception: Exception):
        """Record failed execution."""
        if isinstance(exception, self.config.expected_exception):
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = "OPEN"
                self.success_count = 0
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.now() - self.last_failure_time).seconds >= self.config.timeout


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: float, burst: int = None):
        self.rate = rate  # tokens per second
        self.burst = burst or max(1, int(rate))  # burst size
        self.tokens = self.burst
        self.last_update = datetime.now()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket."""
        async with self._lock:
            now = datetime.now()
            time_passed = (now - self.last_update).total_seconds()
            
            # Add tokens based on time passed
            self.tokens = min(self.burst, self.tokens + time_passed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """Wait until tokens are available."""
        while not await self.acquire(tokens):
            wait_time = tokens / self.rate
            await asyncio.sleep(min(wait_time, 1.0))  # Cap wait time


class RetryClient:
    """HTTP client with retry and circuit breaker capabilities."""
    
    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        retry_config: RetryConfig = None,
        circuit_breaker_config: CircuitBreakerConfig = None,
        rate_limiter: RateLimiter = None,
        default_headers: Dict[str, str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.retry_config = retry_config or RetryConfig()
        self.rate_limiter = rate_limiter
        self.default_headers = default_headers or {}
        
        # Setup circuit breaker
        self.circuit_breaker = None
        if circuit_breaker_config:
            self.circuit_breaker = CircuitBreaker(circuit_breaker_config)
        
        # Setup HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None,
        data: Any = None,
        files: Dict[str, Any] = None,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry and circuit breaker."""
        
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            raise httpx.RequestError("Circuit breaker is open")
        
        # Apply rate limiting
        if self.rate_limiter:
            await self.rate_limiter.wait_for_tokens()
        
        # Build full URL
        full_url = urljoin(self.base_url + "/", url.lstrip("/")) if self.base_url else url
        
        # Merge headers
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        # Retry loop
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=full_url,
                    headers=request_headers,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                    **kwargs
                )
                
                # Check if we should retry based on status code
                if response.status_code in self.retry_config.retry_on_status:
                    if attempt < self.retry_config.max_retries:
                        await self._wait_for_retry(attempt)
                        continue
                
                # Success - record in circuit breaker
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                
                return response
                
            except Exception as e:
                last_exception = e
                
                # Record failure in circuit breaker
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure(e)
                
                # Check if we should retry this exception
                should_retry = any(
                    isinstance(e, exc_type) 
                    for exc_type in self.retry_config.retry_on_exceptions
                )
                
                if should_retry and attempt < self.retry_config.max_retries:
                    await self._wait_for_retry(attempt)
                    continue
                
                # No more retries, re-raise
                raise
        
        # All retries exhausted
        raise last_exception
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request.""" 
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """Make PATCH request."""
        return await self.request("PATCH", url, **kwargs)
    
    async def _wait_for_retry(self, attempt: int) -> None:
        """Wait before retry with exponential backoff."""
        delay = min(
            self.retry_config.initial_delay * (self.retry_config.backoff_factor ** attempt),
            self.retry_config.max_delay
        )
        
        # Add jitter if enabled
        if self.retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        logger.debug(f"Retrying request in {delay:.2f}s (attempt {attempt + 1})")
        await asyncio.sleep(delay)


class HttpClientFactory:
    """Factory for creating HTTP clients with common configurations."""
    
    @staticmethod
    def create_onshape_client(
        base_url: str,
        timeout: float = 30.0,
        rate_limit_per_second: float = 10.0
    ) -> RetryClient:
        """Create HTTP client configured for Onshape API."""
        
        retry_config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            backoff_factor=2.0,
            retry_on_status=[429, 502, 503, 504],
            retry_on_exceptions=[
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.NetworkError
            ]
        )
        
        circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=3,
            timeout=60
        )
        
        rate_limiter = RateLimiter(rate=rate_limit_per_second, burst=int(rate_limit_per_second * 2))
        
        default_headers = {
            "User-Agent": "DesignAssistant/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        return RetryClient(
            base_url=base_url,
            timeout=timeout,
            retry_config=retry_config,
            circuit_breaker_config=circuit_breaker_config,
            rate_limiter=rate_limiter,
            default_headers=default_headers
        )
    
    @staticmethod
    def create_webhook_client(timeout: float = 10.0) -> RetryClient:
        """Create HTTP client for webhook notifications."""
        
        retry_config = RetryConfig(
            max_retries=2,
            initial_delay=0.5,
            backoff_factor=2.0,
            retry_on_status=[502, 503, 504],  # Don't retry 429 for webhooks
            retry_on_exceptions=[
                httpx.ConnectTimeout,
                httpx.NetworkError
            ]
        )
        
        default_headers = {
            "User-Agent": "DesignAssistant-Webhook/1.0",
            "Content-Type": "application/json"
        }
        
        return RetryClient(
            timeout=timeout,
            retry_config=retry_config,
            default_headers=default_headers
        )
    
    @staticmethod
    def create_basic_client(
        base_url: str = "",
        timeout: float = 30.0,
        headers: Dict[str, str] = None
    ) -> RetryClient:
        """Create basic HTTP client with minimal configuration."""
        
        return RetryClient(
            base_url=base_url,
            timeout=timeout,
            default_headers=headers or {}
        )


class RequestLoggingMiddleware:
    """Middleware for logging HTTP requests and responses."""
    
    def __init__(self, client: RetryClient, log_level: int = logging.DEBUG):
        self.client = client
        self.log_level = log_level
        self.logger = logging.getLogger(f"{__name__}.requests")
    
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make request with logging."""
        start_time = datetime.now()
        
        # Log request
        self.logger.log(self.log_level, f"→ {method} {url}")
        
        try:
            response = await self.client.request(method, url, **kwargs)
            
            # Log response
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log(
                self.log_level,
                f"← {response.status_code} {method} {url} ({duration:.3f}s)"
            )
            
            return response
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.log(
                logging.WARNING,
                f"✗ {method} {url} failed after {duration:.3f}s: {e}"
            )
            raise