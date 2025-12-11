"""
FastAPI application entry point for multi-tenant Stock Tracker.
"""

# Load environment variables FIRST before any other imports
from pathlib import Path
from dotenv import load_dotenv

# Try to find .env file in project root
current_file = Path(__file__)
project_root = current_file.parent.parent.parent.parent  # src/stock_tracker/api/main.py -> root
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from stock_tracker.api.routes import auth, tenants, products, health, analytics, sheets, admin
from stock_tracker.api.middleware.tenant_context import TenantContextMiddleware
from stock_tracker.api.middleware.error_handler import ErrorHandlerMiddleware
from stock_tracker.api.middleware.rate_limiter import RateLimitMiddleware
from stock_tracker.monitoring import (
    MetricsMiddleware,
    setup_sentry,
    get_metrics,
)
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Starting Stock Tracker API...")
    
    # Startup tasks
    # Initialize Sentry for error tracking
    setup_sentry(
        environment=os.getenv("ENVIRONMENT", "development"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
    )
    logger.info("✅ Sentry initialized")
    
    # Initialize metrics
    metrics = get_metrics()
    logger.info("✅ Prometheus metrics initialized")
    
    logger.info("✅ API started successfully")
    
    yield
    
    # Shutdown tasks
    logger.info("🛑 Shutting down Stock Tracker API...")


# Create FastAPI application
app = FastAPI(
    title="Stock Tracker API",
    description="Multi-tenant SaaS platform for Wildberries & Ozon sellers",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middlewares (order matters!)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(MetricsMiddleware)  # Track request metrics
app.add_middleware(
    RateLimitMiddleware,
    global_limit=1000,  # 1000 requests per minute globally
    global_window=60,
    tenant_limit=100,  # 100 requests per minute per tenant
    tenant_window=60,
)
app.add_middleware(TenantContextMiddleware)

# Register routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(sheets.router, prefix="/api/v1/sheets", tags=["Google Sheets"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin Panel"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])

# Mount static files for admin panel
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/admin", StaticFiles(directory=str(static_path), html=True), name="static")
    logger.info(f"✅ Admin panel mounted at /admin (static files from {static_path})")
else:
    logger.warning(f"⚠️ Static directory not found: {static_path}")


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    try:
        # Use default REGISTRY which is always available
        return PlainTextResponse(
            generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return PlainTextResponse(f"# Error: {str(e)}\n", media_type=CONTENT_TYPE_LATEST)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Stock Tracker API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "stock_tracker.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
