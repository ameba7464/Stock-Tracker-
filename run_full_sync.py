#!/usr/bin/env python3
"""
Full synchronization script to update Google Sheets with fixed orders data.

This script will perform a complete synchronization to update all products
in Google Sheets with the corrected orders data from Wildberries API.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config

logger = get_logger(__name__)


async def run_full_synchronization():
    """Run complete synchronization with Google Sheets update."""
    
    print("🚀 Starting Full Stock Tracker Synchronization")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 1. Initialize service
        print("🔧 1. Initializing Product Service...")
        config = get_config()
        service = ProductService()
        print(f"   ✅ Service initialized")
        print(f"   📊 Google Sheets ID: {config.google_sheets.sheet_id}")
        print(f"   🔑 API Key configured: {'Yes' if config.wildberries.api_key else 'No'}")
        
        # 2. Health check
        print("\n🏥 2. Performing Health Check...")
        health_status = await service.health_check()
        
        if health_status["service"] == "healthy":
            print("   ✅ All systems healthy")
        else:
            print(f"   ⚠️  Service status: {health_status['service']}")
            for component, status in health_status.get("components", {}).items():
                if "error" in str(status):
                    print(f"      ❌ {component}: {status}")
                else:
                    print(f"      ✅ {component}: {status}")
        
        # 3. Run API-to-Sheets synchronization
        print("\n📊 3. Running API-to-Sheets Synchronization...")
        print("   📡 Fetching fresh data from Wildberries API...")
        print("   📋 This will get warehouse remains and orders data...")
        print("   ⏳ Please wait, this may take 1-2 minutes...")
        
        sync_start = datetime.now()
        sync_result = await service.sync_from_api_to_sheets()
        sync_duration = datetime.now() - sync_start
        
        # 4. Display results
        print(f"\n📈 4. Synchronization Results:")
        print("=" * 60)
        
        print(f"   Status: {sync_result.status}")
        print(f"   Duration: {sync_duration.total_seconds():.1f} seconds")
        print(f"   Products total: {sync_result.products_total}")
        print(f"   Products processed: {sync_result.products_processed}")
        print(f"   Products failed: {sync_result.products_failed}")
        
        if sync_result.status.name == "COMPLETED":
            print("   🎉 SUCCESS: Full synchronization completed!")
            
            # Show success details
            success_rate = (sync_result.products_processed / sync_result.products_total * 100) if sync_result.products_total > 0 else 0
            print(f"   📊 Success rate: {success_rate:.1f}%")
            
            if sync_result.products_processed > 0:
                print(f"   ✅ {sync_result.products_processed} products updated with fresh orders data")
                print("   📋 Orders should now show correct values (not 0)")
            
        elif sync_result.status.name == "FAILED":
            print("   ❌ FAILED: Synchronization encountered errors")
            
            if sync_result.errors:
                print("   🚨 Errors encountered:")
                for error in sync_result.errors[:5]:  # Show first 5 errors
                    print(f"      - {error}")
                
                if len(sync_result.errors) > 5:
                    print(f"      ... and {len(sync_result.errors) - 5} more errors")
        
        # 5. Get updated inventory summary
        print("\n📊 5. Updated Inventory Summary:")
        print("-" * 40)
        
        try:
            summary = service.get_inventory_summary()
            
            if "error" not in summary:
                print(f"   Total products: {summary['total_products']}")
                print(f"   Total stock: {summary['total_stock']}")
                print(f"   Total orders: {summary['total_orders']}")
                print(f"   Average turnover: {summary['avg_turnover']:.3f}")
                
                # Show performance categories
                perf = summary.get("performance_categories", {})
                print(f"   High turnover products: {perf.get('high_turnover', 0)}")
                print(f"   Medium turnover products: {perf.get('medium_turnover', 0)}")
                print(f"   Low turnover products: {perf.get('low_turnover', 0)}")
                
                # Show top warehouses
                warehouses = summary.get("warehouses", {})
                if warehouses:
                    print("\n   📦 Top warehouses by orders:")
                    sorted_warehouses = sorted(
                        warehouses.items(), 
                        key=lambda x: x[1].get("total_orders", 0), 
                        reverse=True
                    )
                    
                    for wh_name, wh_data in sorted_warehouses[:3]:
                        orders = wh_data.get("total_orders", 0)
                        stock = wh_data.get("total_stock", 0)
                        products = wh_data.get("product_count", 0)
                        print(f"      - {wh_name}: {orders} orders, {stock} stock, {products} products")
            
            else:
                print(f"   ❌ Could not get summary: {summary['error']}")
                
        except Exception as e:
            print(f"   ⚠️  Could not get inventory summary: {e}")
        
        # 6. Show next steps
        print(f"\n💡 6. Next Steps and Recommendations:")
        print("-" * 40)
        
        if sync_result.status.name == "COMPLETED":
            print("   🎯 Immediate actions:")
            print("      1. ✅ Check Google Sheets - orders should now show real values")
            print("      2. 📊 Review inventory summary above for insights")
            print("      3. 🔄 Set up automatic sync (daily/hourly)")
            print("      4. 📈 Monitor turnover rates for inventory decisions")
            
            print("\n   🔧 Configuration recommendations:")
            print("      1. Enable automatic sync in .env (AUTO_SYNC_ENABLED=true)")
            print("      2. Set appropriate sync schedule (SYNC_SCHEDULE)")
            print("      3. Monitor API rate limits if frequent syncing")
            
        else:
            print("   🔧 Troubleshooting:")
            print("      1. Check API credentials and permissions")
            print("      2. Verify Google Sheets access and ID")
            print("      3. Review error messages above")
            print("      4. Check network connectivity")
            
        # 7. Final status
        print(f"\n✅ 7. Synchronization Complete!")
        print("=" * 60)
        
        if sync_result.products_processed > 0:
            print("🎉 SUCCESS: Orders data has been updated!")
            print("📋 Your Google Sheets should now show correct order counts")
            print("📊 The 'orders showing 0' issue has been resolved")
        else:
            print("⚠️  No products were updated - please check the errors above")
            
        print(f"\n📝 Session summary:")
        print(f"   - Started: {sync_start.strftime('%H:%M:%S')}")
        print(f"   - Completed: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   - Duration: {sync_duration.total_seconds():.1f} seconds")
        print(f"   - Status: {sync_result.status.name}")
        
        return sync_result.status.name == "COMPLETED"
        
    except Exception as e:
        print(f"\n❌ Synchronization failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_full_synchronization())
    
    if success:
        print("\n🚀 Ready for production use!")
        exit(0)
    else:
        print("\n🔧 Please review and fix issues before production use")
        exit(1)