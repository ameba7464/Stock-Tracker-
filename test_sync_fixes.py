"""
Test script to verify all fixes are working
"""
import asyncio
from src.stock_tracker.services.product_service import ProductService
from src.stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

async def test_sync():
    """Test synchronization with all fixes"""
    
    print("="*70)
    print("TESTING SYNCHRONIZATION WITH ALL FIXES")
    print("="*70)
    
    service = ProductService()
    
    print("\n1. Running sync_from_api_to_sheets...")
    try:
        session = await service.sync_from_api_to_sheets()
        
        print(f"\nSync Results:")
        print(f"  - Session ID: {session.session_id}")
        print(f"  - Status: {session.status}")
        print(f"  - Total products: {session.products_total}")
        print(f"  - Processed: {session.products_processed}")
        print(f"  - Failed: {session.products_failed}")
        
        # Handle duration formatting
        if session.duration:
            if isinstance(session.duration, (int, float)):
                print(f"  - Duration: {session.duration:.2f}s")
            else:
                print(f"  - Duration: {session.duration}")
        else:
            print("  - Duration: N/A")
        
        if session.errors:
            print(f"\nErrors ({len(session.errors)}):")
            for i, error in enumerate(session.errors[:10], 1):
                print(f"  {i}. {error}")
            if len(session.errors) > 10:
                print(f"  ... and {len(session.errors) - 10} more errors")
        else:
            print("\n[OK] No errors!")
        
    except Exception as e:
        print(f"\n[FAIL] SYNC FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sync())
