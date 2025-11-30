"""
Tenant management routes.
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from stock_tracker.database.connection import get_db
from stock_tracker.database.models import Tenant, User
from stock_tracker.api.middleware.tenant_context import get_current_user, get_current_tenant
from stock_tracker.services.tenant_credentials import (
    update_wildberries_credentials,
    update_google_credentials
)
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Response models
class TenantResponse(BaseModel):
    """Tenant information response."""
    id: str
    name: str
    marketplace_type: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TenantCredentialsUpdate(BaseModel):
    """Update tenant marketplace credentials."""
    wildberries_api_key: Optional[str] = None
    google_sheet_id: Optional[str] = None
    google_credentials_json: Optional[str] = None


@router.get("/me", response_model=TenantResponse)
async def get_current_tenant_info(
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get current tenant information."""
    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        marketplace_type=tenant.marketplace_type,
        is_active=tenant.is_active,
        created_at=tenant.created_at
    )


@router.patch("/me/credentials")
async def update_credentials(
    data: TenantCredentialsUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update tenant marketplace credentials.
    
    Requires owner or admin role.
    
    This endpoint is used by Telegram bot to save API keys sent by sellers.
    """
    # Check permissions
    if user.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can update credentials"
        )
    
    # Update Wildberries API key
    if data.wildberries_api_key:
        update_wildberries_credentials(tenant, data.wildberries_api_key)
        logger.info(f"Wildberries API key updated for tenant {tenant.id}")
    
    # Update Google Sheets credentials
    if data.google_sheet_id and data.google_credentials_json:
        update_google_credentials(
            tenant,
            data.google_sheet_id,
            data.google_credentials_json
        )
        logger.info(f"Google Sheets credentials updated for tenant {tenant.id}")
    elif data.google_sheet_id:
        tenant.google_sheet_id = data.google_sheet_id
        logger.info(f"Google Sheet ID updated for tenant {tenant.id}")
    
    db.commit()
    
    return {
        "message": "Credentials updated successfully",
        "tenant_id": str(tenant.id)
    }


@router.patch("/me")
async def update_tenant_info(
    name: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update tenant information.
    
    Requires owner role.
    """
    if user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenant owner can update tenant info"
        )
    
    if name:
        tenant.name = name
    
    db.commit()
    
    logger.info(f"Tenant info updated: {tenant.id}")
    
    return {"message": "Tenant updated successfully"}
