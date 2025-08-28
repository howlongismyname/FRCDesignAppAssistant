"""Main FastAPI application entry point for Design Assistant."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .infrastructure.config import get_config
from .infrastructure.logging import setup_logging
from .interfaces.api import create_design_assistant_router
from .interfaces.middleware import (
    RequestLoggingMiddleware, AuthMiddleware, RateLimitMiddleware,
    SecurityHeadersMiddleware
)
from .interfaces.dependencies import cleanup_dependencies


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    config = get_config()
    
    # Setup logging
    setup_logging(config.logging)
    
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed", errors=errors)
        raise RuntimeError(f"Configuration errors: {', '.join(errors)}")
    
    logger.info("Design Assistant started successfully")
    
    yield
    
    # Shutdown
    await cleanup_dependencies()
    logger.info("Design Assistant shutdown completed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    config = get_config()
    
    # Create FastAPI app
    app = FastAPI(
        title="Design Assistant API",
        description="API for FRC Design Assistant - BOM analysis, thumbnails, and fabrication packages",
        version="1.0.0",
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None,
        lifespan=lifespan
    )
    
    # Add middleware
    if config.security.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.security.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"]
        )
    
    # Custom middleware (order matters - last added is executed first)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=config.security.rate_limit_per_minute)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add routers
    app.include_router(create_design_assistant_router())
    
    # Health check endpoint (no auth required)
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "service": "design-assistant",
            "version": "1.0.0"
        }
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.logging.level.lower(),
        access_log=True
    )