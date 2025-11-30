"""
API Startup Test Script - Tests multi-tenant FastAPI components
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

print("=" * 80)
print("STOCK TRACKER API - COMPONENT TEST")
print("=" * 80)

# Test 1: Auth modules
print("\n[1/5] Testing Auth modules...")
try:
    from stock_tracker.auth import hash_password, verify_password, create_access_token
    
    # Test password hashing
    test_pwd = "test12345678"
    hashed = hash_password(test_pwd)
    is_valid = verify_password(test_pwd, hashed)
    
    if is_valid:
        print("  ✅ Password hashing works")
    else:
        print("  ❌ Password verification failed")
        
except Exception as e:
    print(f"  ❌ Auth import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Database models
print("\n[2/5] Testing Database models...")
try:
    from stock_tracker.database.models import Tenant, User, Subscription, SyncLog, RefreshToken, WebhookConfig
    print("  ✅ All models imported:")
    print(f"     - Tenant: {Tenant.__tablename__}")
    print(f"     - User: {User.__tablename__}")
    print(f"     - Subscription: {Subscription.__tablename__}")
    print(f"     - SyncLog: {SyncLog.__tablename__}")
    print(f"     - RefreshToken: {RefreshToken.__tablename__}")
    print(f"     - WebhookConfig: {WebhookConfig.__tablename__}")
except Exception as e:
    print(f"  ❌ Database models import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Marketplace clients
print("\n[3/5] Testing Marketplace clients...")
try:
    from stock_tracker.marketplaces import (
        create_marketplace_client,
        MarketplaceType,
        WildberriesMarketplaceClient,
        OzonMarketplaceClient
    )
    print("  ✅ Marketplace abstraction imported:")
    print(f"     - MarketplaceType: {list(MarketplaceType)}")
    print(f"     - WildberriesMarketplaceClient: {WildberriesMarketplaceClient.__name__}")
    print(f"     - OzonMarketplaceClient: {OzonMarketplaceClient.__name__}")
except Exception as e:
    print(f"  ❌ Marketplace import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: FastAPI app
print("\n[4/5] Testing FastAPI app...")
try:
    from stock_tracker.api.main import app
    
    # Count routes
    route_count = len([r for r in app.routes if hasattr(r, 'path')])
    print(f"  ✅ FastAPI app loaded with {route_count} routes:")
    
    # Show key routes
    key_routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            if any(path in route.path for path in ['/auth/', '/tenants/', '/products/', '/health/']):
                methods = ', '.join(route.methods)
                key_routes.append(f"{methods} {route.path}")
    
    for route in sorted(key_routes)[:10]:
        print(f"     {route}")
        
except Exception as e:
    print(f"  ❌ FastAPI app import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Environment variables
print("\n[5/5] Checking Environment variables...")
env_vars = {
    "Multi-tenant": ['DATABASE_URL', 'SECRET_KEY', 'ENCRYPTION_MASTER_KEY'],
    "Optional": ['REDIS_URL', 'CELERY_BROKER_URL', 'SENTRY_DSN'],
    "Legacy": ['WILDBERRIES_API_KEY', 'GOOGLE_SHEET_ID']
}

for category, vars_list in env_vars.items():
    print(f"  {category}:")
    for var in vars_list:
        value = os.getenv(var)
        if value:
            print(f"    ✅ {var}: {'*' * 20} (set)")
        else:
            status = "⚠️" if category == "Multi-tenant" else "ℹ️"
            print(f"    {status} {var}: NOT SET")

print("\n" + "=" * 80)
print("TEST COMPLETED")
print("=" * 80)

print("\n📋 Next steps:")
print("1. Set environment variables in .env file")
print("2. Install dependencies: pip install -r requirements.txt")
print("3. Create database: createdb stock_tracker")
print("4. Run migrations: alembic upgrade head")
print("5. Start API: uvicorn stock_tracker.api.main:app --reload")
print("\nSwagger UI: http://localhost:8000/docs")
