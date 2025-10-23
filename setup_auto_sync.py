#!/usr/bin/env python3
"""
Setup script for automated synchronization.

This script will help configure automatic synchronization
for the Stock Tracker to keep data up-to-date.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.utils.config import get_config
from stock_tracker.services.scheduler import SyncScheduler
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def setup_automatic_sync():
    """Setup automatic synchronization."""
    
    print("⚙️  Setting Up Automatic Synchronization")
    print("=" * 50)
    
    try:
        # Load current config
        config = get_config()
        
        print("\n📋 Current Configuration:")
        print(f"   Auto sync enabled: {config.app.auto_sync_enabled}")
        print(f"   Sync schedule: {config.app.sync_schedule}")
        print(f"   Max products per sync: {config.app.max_products_per_sync}")
        
        # Recommendations for sync frequency
        print("\n💡 Sync Frequency Recommendations:")
        print("   📅 Daily (recommended): '0 2 * * *' - runs at 2 AM daily")
        print("   🕒 Every 6 hours: '0 */6 * * *' - runs 4 times per day")  
        print("   🕐 Hourly (intensive): '0 * * * *' - runs every hour")
        print("   🕘 Business hours: '0 9-17 * * 1-5' - weekdays 9 AM to 5 PM")
        
        # Show current .env settings
        env_file = Path(".env")
        if env_file.exists():
            print("\n📄 Current .env Settings:")
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                if any(key in line for key in ['AUTO_SYNC', 'SYNC_SCHEDULE', 'MAX_PRODUCTS']):
                    print(f"   {line.strip()}")
        
        print("\n🔧 Automated Sync Setup Instructions:")
        print("-" * 40)
        
        print("1. ✅ Enable auto sync in .env:")
        print("   AUTO_SYNC_ENABLED=true")
        
        print("\n2. 📅 Set sync schedule (cron format):")
        print("   SYNC_SCHEDULE=0 2 * * *  # Daily at 2 AM")
        
        print("\n3. 🚀 Start the scheduler service:")
        print("   python -m stock_tracker.services.scheduler")
        
        print("\n4. 📊 Monitor sync logs:")
        print("   tail -f ./logs/stock_tracker.log")
        
        # Create a simple starter script
        starter_script = """#!/usr/bin/env python3
\"\"\"
Automatic sync starter script.
Run this to start the automated synchronization service.
\"\"\"

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.services.scheduler import SyncScheduler
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

async def main():
    print("🚀 Starting Stock Tracker Automatic Sync Service")
    print("Press Ctrl+C to stop")
    
    scheduler = SyncScheduler()
    
    try:
        await scheduler.start()
    except KeyboardInterrupt:
        print("\\n⏹️  Stopping sync service...")
        await scheduler.stop()
        print("✅ Service stopped")

if __name__ == "__main__":
    asyncio.run(main())
"""
        
        with open("start_auto_sync.py", "w", encoding="utf-8") as f:
            f.write(starter_script)
        
        print("\n📁 Created starter script: start_auto_sync.py")
        
        # Instructions for Windows service (optional)
        print("\n🪟 Optional: Windows Service Setup")
        print("-" * 40)
        print("To run as Windows service:")
        print("1. Install: pip install pywin32")
        print("2. Create service script (advanced users)")
        print("3. Or use Task Scheduler for simple automation")
        
        print("\n✅ Setup Complete!")
        print("📋 Next steps:")
        print("   1. Update .env with desired schedule")
        print("   2. Run: python start_auto_sync.py")
        print("   3. Monitor logs for successful runs")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False


if __name__ == "__main__":
    setup_automatic_sync()