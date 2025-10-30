#!/usr/bin/env python
"""Проверка сырых данных из WB API для склада Обухово."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.config import get_config

def main():
    print("🔍 Диагностика данных склада 'Обухово'\n")
    print("=" * 60)
    
    config = get_config()
    client = WildberriesAPIClient()
    
    # Получаем сырые данные FBO
    print("\n📥 Получаем данные из Statistics API (FBO)...")
    fbo_stocks = client.get_statistics_stocks()  # Синхронный метод
    
    print(f"\n📊 Всего записей FBO: {len(fbo_stocks)}")
    
    # Ищем склады с "Обухово" в названии
    print("\n🔍 Склады содержащие 'Обухово':\n")
    
    obuhovo_variants = set()
    
    for stock in fbo_stocks:
        wh_name = stock.get('warehouseName', '')
        if 'Обухово' in wh_name or 'обухово' in wh_name.lower():
            qty = stock.get('quantityFull', 0)
            article = stock.get('supplierArticle', 'N/A')
            obuhovo_variants.add(wh_name)
            if qty > 0:  # Показываем только ненулевые остатки
                print(f"  FBO: '{wh_name}' | Артикул: {article} | Остаток: {qty}")
    
    print(f"\n📋 Все варианты названия 'Обухово' из WB API:")
    for variant in sorted(obuhovo_variants):
        print(f"  - '{variant}'")
    
    print("\n" + "=" * 60)
    print("✅ Диагностика завершена!")

if __name__ == "__main__":
    main()

