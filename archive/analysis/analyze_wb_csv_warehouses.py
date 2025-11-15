"""
Анализ складов в WB CSV для ItsSport2/50g
"""
import csv

csv_file = "30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv"

print("\n" + "="*100)
print("АНАЛИЗ СКЛАДОВ В WB CSV ДЛЯ ItsSport2/50g")
print("="*100)

with open(csv_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    
    print(f"\nЗаголовки CSV:")
    for i, h in enumerate(header[:20]):
        print(f"  [{i}] {h}")
    
    print(f"\n\nДанные для ItsSport2/50g:")
    print(f"{'Артикул':<30} {'Округ':<25} {'Склад':<35} {'Остатки':<10}")
    print("-"*105)
    
    total = 0
    warehouses = {}
    
    for row in reader:
        if len(row) > 16:
            article_full = row[0]
            
            # Нормализуем артикул
            article_base = article_full.split('+')[0].split('.')[0]
            
            if article_base == 'ItsSport2/50g':
                okrug = row[6] if len(row) > 6 else ''
                warehouse = row[7] if len(row) > 7 else ''
                qty = int(row[16]) if row[16] and row[16].isdigit() else 0
                
                print(f"{article_full:<30} {okrug:<25} {warehouse:<35} {qty:<10}")
                
                total += qty
                
                if warehouse not in warehouses:
                    warehouses[warehouse] = 0
                warehouses[warehouse] += qty
    
    print("-"*105)
    print(f"{'ВСЕГО':<92} {total:<10}")
    
    print(f"\n\nСводка по складам:")
    print(f"{'Склад':<45} {'Остатки':<10}")
    print("-"*60)
    
    for wh, qty in sorted(warehouses.items(), key=lambda x: -x[1]):
        print(f"{wh:<45} {qty:<10}")
    
    print("="*100 + "\n")
