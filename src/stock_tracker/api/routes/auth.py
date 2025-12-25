"""
Authentication routes for login, registration, token refresh.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from stock_tracker.database.connection import get_db
from stock_tracker.database.models import User, Tenant, Subscription, RefreshToken
from stock_tracker.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from stock_tracker.api.middleware.tenant_context import get_current_user
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.transaction import transaction_scope

logger = get_logger(__name__)

router = APIRouter()


# Request/Response models
class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    company_name: str = Field(..., min_length=2, max_length=255)
    marketplace_type: str = Field("wildberries", pattern="^(wildberries|ozon)$")


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register new tenant and owner user.
    
    Creates:
    - Tenant account (company)
    - Owner user
    - Free subscription
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Use explicit transaction management to ensure atomicity
    try:
        # Create tenant
        tenant = Tenant(
            name=data.company_name,
            marketplace_type=data.marketplace_type,
            is_active=True
        )
        db.add(tenant)
        db.flush()  # Get tenant ID
        
        # Create subscription (FREE plan)
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_type="FREE",
            status="active",
            quota_used=0
        )
        db.add(subscription)
        
        # Create owner user
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            tenant_id=tenant.id,
            role="owner",
            is_active=True
        )
        db.add(user)
        db.flush()  # Get user ID
        
        # Create tokens
        access_token = create_access_token(
            user_id=str(user.id),
            tenant_id=str(tenant.id),
            role=user.role
        )
        refresh_token_str = create_refresh_token(user_id=str(user.id))
        
        # Store refresh token hash (using SHA256 for long tokens)
        import hashlib
        token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(refresh_token_record)
        
        # Commit all changes in one transaction
        db.commit()
        
        logger.info(f"New tenant registered: {tenant.name} ({tenant.id})")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return tokens.
    """
    # Find user by email
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    if not user.tenant or not user.tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is suspended"
        )
    
    # Create tokens
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role
    )
    refresh_token_str = create_refresh_token(user_id=str(user.id))
    
    # Store refresh token (using SHA256 for long tokens)
    import hashlib
    token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
    
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(refresh_token_record)
    db.commit()
    
    logger.info(f"User logged in: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        # Verify refresh token
        payload = verify_token(data.refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        # Find user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token exists and not revoked (using SHA256 for long tokens)
        import hashlib
        token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()
        stored_token = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False
        ).first()
        
        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found or revoked"
            )
        
        # Create new tokens
        access_token = create_access_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            role=user.role
        )
        new_refresh_token = create_refresh_token(user_id=str(user.id))
        
        # Revoke old refresh token
        stored_token.is_revoked = True
        
        # Store new refresh token (using SHA256 for long tokens)
        new_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        new_token_record = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(new_token_record)
        db.commit()
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token
        )
        
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking all refresh tokens.
    """
    # Revoke all refresh tokens for user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    
    db.commit()
    
    logger.info(f"User logged out: {user.email}")
    
    return {"message": "Logged out successfully"}
