"""
Tenant context middleware for extracting tenant from JWT token.
"""

from typing import Optional
from contextvars import ContextVar

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError

from stock_tracker.auth import verify_token
from stock_tracker.database.connection import get_db
from stock_tracker.database.models import Tenant, User
from stock_tracker.utils.logger import get_logger
from sqlalchemy.orm import Session

logger = get_logger(__name__)

# Context variables for request-scoped tenant and user
current_tenant_context: ContextVar[Optional[Tenant]] = ContextVar("current_tenant", default=None)
current_user_context: ContextVar[Optional[User]] = ContextVar("current_user", default=None)

# Security scheme
security = HTTPBearer()


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant context from JWT token.
    
    Sets current_tenant_context for use in request handlers.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request and set tenant context."""
        
        # Skip auth for public endpoints
        public_paths = ["/", "/docs", "/redoc", "/openapi.json", "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/health"]
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"Missing or invalid Authorization header for {request.url.path}")
            # Continue without setting context (will fail in protected routes)
            return await call_next(request)
        
        token = auth_header.split(" ")[1]
        
        try:
            # Verify JWT token
            payload = verify_token(token, token_type="access")
            user_id = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            
            # Load tenant and user from database
            # Note: This creates a new DB session per request
            # In production, consider connection pooling
            from stock_tracker.database.connection import SessionLocal
            db = SessionLocal()
            
            try:
                tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
                user = db.query(User).filter(User.id == user_id).first()
                
                if not tenant or not user:
                    logger.warning(f"Tenant or user not found: tenant_id={tenant_id}, user_id={user_id}")
                    db.close()
                    return await call_next(request)
                
                # Check if tenant is active
                if not tenant.is_active:
                    logger.warning(f"Inactive tenant attempted access: {tenant_id}")
                    db.close()
                    return await call_next(request)
                
                # Set context variables
                current_tenant_context.set(tenant)
                current_user_context.set(user)
                
                logger.debug(f"Set tenant context: {tenant.name} ({tenant_id})")
                
            finally:
                db.close()
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            # Continue without context
        except Exception as e:
            logger.error(f"Error in tenant context middleware: {e}", exc_info=True)
        
        response = await call_next(request)
        return response


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user.
    
    Usage:
        @app.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    token = credentials.credentials
    
    try:
        payload = verify_token(token, token_type="access")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_tenant(user: User = Depends(get_current_user)) -> Tenant:
    """
    Dependency to get current tenant from authenticated user.
    
    Usage:
        @app.get("/tenant-info")
        def tenant_info(tenant: Tenant = Depends(get_current_tenant)):
            return {"tenant_name": tenant.name}
    """
    if not user.tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not user.tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is suspended"
        )
    
    return user.tenant


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Get current active user (alias for get_current_user with active check)."""
    return user
