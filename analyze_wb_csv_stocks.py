"""
Analyze Its2/50g and ItsSport2/50g stocks from WB CSV
"""
import csv

csv_file = "28-10-2025 История остатков с 22-10-2025 по 28-10-2025_export (1).csv"

def analyze_stocks():
    articles = ['Its2/50g', 'ItsSport2/50g', 'Its1_2_3/50g']
    
    for target_article in articles:
        print(f"\n{'='*80}")
        print(f"{target_article} - WAREHOUSES IN WB CSV:")
        print(f"{'='*80}")
        
        total_stock = 0
        warehouses = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            # Skip first line (title)
            next(f)
            reader = csv.DictReader(f)
            
            for row in reader:
                article = row.get('Артикул продавца', '')
                if article == target_article:
                    warehouse = row.get('Склад', '')
                    stock_str = row.get('Остатки на текущий день, шт', '0')
                    stock = int(stock_str) if stock_str and stock_str.strip() else 0
                    
                    warehouses.append((warehouse, stock))
                    total_stock += stock
        
        # Print all warehouses
        for wh, stock in warehouses:
            print(f"  {wh:40s}: {stock:>6d} pcs")
        
        print(f"{'-'*80}")
        print(f"  {'TOTAL':40s}: {total_stock:>6d} pcs")
        print(f"{'='*80}")

if __name__ == '__main__':
    analyze_stocks()
