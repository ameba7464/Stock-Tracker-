#!/usr/bin/env python3
"""
Анализ данных WB CSV - альтернативный подход
"""

import csv
import json
from collections import defaultdict

def analyze_wb_data_raw():
    """Анализ CSV файла от WB через raw CSV reader"""
    csv_file = r"c:\Users\miros\Downloads\24-10-2025-a-s-18-10-2025-po-24-10-2025_export.csv"
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if len(rows) < 2:
            print("Недостаточно данных в файле")
            return None
        
        headers = rows[0]
        data_rows = rows[1:]
        
        print(f"Загружено {len(data_rows)} строк данных")
        print(f"Заголовки ({len(headers)}): {headers}")
        
        # Найдем индексы важных колонок
        try:
            article_idx = headers.index('Артикул продавца')
            warehouse_idx = headers.index('Склад')
            region_idx = headers.index('Регион')
            orders_idx = headers.index('Заказали, шт')
            stock_idx = headers.index('Остатки на текущий день, шт')
        except ValueError as e:
            print(f"Не найдена колонка: {e}")
            return None
        
        print(f"\nИндексы колонок:")
        print(f"  Артикул продавца: {article_idx}")
        print(f"  Склад: {warehouse_idx}")
        print(f"  Регион: {region_idx}")
        print(f"  Заказали, шт: {orders_idx}")
        print(f"  Остатки: {stock_idx}")
        
        # Анализ складов
        warehouses = set()
        marketplace_data = []
        fbs_articles = set()
        
        for i, row in enumerate(data_rows):
            if len(row) <= max(article_idx, warehouse_idx, region_idx, orders_idx, stock_idx):
                print(f"Строка {i+2} имеет недостаточно колонок: {len(row)}")
                continue
                
            article = row[article_idx].strip()
            warehouse = row[warehouse_idx].strip()
            region = row[region_idx].strip()
            orders = row[orders_idx].strip()
            stock = row[stock_idx].strip()
            
            warehouses.add(warehouse)
            
            if warehouse == 'Маркетплейс':
                marketplace_data.append({
                    'article': article,
                    'warehouse': warehouse,
                    'region': region,
                    'orders': orders,
                    'stock': stock
                })
            
            if '.FBS' in article:
                fbs_articles.add(article)
        
        print(f"\nВсего складов: {len(warehouses)}")
        print("Список всех складов:")
        for w in sorted(warehouses):
            print(f"  - '{w}'")
        
        print(f"\nДанные по складу 'Маркетплейс': {len(marketplace_data)} записей")
        if marketplace_data:
            print("Записи по Маркетплейс:")
            for item in marketplace_data[:5]:  # Первые 5 записей
                print(f"  {item['article']}: заказы={item['orders']}, остатки={item['stock']}")
        
        print(f"\nТовары с расширением .FBS: {len(fbs_articles)}")
        if fbs_articles:
            print("FBS артикулы:")
            for article in sorted(fbs_articles):
                print(f"  - {article}")
        
        # Анализ критичных примеров
        print("\n=== АНАЛИЗ КРИТИЧНЫХ ПРИМЕРОВ ===")
        
        # ItsSport2/50g - пример с разрывом по остаткам >1000 шт
        itssport_marketplace = [item for item in marketplace_data if item['article'] == 'ItsSport2/50g']
        print(f"\nItsSport2/50g на Маркетплейс: {len(itssport_marketplace)} записей")
        for item in itssport_marketplace:
            print(f"  Заказы: {item['orders']}, Остатки: {item['stock']}")
        
        # Its1_2_3/50g - пример с Чехов 1
        chehov_data = []
        for row in data_rows:
            if len(row) > warehouse_idx and row[article_idx] == 'Its1_2_3/50g' and row[warehouse_idx] == 'Чехов 1':
                chehov_data.append({
                    'orders': row[orders_idx],
                    'stock': row[stock_idx]
                })
        
        print(f"\nIts1_2_3/50g на складе 'Чехов 1': {len(chehov_data)} записей")
        for item in chehov_data:
            print(f"  Заказы: {item['orders']}, Остатки: {item['stock']}")
        
        # Анализ проблемы с дублированием названий складов
        print("\n=== АНАЛИЗ ДУБЛИРОВАНИЯ СКЛАДОВ ===")
        warehouse_patterns = defaultdict(list)
        
        for warehouse in warehouses:
            # Ищем базовое название (убираем дополнительные обозначения)
            base_name = warehouse.split(',')[0].split('(')[0].strip()
            warehouse_patterns[base_name].append(warehouse)
        
        # Найдем дубликаты
        duplicates = {k: v for k, v in warehouse_patterns.items() if len(v) > 1}
        if duplicates:
            print("Найдены потенциальные дубликаты складов:")
            for base, variants in duplicates.items():
                print(f"  Базовое название '{base}':")
                for variant in variants:
                    count = sum(1 for row in data_rows if len(row) > warehouse_idx and row[warehouse_idx] == variant)
                    print(f"    - '{variant}' ({count} записей)")
        
        # Сохраним анализ в JSON
        analysis_result = {
            'total_records': len(data_rows),
            'total_warehouses': len(warehouses),
            'marketplace_records': len(marketplace_data),
            'fbs_records': len(fbs_articles),
            'warehouse_list': sorted(warehouses),
            'fbs_articles': sorted(fbs_articles),
            'warehouse_duplicates': duplicates,
            'marketplace_examples': marketplace_data[:10],  # Первые 10 примеров
            'chehov_examples': chehov_data
        }
        
        with open('wb_data_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"\nАнализ сохранен в wb_data_analysis.json")
        
        return analysis_result
        
    except Exception as e:
        print(f"Ошибка при анализе данных: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    analyze_wb_data_raw()