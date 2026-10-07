"""
Lost & Found Image-Matching System - Main Application

FastAPI application entry point with all routes, middleware, and lifecycle events.
"""

from contextlib import asynccontextmanager
import mimetypes
import os

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.database import init_db, close_db
from app.services.storage import storage_service, StorageError
from app.api.routes import (
    users_router,
    auth_router,
    items_router,
    matches_router,
    notifications_router,
    recovery_router,
)
from app.middleware.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    InputSanitizationMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database, load ML models
    - Shutdown: Close database connections
    """
    # Startup
    print("Starting Mustardat Backend...")
    
    # Initialize database
    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

    # Validate or create the remote image bucket before serving requests.
    try:
        await storage_service.ensure_ready()
        print(f"Image storage ready ({settings.storage_backend})")
    except StorageError as e:
        print(f"Image storage initialization failed: {e}")
        raise
    
    # Pre-load ML models (optional, can be lazy-loaded)
    if not settings.debug:
        try:
            from app.services.image_processing import image_processor
            # Trigger lazy loading
            _ = image_processor.yolo_model
            _ = image_processor.clip_model
            print("ML models loaded successfully")
        except Exception as e:
            print(f"ML model loading failed: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down Mustardat Backend...")
    await close_db()
    print("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="مستردات - نظام مطابقة المفقودات",
    description="""
    A backend system for matching lost and found items using image processing 
    and vector similarity search.
    
    ## Features
    
    - **Item Management**: Create and manage lost/found item listings
    - **Image Processing**: YOLO detection, CLIP embeddings, pHash, ORB descriptors
    - **Smart Matching**: Vector similarity search with multi-signal re-ranking
    - **Privacy Protection**: Contact info revealed only after mutual confirmation
    
    ## Authentication
    
    All endpoints (except user registration and login) require JWT authentication.
    Include the token in the Authorization header: `Bearer <token>`
    """,
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# ===========================================
# Middleware (order matters - last added runs first)
# ===========================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Input sanitization
app.add_middleware(InputSanitizationMiddleware)

# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_period,
)


# ===========================================
# Exception Handlers
# ===========================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with cleaner messages."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    # Log the error (in production, use proper logging)
    print(f"Unhandled error: {exc}")
    
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred"}
    )


# ===========================================
# API Routes
# ===========================================

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment,
        "commit": os.getenv("RENDER_GIT_COMMIT", "local")[:7],
    }


# API v1 routes
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(items_router, prefix=settings.api_v1_prefix)
app.include_router(matches_router, prefix=settings.api_v1_prefix)
app.include_router(notifications_router, prefix=settings.api_v1_prefix)
app.include_router(recovery_router, prefix=settings.api_v1_prefix)

# Uploaded images keep the same URL shape for both backends. Public Supabase
# buckets redirect to its CDN; private buckets are streamed through the API.
if storage_service.is_remote:
    @app.get("/uploads/{relative_path:path}", include_in_schema=False)
    async def uploaded_image(relative_path: str):
        if storage_service.public_bucket:
            return RedirectResponse(
                storage_service.get_file_url(relative_path),
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            )
        try:
            content = await storage_service.download_image(relative_path)
        except StorageError:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        content_type = mimetypes.guess_type(relative_path)[0] or "application/octet-stream"
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
else:
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

# Frontend static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ===========================================
# Root endpoint
# ===========================================

@app.get("/", tags=["Root"])
async def root():
    """
    Serve the frontend index.html.
    """
    index_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "name": "مستردات",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health",
        "api_prefix": settings.api_v1_prefix
    }


@app.get("/api", tags=["Root"])
async def api_info():
    """
    API information endpoint.
    """
    return {
        "name": "مستردات",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health",
        "api_prefix": settings.api_v1_prefix
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1 if settings.debug else 4,
    )
