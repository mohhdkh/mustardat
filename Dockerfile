# Lost & Found Backend Dockerfile
# Multi-stage build for optimized image size

# ===========================================
# Stage 1: Builder - Install dependencies
# ===========================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.production.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.production.txt


# ===========================================
# Stage 2: Runtime - Production image
# ===========================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies and health-check tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Create data directories
RUN mkdir -p /app/data/uploads && chown -R appuser:appuser /app/data

# Copy application code
COPY --chown=appuser:appuser app/ /app/app/
COPY --chown=appuser:appuser frontend/ /app/frontend/
COPY --chown=appuser:appuser alembic/ /app/alembic/
COPY --chown=appuser:appuser alembic.ini /app/

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    DEBUG=false \
    ENVIRONMENT=production \
    DATABASE_PATH=/app/data/mustardat.db \
    UPLOAD_DIR=/app/data/uploads \
    PATH="/home/appuser/.local/bin:$PATH"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD-SHELL curl -f "http://localhost:${PORT:-8000}/health" || exit 1

# Run the application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
