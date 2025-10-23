#!/usr/bin/env python3
"""
Простой тест обновления данных через новую систему.
Проверяем что именно записывается в Google Sheets.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.utils.config import get_config

async def test_table_refresh():
    """Тест прямого обновления таблицы."""
    
    print("🧪 TESTING: Direct Table Refresh")
    print("=" * 50)
    
    try:
        # Инициализация
        sheets_client = GoogleSheetsClient("1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
        operations = SheetsOperations(sheets_client)
        
        print(f"📊 Target spreadsheet: 1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
        print(f"📋 Target worksheet: Stock Tracker")
        
        # Попытка обновления данных
        print("\n🔄 Starting table refresh...")
        await operations.refresh_table_data(
            spreadsheet_id="1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho",
            worksheet_name="Stock Tracker"
        )
        
        print("✅ Table refresh completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Table refresh failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔄 TESTING: Table Refresh with New Logic")
    print("=" * 60)
    print("Purpose: Test direct table refresh to see what warehouse data is generated")
    print()
    
    try:
        success = asyncio.run(test_table_refresh())
        if success:
            print("\n✅ TEST PASSED: Table refresh successful")
            print("📊 Check Google Sheets to see if warehouse names are real or fake")
        else:
            print("\n❌ TEST FAILED: Table refresh error")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)