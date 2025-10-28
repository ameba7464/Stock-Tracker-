"""
Dual-API Stock Fetcher - combines FBO (Statistics) and FBS (Marketplace) stocks
"""

import requests
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from stock_tracker.utils.config import get_config


class DualAPIStockFetcher:
    """Fetches stocks from both Statistics API (FBO) and Marketplace API v3 (FBS)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'Authorization': api_key,
            'Content-Type': 'application/json'
        }
        self._fbs_warehouses = None
    
    def get_fbs_warehouses(self) -> List[Dict]:
        """Get list of FBS warehouses"""
        if self._fbs_warehouses is not None:
            return self._fbs_warehouses
        
        url = "https://marketplace-api.wildberries.ru/api/v3/warehouses"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            self._fbs_warehouses = response.json()
            return self._fbs_warehouses
        
        except Exception as e:
            print(f"Error fetching FBS warehouses: {e}")
            return []
    
    def get_fbo_stocks(self, date_from: str = None) -> List[Dict]:
        """
        Get FBO stocks from Statistics API
        
        Args:
            date_from: Date in format YYYY-MM-DD (default: 7 days ago)
        
        Returns:
            List of stock records with fields:
            - nmId, barcode, supplierArticle, warehouseName, quantity, etc.
        """
        if date_from is None:
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
        params = {"dateFrom": date_from}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            print(f"Error fetching FBO stocks: {e}")
            return []
    
    def get_fbs_stocks(self, barcodes: List[str]) -> Dict[int, List[Dict]]:
        """
        Get FBS stocks from Marketplace API v3
        
        Args:
            barcodes: List of barcodes to query
        
        Returns:
            Dictionary mapping warehouse_id -> list of stocks
            Each stock has: {"sku": barcode, "amount": quantity}
        """
        warehouses = self.get_fbs_warehouses()
        
        if not warehouses:
            return {}
        
        result = {}
        
        for warehouse in warehouses:
            wh_id = warehouse.get('id')
            wh_name = warehouse.get('name')
            
            url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{wh_id}"
            body = {"skus": barcodes}
            
            try:
                response = requests.post(url, headers=self.headers, json=body, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                stocks = data.get('stocks', [])
                
                if stocks:
                    result[wh_id] = {
                        'warehouse_name': wh_name,
                        'warehouse_id': wh_id,
                        'stocks': stocks
                    }
            
            except Exception as e:
                print(f"Error fetching FBS stocks for warehouse {wh_name} ({wh_id}): {e}")
        
        return result
    
    def get_combined_stocks_by_article(self, supplier_article: str = None) -> Dict[str, any]:
        """
        Get combined FBO + FBS stocks, aggregated by supplier article
        
        Args:
            supplier_article: Filter by specific article (optional)
        
        Returns:
            Dictionary with structure:
            {
                "article1": {
                    "supplier_article": "article1",
                    "nm_id": 12345,
                    "barcodes": ["123", "456"],
                    "fbo_stock": 100,
                    "fbs_stock": 200,
                    "total_stock": 300,
                    "fbo_details": [...],  # Detailed records from Statistics API
                    "fbs_details": [...]   # Detailed records from Marketplace API
                },
                ...
            }
        """
        # Step 1: Get FBO stocks
        fbo_stocks = self.get_fbo_stocks()
        
        # Step 2: Filter by article if needed
        if supplier_article:
            fbo_stocks = [s for s in fbo_stocks if s.get('supplierArticle') == supplier_article]
        
        # Step 3: Extract unique barcodes
        barcodes = list(set(s.get('barcode') for s in fbo_stocks if s.get('barcode')))
        
        # Step 4: Get FBS stocks for these barcodes
        fbs_stocks_by_warehouse = self.get_fbs_stocks(barcodes)
        
        # Step 5: Aggregate by supplier article
        result = {}
        
        for record in fbo_stocks:
            article = record.get('supplierArticle')
            if not article:
                continue
            
            if article not in result:
                result[article] = {
                    'supplier_article': article,
                    'nm_id': record.get('nmId'),
                    'barcodes': set(),
                    'fbo_stock': 0,
                    'fbs_stock': 0,
                    'total_stock': 0,
                    'fbo_details': [],
                    'fbs_details': []
                }
            
            # Add barcode
            barcode = record.get('barcode')
            if barcode:
                result[article]['barcodes'].add(barcode)
            
            # Add FBO stock
            result[article]['fbo_stock'] += record.get('quantity', 0)
            result[article]['fbo_details'].append(record)
        
        # Add FBS stocks
        for wh_data in fbs_stocks_by_warehouse.values():
            for stock in wh_data['stocks']:
                sku = stock.get('sku')
                amount = stock.get('amount', 0)
                
                # Find which article this barcode belongs to
                for article, data in result.items():
                    if sku in data['barcodes']:
                        data['fbs_stock'] += amount
                        data['fbs_details'].append({
                            'warehouse_name': wh_data['warehouse_name'],
                            'warehouse_id': wh_data['warehouse_id'],
                            'barcode': sku,
                            'amount': amount
                        })
                        break
        
        # Calculate totals and convert sets to lists
        for article, data in result.items():
            data['barcodes'] = list(data['barcodes'])
            data['total_stock'] = data['fbo_stock'] + data['fbs_stock']
        
        return result
    
    def get_all_stocks_summary(self) -> Dict[str, int]:
        """
        Get summary of all stocks
        
        Returns:
            {
                "total_fbo": 1000,
                "total_fbs": 2000,
                "total": 3000,
                "articles_count": 50,
                "fbs_warehouses_count": 2
            }
        """
        stocks = self.get_combined_stocks_by_article()
        
        total_fbo = sum(s['fbo_stock'] for s in stocks.values())
        total_fbs = sum(s['fbs_stock'] for s in stocks.values())
        
        return {
            'total_fbo': total_fbo,
            'total_fbs': total_fbs,
            'total': total_fbo + total_fbs,
            'articles_count': len(stocks),
            'fbs_warehouses_count': len(self.get_fbs_warehouses())
        }


def test_dual_api():
    """Test the dual API fetcher"""
    config = get_config()
    fetcher = DualAPIStockFetcher(config.wildberries_api_key)
    
    print("\n" + "="*100)
    print("🧪 ТЕСТ: Dual API Stock Fetcher")
    print("="*100)
    
    # Test 1: Get summary
    print("\n📊 Тест 1: Получение общей статистики...")
    summary = fetcher.get_all_stocks_summary()
    
    print(f"✅ Общая статистика:")
    print(f"  - FBO остатков: {summary['total_fbo']} шт")
    print(f"  - FBS остатков: {summary['total_fbs']} шт")
    print(f"  - ВСЕГО: {summary['total']} шт")
    print(f"  - Артикулов: {summary['articles_count']}")
    print(f"  - FBS складов: {summary['fbs_warehouses_count']}")
    
    # Test 2: Get specific article
    print("\n📦 Тест 2: Получение данных для Its1_2_3/50g...")
    stocks = fetcher.get_combined_stocks_by_article('Its1_2_3/50g')
    
    if 'Its1_2_3/50g' in stocks:
        data = stocks['Its1_2_3/50g']
        
        print(f"✅ Its1_2_3/50g:")
        print(f"  - NM ID: {data['nm_id']}")
        print(f"  - Баркодов: {len(data['barcodes'])}")
        print(f"  - FBO остаток: {data['fbo_stock']} шт ({len(data['fbo_details'])} записей)")
        print(f"  - FBS остаток: {data['fbs_stock']} шт ({len(data['fbs_details'])} записей)")
        print(f"  - ИТОГО: {data['total_stock']} шт")
        
        print(f"\n  Баркоды: {data['barcodes']}")
        
        print(f"\n  FBO склады:")
        for detail in data['fbo_details'][:5]:
            wh = detail.get('warehouseName')
            qty = detail.get('quantity', 0)
            print(f"    - {wh}: {qty} шт")
        
        if len(data['fbo_details']) > 5:
            print(f"    ... и еще {len(data['fbo_details']) - 5}")
        
        print(f"\n  FBS склады:")
        for detail in data['fbs_details']:
            wh = detail.get('warehouse_name')
            qty = detail.get('amount', 0)
            print(f"    - {wh}: {qty} шт")
    else:
        print("❌ Its1_2_3/50g не найден")
    
    print("\n" + "="*100)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*100)


if __name__ == "__main__":
    test_dual_api()
