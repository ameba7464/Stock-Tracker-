"""
Debug V2 API request to see exact error
"""
import asyncio
import json
from datetime import datetime, timedelta
from src.stock_tracker.api.client import WildberriesAPIClient
from src.stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

async def test_v2_api():
    """Test V2 API request with detailed logging"""
    
    print("="*70)
    print("DEBUGGING V2 API REQUEST")
    print("="*70)
    
    client = WildberriesAPIClient()
    
    # Build request manually
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    request_body = {
        "currentPeriod": {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        },
        "stockType": "",
        "skipDeletedNm": True,
        "availabilityFilters": ["actual", "balanced", "deficient"],
        "orderBy": {
            "field": "stockCount",
            "mode": "desc"
        },
        "limit": 10,
        "offset": 0
    }
    
    print("\nRequest Body:")
    print(json.dumps(request_body, indent=2, ensure_ascii=False))
    
    url = "https://seller-analytics-api.wildberries.ru/api/v2/stocks-report/products/products"
    
    print(f"\nURL: {url}")
    print(f"Method: POST")
    print(f"Headers: {dict(client.session.headers)}")
    
    print("\nMaking request...")
    
    try:
        # Make raw request to see exact error
        import requests
        response = requests.post(
            url,
            json=request_body,
            headers=dict(client.session.headers),
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"\nResponse Body:")
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text)
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_v2_api())
