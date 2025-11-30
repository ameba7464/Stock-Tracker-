#!/usr/bin/env python3
"""
Legacy to Multi-Tenant Migration Script

Migrates existing single-tenant .env configuration to PostgreSQL multi-tenant setup.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from stock_tracker.database.connection import SessionLocal, init_db
from stock_tracker.database.models import (
    Tenant, User, Subscription, MarketplaceType,
    UserRole, PlanType, SubscriptionStatus
)
from stock_tracker.security import encrypt_credential
from stock_tracker.utils.logger import get_logger
import json

logger = get_logger(__name__)


def load_legacy_env() -> dict:
    """Load legacy .env configuration."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        config = {
            'wb_api_key': os.getenv('WILDBERRIES_API_KEY'),
            'google_sheet_id': os.getenv('GOOGLE_SHEET_ID'),
            'google_service_account_path': os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_PATH'),
            'google_service_account': os.getenv('GOOGLE_SERVICE_ACCOUNT'),
        }
        
        # Validate required fields
        if not config['wb_api_key']:
            raise ValueError("WILDBERRIES_API_KEY not found in .env")
        
        if not config['google_sheet_id']:
            raise ValueError("GOOGLE_SHEET_ID not found in .env")
        
        if not config['google_service_account'] and not config['google_service_account_path']:
            raise ValueError("Neither GOOGLE_SERVICE_ACCOUNT nor GOOGLE_SERVICE_ACCOUNT_KEY_PATH found")
        
        # Read service account JSON
        if config['google_service_account']:
            service_account_json = config['google_service_account']
        elif config['google_service_account_path']:
            with open(config['google_service_account_path'], 'r') as f:
                service_account_json = f.read()
        
        config['service_account_json'] = service_account_json
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load legacy .env: {e}")
        raise


def migrate_to_multitenant(admin_email: str, admin_password: str) -> dict:
    """
    Migrate legacy single-tenant to multi-tenant setup.
    
    Args:
        admin_email: Email for owner account
        admin_password: Password for owner account
        
    Returns:
        Dict with migration results
    """
    logger.info("Starting migration from legacy single-tenant to multi-tenant...")
    
    # Initialize database
    logger.info("Initializing database tables...")
    init_db()
    
    # Load legacy config
    logger.info("Loading legacy .env configuration...")
    legacy_config = load_legacy_env()
    
    db = SessionLocal()
    
    try:
        # Check if already migrated
        existing_tenant = db.query(Tenant).first()
        if existing_tenant:
            logger.warning("Migration already completed - tenants exist in database")
            return {
                "success": False,
                "message": "Database already contains tenants",
                "existing_tenants": db.query(Tenant).count()
            }
        
        # Encrypt credentials
        logger.info("Encrypting credentials...")
        encrypted_wb_key = encrypt_credential(legacy_config['wb_api_key'])
        encrypted_service_account = encrypt_credential(legacy_config['service_account_json'])
        
        # Create Tenant
        logger.info("Creating tenant...")
        tenant = Tenant(
            name="Legacy Seller",
            marketplace_type=MarketplaceType.WILDBERRIES,
            credentials_encrypted={
                'api_key': encrypted_wb_key
            },
            google_sheet_id=legacy_config['google_sheet_id'],
            google_service_account_encrypted=encrypted_service_account,
            auto_sync_enabled=True,
            sync_schedule="0 */6 * * *",  # Every 6 hours
            is_active=True
        )
        db.add(tenant)
        db.flush()  # Get tenant.id
        
        # Create Owner User
        logger.info("Creating owner user...")
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        user = User(
            email=admin_email,
            password_hash=pwd_context.hash(admin_password),
            full_name="Legacy Admin",
            tenant_id=tenant.id,
            role=UserRole.OWNER,
            is_active=True,
            is_verified=True
        )
        db.add(user)
        
        # Create Subscription
        logger.info("Creating subscription...")
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_type=PlanType.FREE,
            status=SubscriptionStatus.TRIAL,
            quota_used=0,
            quota_limit=100,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.add(subscription)
        
        # Commit transaction
        db.commit()
        
        logger.info("✅ Migration completed successfully!")
        
        return {
            "success": True,
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "user_email": user.email,
            "google_sheet_id": tenant.google_sheet_id,
            "subscription_plan": subscription.plan_type.value,
            "message": "Migration successful - you can now use the multi-tenant API"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Migration failed - check logs for details"
        }
        
    finally:
        db.close()


def main():
    """Main migration entry point."""
    print("=" * 80)
    print("STOCK TRACKER: LEGACY TO MULTI-TENANT MIGRATION")
    print("=" * 80)
    print()
    
    # Check prerequisites
    if not os.getenv("DATABASE_URL"):
        print("❌ ERROR: DATABASE_URL environment variable not set")
        print("   Please set DATABASE_URL to your PostgreSQL connection string")
        sys.exit(1)
    
    if not os.getenv("ENCRYPTION_MASTER_KEY"):
        print("❌ ERROR: ENCRYPTION_MASTER_KEY environment variable not set")
        print("   Generate key with:")
        print("   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
        sys.exit(1)
    
    print("📋 This script will:")
    print("   1. Create PostgreSQL tables")
    print("   2. Read your existing .env configuration")
    print("   3. Encrypt API keys and service account")
    print("   4. Create first Tenant with your credentials")
    print("   5. Create Owner user account")
    print("   6. Set up FREE subscription")
    print()
    
    # Get admin credentials
    admin_email = input("👤 Enter owner email address: ").strip()
    if not admin_email or '@' not in admin_email:
        print("❌ Invalid email address")
        sys.exit(1)
    
    import getpass
    admin_password = getpass.getpass("🔐 Enter owner password: ").strip()
    if len(admin_password) < 8:
        print("❌ Password must be at least 8 characters")
        sys.exit(1)
    
    password_confirm = getpass.getpass("🔐 Confirm password: ").strip()
    if admin_password != password_confirm:
        print("❌ Passwords do not match")
        sys.exit(1)
    
    print()
    print("🚀 Starting migration...")
    print()
    
    # Run migration
    result = migrate_to_multitenant(admin_email, admin_password)
    
    print()
    print("=" * 80)
    if result['success']:
        print("✅ MIGRATION SUCCESSFUL")
        print("=" * 80)
        print()
        print(f"Tenant ID: {result['tenant_id']}")
        print(f"Tenant Name: {result['tenant_name']}")
        print(f"Owner Email: {result['user_email']}")
        print(f"Google Sheet: {result['google_sheet_id']}")
        print(f"Subscription: {result['subscription_plan']}")
        print()
        print("📝 Next steps:")
        print("   1. Start FastAPI server: uvicorn src.stock_tracker.api.main:app --reload")
        print("   2. Start Celery worker: celery -A src.stock_tracker.workers.celery_app worker")
        print("   3. Login at: http://localhost:8000/docs")
        print(f"   4. Use email: {result['user_email']}")
        print()
    else:
        print("❌ MIGRATION FAILED")
        print("=" * 80)
        print()
        print(f"Error: {result.get('error', 'Unknown error')}")
        print(f"Message: {result['message']}")
        print()
        print("Check logs for details: logs/stock_tracker.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
