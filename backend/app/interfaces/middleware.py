"""Middleware for the Design Assistant API."""

import time
import uuid
import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..infrastructure.config import get_config
from ..infrastructure.auth import AuthManager, AuthenticationError, AuthorizationError
from ..infrastructure.logging import RequestContext, get_logger
from .schemas import ErrorResponse


logger = get_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    def __init__(self, app, log_level: int = logging.INFO):
        super().__init__(app)
        self.log_level = log_level
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract user ID from auth headers if available
        user_id = None
        if hasattr(request.state, "auth_data") and request.state.auth_data:
            user_id = request.state.auth_data.get("user_id")
        
        start_time = time.time()
        
        with RequestContext(request_id, user_id):
            # Log incoming request
            logger.log(
                self.log_level,
                f"→ {request.method} {request.url.path}",
                method=request.method,
                path=request.url.path,
                query_params=str(request.query_params),
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            
            try:
                # Process request
                response = await call_next(request)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log response
                logger.log(
                    self.log_level,
                    f"← {response.status_code} {request.method} {request.url.path}",
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    content_length=response.headers.get("content-length")
                )
                
                # Add request ID to response headers
                response.headers["X-Request-ID"] = request_id
                
                return response
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                logger.error(
                    f"✗ {request.method} {request.url.path} failed",
                    error=str(e),
                    duration_ms=duration_ms,
                    exc_info=True
                )
                
                # Return error response
                error_response = ErrorResponse(
                    error="InternalServerError",
                    message="An unexpected error occurred",
                    request_id=request_id,
                    status_code=500
                )
                
                return JSONResponse(
                    status_code=500,
                    content=error_response.dict(),
                    headers={"X-Request-ID": request_id}
                )


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and authorization."""
    
    def __init__(self, app):
        super().__init__(app)
        self.auth_manager = None
        self.public_paths = {
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authentication."""
        
        # Initialize auth manager if needed
        if self.auth_manager is None:
            config = get_config()
            self.auth_manager = AuthManager(config.security)
        
        # Skip auth for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Extract and validate authentication
        authorization_header = request.headers.get("authorization")
        
        if not authorization_header:
            return self._unauthorized_response("Missing authorization header")
        
        try:
            auth_data = self.auth_manager.authenticate_request(authorization_header)
            
            if not auth_data:
                return self._unauthorized_response("Invalid credentials")
            
            # Store auth data in request state
            request.state.auth_data = auth_data
            
            return await call_next(request)
            
        except AuthenticationError as e:
            return self._unauthorized_response(str(e))
        except AuthorizationError as e:
            return self._forbidden_response(str(e))
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            return self._server_error_response("Authentication failed")
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """Return 401 Unauthorized response."""
        error_response = ErrorResponse(
            error="Unauthorized",
            message=message,
            status_code=401
        )
        
        return JSONResponse(
            status_code=401,
            content=error_response.dict(),
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    def _forbidden_response(self, message: str) -> JSONResponse:
        """Return 403 Forbidden response."""
        error_response = ErrorResponse(
            error="Forbidden",
            message=message,
            status_code=403
        )
        
        return JSONResponse(
            status_code=403,
            content=error_response.dict()
        )
    
    def _server_error_response(self, message: str) -> JSONResponse:
        """Return 500 Internal Server Error response."""
        error_response = ErrorResponse(
            error="InternalServerError",
            message=message,
            status_code=500
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.dict()
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests: Dict[str, Dict[str, Any]] = {}
        self.window_size = 60  # 1 minute
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        
        # Get client identifier (IP address or user ID)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self._is_request_allowed(client_id):
            return self._rate_limit_response()
        
        # Record request
        self._record_request(client_id)
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to use authenticated user ID first
        if hasattr(request.state, "auth_data") and request.state.auth_data:
            user_id = request.state.auth_data.get("user_id")
            if user_id:
                return f"user:{user_id}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _is_request_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client."""
        now = time.time()
        
        if client_id not in self.client_requests:
            return True
        
        client_data = self.client_requests[client_id]
        
        # Clean old requests outside window
        client_data["requests"] = [
            req_time for req_time in client_data["requests"]
            if now - req_time < self.window_size
        ]
        
        # Check if under limit
        return len(client_data["requests"]) < self.requests_per_minute
    
    def _record_request(self, client_id: str) -> None:
        """Record request timestamp for client."""
        now = time.time()
        
        if client_id not in self.client_requests:
            self.client_requests[client_id] = {"requests": []}
        
        self.client_requests[client_id]["requests"].append(now)
    
    def _rate_limit_response(self) -> JSONResponse:
        """Return 429 Too Many Requests response."""
        error_response = ErrorResponse(
            error="TooManyRequests",
            message="Rate limit exceeded. Please try again later.",
            status_code=429
        )
        
        return JSONResponse(
            status_code=429,
            content=error_response.dict(),
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Window": str(self.window_size)
            }
        )


class CORSMiddleware(BaseHTTPMiddleware):
    """Middleware for CORS headers."""
    
    def __init__(self, app, allowed_origins: list = None, allowed_methods: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = [
            "accept",
            "accept-language", 
            "content-language",
            "content-type",
            "authorization",
            "x-requested-with"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with CORS headers."""
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._preflight_response(request)
        
        # Process normal request
        response = await call_next(request)
        
        # Add CORS headers
        self._add_cors_headers(request, response)
        
        return response
    
    def _preflight_response(self, request: Request) -> Response:
        """Handle CORS preflight request."""
        response = Response()
        self._add_cors_headers(request, response)
        return response
    
    def _add_cors_headers(self, request: Request, response: Response) -> None:
        """Add CORS headers to response."""
        origin = request.headers.get("origin")
        
        if origin and (self.allowed_origins == ["*"] or origin in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif self.allowed_origins == ["*"]:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
        response.headers["Access-Control-Max-Age"] = "3600"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security headers."""
        
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (adjust as needed)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'"
        )
        
        return response


class ResponseCompressionMiddleware(BaseHTTPMiddleware):
    """Middleware for response compression (placeholder)."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with response compression."""
        # This is a placeholder - actual compression would be handled
        # by the web server (nginx, Apache) or a dedicated compression library
        
        response = await call_next(request)
        
        # Could add compression logic here if needed
        return response