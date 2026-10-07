"""
Security middleware for rate limiting, input sanitization, and request validation.
"""

import re
import time
from urllib.parse import urlparse
from typing import Callable
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using a sliding window algorithm.
    
    Limits requests per IP address within a time window.
    """
    
    def __init__(self, app, requests_limit: int = None, window_seconds: int = None):
        super().__init__(app)
        self.requests_limit = requests_limit or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_period
        
        # Store request timestamps per IP
        # In production, use Redis for distributed rate limiting
        self.request_counts = defaultdict(list)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check for forwarded header (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_requests(self, ip: str, current_time: float):
        """Remove request timestamps outside the current window."""
        cutoff = current_time - self.window_seconds
        self.request_counts[ip] = [
            ts for ts in self.request_counts[ip] if ts > cutoff
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and apply rate limiting."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Cleanup old requests
        self._cleanup_old_requests(client_ip, current_time)
        
        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.requests_limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": self.window_seconds
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.requests_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_seconds))
                }
            )
        
        # Record this request
        self.request_counts[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.requests_limit - len(self.request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict Transport Security (HTTPS only)
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy. Public Supabase images are served from the
        # project's CDN origin; all other third-party access remains blocked.
        connect_sources = "'self' http://localhost:8000" if settings.debug else "'self'"
        image_sources = "'self' data: blob:"
        if (
            settings.storage_backend == "supabase"
            and settings.supabase_storage_public
            and settings.supabase_url
        ):
            parsed_supabase_url = urlparse(settings.supabase_url)
            supabase_origin = f"{parsed_supabase_url.scheme}://{parsed_supabase_url.netloc}"
            image_sources = f"{image_sources} {supabase_origin}"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            f"img-src {image_sources}; "
            f"connect-src {connect_sources}; "
            "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy - allow geolocation for location feature
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"
        
        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for basic input sanitization.
    
    Checks for common attack patterns in request data.
    """
    
    # Patterns that might indicate malicious input
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>",           # Script tags
        r"javascript:",              # JavaScript protocol
        r"on\w+\s*=",               # Event handlers
        r"data:text/html",          # Data URLs with HTML
        r"\.\./",                   # Path traversal
        r";\s*--",                  # SQL comment
        r"'\s*or\s*'",              # SQL injection
        r"union\s+select",          # SQL injection
        r"\$\{.*\}",                # Template injection
        r"\{\{.*\}\}",              # Template injection
    ]
    
    def __init__(self, app):
        super().__init__(app)
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS]
    
    def _check_value(self, value: str) -> bool:
        """Check if a string value contains dangerous patterns."""
        if not isinstance(value, str):
            return True
        
        for pattern in self.patterns:
            if pattern.search(value):
                return False
        
        return True
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check query parameters
        for key, value in request.query_params.items():
            if not self._check_value(value):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": f"Invalid characters in query parameter: {key}"}
                )
        
        # Check path parameters
        for key, value in request.path_params.items():
            if isinstance(value, str) and not self._check_value(value):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": f"Invalid characters in path parameter: {key}"}
                )
        
        return await call_next(request)


def validate_file_upload(
    content_type: str,
    file_size: int,
    filename: str
) -> tuple[bool, str]:
    """
    Validate an uploaded file.
    
    Args:
        content_type: MIME type of the file
        file_size: Size in bytes
        filename: Original filename
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check content type
    if content_type not in settings.allowed_image_types_list:
        return False, f"Invalid file type: {content_type}"
    
    # Check file size
    if file_size > settings.max_image_size_bytes:
        return False, f"File too large. Maximum: {settings.max_image_size_mb}MB"
    
    # Check filename for path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return False, "Invalid filename"
    
    # Check file extension matches content type
    extension_map = {
        "image/jpeg": [".jpg", ".jpeg"],
        "image/png": [".png"],
        "image/webp": [".webp"],
    }
    
    expected_extensions = extension_map.get(content_type, [])
    file_ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if expected_extensions and file_ext not in expected_extensions:
        return False, "File extension doesn't match content type"
    
    return True, ""


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other issues.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.replace("\\", "/").split("/")[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + ("." + ext if ext else "")
    
    return filename or "unnamed"
