# Multi-stage Dockerfile for Stock Tracker

# =============================================================================
# Stage 1: Base Image with Python and System Dependencies
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# =============================================================================
# Stage 2: Dependencies Installation
# =============================================================================
FROM base as dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 3: Development Image
# =============================================================================
FROM dependencies as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-mock \
    black \
    mypy \
    flake8 \
    ipdb

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to app user
USER appuser

# Expose ports
EXPOSE 8000

# Default command (can be overridden)
CMD ["uvicorn", "stock_tracker.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Stage 4: Production Image
# =============================================================================
FROM dependencies as production

# Copy application code
COPY --chown=appuser:appuser . .

# Create logs directory
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# Switch to app user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "stock_tracker.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# Stage 5: Testing Image
# =============================================================================
FROM development as testing

# Copy test configuration
COPY pytest.ini .
COPY .coveragerc .

# Run tests
CMD ["pytest", "-v", "--cov=stock_tracker", "--cov-report=html", "--cov-report=term"]
