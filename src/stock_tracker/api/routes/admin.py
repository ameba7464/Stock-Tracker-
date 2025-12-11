"""
Admin panel routes for user and subscription management.
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from stock_tracker.database.connection import get_db
from stock_tracker.database.models import User, Tenant, Subscription, UserRole
from stock_tracker.api.middleware.tenant_context import get_current_user
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Response Models
class UserDetailResponse(BaseModel):
    """Detailed user information for admin panel."""
    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    is_admin: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    
    # Tenant info
    tenant_id: Optional[str] = None
    tenant_name: str
    marketplace_type: str
    
    # Subscription info
    has_access: bool
    subscription_status: str
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list item for admin panel."""
    id: str
    email: str
    full_name: Optional[str]
    tenant_name: str
    has_access: bool
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UpdateUserAccessRequest(BaseModel):
    """Request to update user access permissions."""
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    has_access: Optional[bool] = None


class UsersListPaginatedResponse(BaseModel):
    """Paginated users list response."""
    users: List[UserListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatsResponse(BaseModel):
    """Admin panel statistics."""
    total_users: int
    active_users: int
    admin_users: int
    total_tenants: int
    users_with_access: int
    users_without_access: int


# Dependency to check admin access
async def require_admin(current_user: User = Depends(get_current_user)):
    """Ensure current user has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/stats", response_model=StatsResponse)
async def get_admin_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Get admin panel statistics.
    
    Returns overview of users, tenants, and subscriptions.
    """
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    admin_users = db.query(func.count(User.id)).filter(User.is_admin == True).scalar()
    total_tenants = db.query(func.count(Tenant.id)).scalar()
    
    # Access counts
    with_access = db.query(func.count(Subscription.id)).filter(
        Subscription.has_access == True
    ).scalar()
    without_access = db.query(func.count(Subscription.id)).filter(
        Subscription.has_access == False
    ).scalar()
    
    return StatsResponse(
        total_users=total_users or 0,
        active_users=active_users or 0,
        admin_users=admin_users or 0,
        total_tenants=total_tenants or 0,
        users_with_access=with_access or 0,
        users_without_access=without_access or 0
    )


@router.get("/users", response_model=UsersListPaginatedResponse)
async def get_all_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    access_filter: Optional[bool] = Query(None, description="Filter by access status"),
    active_only: bool = Query(False, description="Show only active users"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Get paginated list of all users with filtering and search.
    
    Supports:
    - Pagination
    - Search by email or full name
    - Filter by access status
    - Filter by active status
    """
    # Build query with LEFT JOINs since tenant and subscription are optional
    query = db.query(User).outerjoin(Tenant).outerjoin(Subscription)
    
    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                User.email.ilike(search_filter),
                User.full_name.ilike(search_filter),
                Tenant.name.ilike(search_filter)
            )
        )
    
    if access_filter is not None:
        query = query.filter(Subscription.has_access == access_filter)
    
    if active_only:
        query = query.filter(User.is_active == True)
    
    # Get total count
    total = query.count()
    
    logger.info(f"Loading users: page={page}, total={total}, search={search}, access_filter={access_filter}, active_only={active_only}")
    
    # Apply pagination
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
    
    logger.info(f"Found {len(users)} users on page {page}")
    
    # Format response
    users_list = [
        UserListResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name or "N/A",
            tenant_name=user.tenant.name if user.tenant else "No Tenant",
            has_access=user.subscription.has_access if hasattr(user, 'subscription') and user.subscription else False,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        )
        for user in users
    ]
    
    total_pages = (total + page_size - 1) // page_size
    
    logger.info(f"Returning {len(users_list)} users, total_pages={total_pages}")
    
    return UsersListPaginatedResponse(
        users=users_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Get detailed information about a specific user.
    
    Returns:
    - User profile
    - Tenant information
    - Subscription details
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    tenant = user.tenant
    subscription = user.subscription if hasattr(user, 'subscription') else None
    
    return UserDetailResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name or "N/A",
        role=user.role.value if user.role else "USER",
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        tenant_id=str(tenant.id) if tenant else None,
        tenant_name=tenant.name if tenant else "No Tenant",
        marketplace_type="wildberries",  # Default marketplace
        has_access=subscription.has_access if subscription else False,
        subscription_status=subscription.status if subscription else "unpaid"
    )


@router.patch("/users/{user_id}/access", response_model=UserDetailResponse)
async def update_user_access(
    user_id: UUID,
    data: UpdateUserAccessRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Update user access permissions.
    
    Allows admin to:
    - Activate/deactivate user account
    - Grant/revoke admin privileges
    - Change user's subscription plan
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from removing their own admin rights
    if user.id == admin.id and data.is_admin is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges"
        )
    
    try:
        # Update user fields
        if data.is_active is not None:
            user.is_active = data.is_active
            logger.info(f"Admin {admin.email} set user {user.email} active status to {data.is_active}")
        
        if data.is_admin is not None:
            user.is_admin = data.is_admin
            logger.info(f"Admin {admin.email} set user {user.email} admin status to {data.is_admin}")
        
        # Update subscription access
        if data.has_access is not None:
            subscription = None
            if hasattr(user, 'subscription'):
                subscription = user.subscription
            
            if not subscription:
                # Create subscription if it doesn't exist
                subscription = Subscription(
                    user_id=user.id,
                    has_access=False,
                    status='unpaid'
                )
                db.add(subscription)
                db.flush()
            
            # Grant or revoke access
            if data.has_access:
                subscription.grant_access()
                logger.info(f"Admin {admin.email} granted access to user {user.email}")
            else:
                subscription.revoke_access()
                logger.info(f"Admin {admin.email} revoked access from user {user.email}")
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        # Return updated user details
        return await get_user_details(user_id, db, admin)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user access: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user access"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Delete a user account (soft delete by setting is_active to False).
    
    Note: This doesn't actually delete the user from database,
    just deactivates the account.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deleting themselves
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    try:
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Admin {admin.email} deactivated user {user.email}")
        
        return {"message": f"User {user.email} has been deactivated"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
