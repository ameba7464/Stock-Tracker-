"""
Google Sheets Management API endpoints.

Provides endpoints for:
- Creating new Google Sheets for tenants
- Updating Google credentials
- Testing sheet connection
- Manual sheet refresh
- Getting sheet information
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from stock_tracker.database.connection import get_db
from stock_tracker.api.middleware.tenant_context import get_current_tenant
from stock_tracker.database.models import Tenant, Product
from stock_tracker.services.google_sheets_service import GoogleSheetsService
from stock_tracker.services.tenant_credentials import update_google_credentials
from stock_tracker.utils.exceptions import SheetsAPIError

logger = logging.getLogger(__name__)

router = APIRouter()


class GoogleCredentialsRequest(BaseModel):
    """Request body for updating Google credentials."""
    google_sheet_id: Optional[str] = Field(
        None,
        description="Google Sheet ID (if connecting to existing sheet)"
    )
    google_credentials_json: str = Field(
        ...,
        description="Google service account JSON credentials"
    )


class CreateSheetRequest(BaseModel):
    """Request body for creating new Google Sheet."""
    title: Optional[str] = Field(
        None,
        description="Custom sheet title (default: '{tenant_name} - Stock Tracker')"
    )
    share_with_email: Optional[str] = Field(
        None,
        description="Email address to share sheet with"
    )


class SheetInfoResponse(BaseModel):
    """Response with Google Sheet information."""
    sheet_id: str
    sheet_url: str
    title: str
    worksheet_name: str
    row_count: int
    col_count: int
    data_rows: int
    last_updated: str
    is_configured: bool


class SheetCreatedResponse(BaseModel):
    """Response after creating Google Sheet."""
    sheet_id: str
    sheet_url: str
    title: str
    worksheet_name: str
    message: str


class TestConnectionResponse(BaseModel):
    """Response from connection test."""
    success: bool
    sheet_title: Optional[str] = None
    sheet_url: Optional[str] = None
    worksheet_title: Optional[str] = None
    row_count: Optional[int] = None
    col_count: Optional[int] = None
    error: Optional[str] = None


class SyncResponse(BaseModel):
    """Response from manual sheet sync."""
    success: bool
    products_synced: int
    duration_seconds: float
    sheet_url: str
    message: str


@router.post(
    "/credentials",
    response_model=Dict[str, str],
    summary="Update Google Sheets credentials",
    description="Store encrypted Google service account credentials for tenant"
)
async def update_credentials(
    request: GoogleCredentialsRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Update Google Sheets credentials for tenant.
    
    Stores encrypted service account JSON and optional sheet ID.
    """
    try:
        logger.info(f"Updating Google credentials for tenant {tenant.id}")
        
        # Update credentials using tenant credentials service
        update_google_credentials(
            tenant=tenant,
            sheet_id=request.google_sheet_id,
            credentials_json=request.google_credentials_json,
            db_session=db
        )
        
        logger.info(f"✅ Google credentials updated for tenant {tenant.id}")
        
        return {
            "message": "Google Sheets credentials updated successfully",
            "tenant_id": str(tenant.id),
            "sheet_id": request.google_sheet_id or "not_set"
        }
        
    except Exception as e:
        logger.error(f"Failed to update Google credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credentials: {str(e)}"
        )


@router.post(
    "/create",
    response_model=SheetCreatedResponse,
    summary="Create new Google Sheet",
    description="Create a new Google Sheet for the tenant with proper formatting"
)
async def create_sheet(
    request: CreateSheetRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> SheetCreatedResponse:
    """
    Create a new Google Sheet for tenant.
    
    Requires Google credentials to be configured first.
    """
    try:
        # Check if credentials are configured
        if not tenant.google_service_account_encrypted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google credentials not configured. Please update credentials first."
            )
        
        logger.info(f"Creating new Google Sheet for tenant {tenant.id}")
        
        # Initialize sheets service
        sheets_service = GoogleSheetsService(tenant)
        
        # Create sheet
        result = sheets_service.create_new_sheet(
            title=request.title,
            share_with_email=request.share_with_email
        )
        
        # Update tenant with sheet ID
        tenant.google_sheet_id = result["sheet_id"]
        db.commit()
        
        logger.info(f"✅ Created Google Sheet: {result['sheet_url']}")
        
        return SheetCreatedResponse(
            sheet_id=result["sheet_id"],
            sheet_url=result["sheet_url"],
            title=result["title"],
            worksheet_name=result["worksheet_name"],
            message=f"Google Sheet created successfully! Access it at: {result['sheet_url']}"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SheetsAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Sheets API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to create Google Sheet: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sheet: {str(e)}"
        )


@router.get(
    "/info",
    response_model=SheetInfoResponse,
    summary="Get Google Sheet information",
    description="Retrieve information about tenant's Google Sheet"
)
async def get_sheet_info(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> SheetInfoResponse:
    """
    Get information about tenant's Google Sheet.
    """
    try:
        # Check if sheet is configured
        if not tenant.google_sheet_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Google Sheet not configured for this tenant"
            )
        
        logger.info(f"Getting sheet info for tenant {tenant.id}")
        
        # Initialize sheets service
        sheets_service = GoogleSheetsService(tenant)
        
        # Get sheet info
        info = sheets_service.get_sheet_info()
        
        return SheetInfoResponse(
            **info,
            is_configured=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SheetsAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Sheets API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to get sheet info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sheet info: {str(e)}"
        )


@router.post(
    "/test",
    response_model=TestConnectionResponse,
    summary="Test Google Sheets connection",
    description="Verify access to Google Sheet and return basic information"
)
async def test_connection(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> TestConnectionResponse:
    """
    Test connection to Google Sheet.
    """
    try:
        # Check if configured
        if not tenant.google_sheet_id or not tenant.google_service_account_encrypted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google Sheets not fully configured. Please update credentials and sheet ID."
            )
        
        logger.info(f"Testing Google Sheets connection for tenant {tenant.id}")
        
        # Initialize sheets service
        sheets_service = GoogleSheetsService(tenant)
        
        # Test connection
        result = sheets_service.test_connection()
        
        return TestConnectionResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SheetsAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Sheets API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to test connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {str(e)}"
        )


@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Manually sync products to Google Sheet",
    description="Force immediate synchronization of products to Google Sheet"
)
async def sync_to_sheet(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> SyncResponse:
    """
    Manually trigger product sync to Google Sheet.
    
    This will immediately update the Google Sheet with current product data.
    """
    try:
        # Check if configured
        if not tenant.google_sheet_id or not tenant.google_service_account_encrypted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google Sheets not fully configured"
            )
        
        logger.info(f"Manual Google Sheets sync for tenant {tenant.id}")
        
        # Get all products for tenant
        products = db.query(Product).filter(
            Product.tenant_id == tenant.id
        ).all()
        
        if not products:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No products found to sync. Please sync with marketplace first."
            )
        
        # Initialize sheets service
        sheets_service = GoogleSheetsService(tenant)
        
        # Sync products
        result = sheets_service.sync_products_to_sheet(products, db)
        
        logger.info(f"✅ Manual sync completed: {result['products_synced']} products")
        
        return SyncResponse(
            success=result["success"],
            products_synced=result["products_synced"],
            duration_seconds=result["duration_seconds"],
            sheet_url=result["sheet_url"],
            message=f"Successfully synced {result['products_synced']} products to Google Sheet"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SheetsAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Sheets API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to sync to Google Sheet: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync: {str(e)}"
        )
