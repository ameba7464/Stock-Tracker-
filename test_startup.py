#!/usr/bin/env python3
"""
Minimal test script to diagnose Railway startup issues
"""

import sys
import os
import time

print("=" * 80)
print("TEST STARTUP SCRIPT")
print("=" * 80)
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Platform: {sys.platform}")
print(f"Current directory: {os.getcwd()}")
print(f"Script location: {__file__}")
print("=" * 80)

print("\n[1/5] Checking environment variables...")
env_vars = ['WILDBERRIES_API_KEY', 'GOOGLE_SHEET_ID', 'GOOGLE_SERVICE_ACCOUNT']
for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"  ✅ {var}: {'*' * 20} (set)")
    else:
        print(f"  ❌ {var}: NOT SET")

print("\n[2/5] Checking directory structure...")
expected_dirs = ['src', 'src/stock_tracker', 'logs']
for dir_path in expected_dirs:
    if os.path.exists(dir_path):
        print(f"  ✅ {dir_path}")
    else:
        print(f"  ❌ {dir_path} - NOT FOUND")

print("\n[3/5] Testing basic imports...")
try:
    import asyncio
    print("  ✅ asyncio")
except ImportError as e:
    print(f"  ❌ asyncio: {e}")

try:
    import requests
    print("  ✅ requests")
except ImportError as e:
    print(f"  ❌ requests: {e}")

try:
    import gspread
    print("  ✅ gspread")
except ImportError as e:
    print(f"  ❌ gspread: {e}")

print("\n[4/5] Testing path setup...")
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
print(f"  Python path[0]: {sys.path[0]}")

print("\n[5/5] Testing module imports...")
try:
    from stock_tracker.utils.logger import get_logger
    print("  ✅ stock_tracker.utils.logger")
    logger = get_logger(__name__)
    logger.info("Logger initialized successfully")
except Exception as e:
    print(f"  ❌ stock_tracker.utils.logger: {e}")
    import traceback
    traceback.print_exc()

try:
    from stock_tracker.utils.config import get_config
    print("  ✅ stock_tracker.utils.config")
    config = get_config()
    print(f"     - Sheet ID: {config.google_sheets.sheet_id[:20]}...")
except Exception as e:
    print(f"  ❌ stock_tracker.utils.config: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ TEST COMPLETED - Service should start if all checks pass")
print("Keeping alive for 60 seconds...")
print("=" * 80)

# Keep alive
try:
    for i in range(60):
        time.sleep(1)
        if i % 10 == 0:
            print(f"[{i}s] Still alive...")
except KeyboardInterrupt:
    print("\nStopped by user")

print("\nTest script finished")
