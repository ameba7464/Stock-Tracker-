"""
Debug script to check Statistics API response structure
"""
import requests
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.config import get_config

def check_statistics_api():
    """Check what fields Statistics API actually returns"""
    config = get_config()
    
    headers = {
        "Authorization": config.wildberries_api_key
    }
    
    date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
    params = {"dateFrom": date_from}
    
    print(f"\n🔍 Testing Statistics API")
    print(f"URL: {url}")
    print(f"Date from: {date_from}")
    print("="*80)
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\n✅ Response received: {len(data)} records")
        
        if data:
            # Show first record structure
            print(f"\n📋 First record structure:")
            first_record = data[0]
            print(json.dumps(first_record, indent=2, ensure_ascii=False))
            
            # Check for quantity fields
            print(f"\n🔎 Quantity fields in first record:")
            quantity_fields = [k for k in first_record.keys() if 'quant' in k.lower()]
            for field in quantity_fields:
                print(f"  - {field}: {first_record[field]}")
            
            # Statistics
            print(f"\n📊 Field statistics (first 10 records):")
            all_fields = set()
            for record in data[:10]:
                all_fields.update(record.keys())
            
            print(f"Unique fields found: {sorted(all_fields)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_statistics_api()
