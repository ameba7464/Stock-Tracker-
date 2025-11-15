#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка реальных названий складов из API для проблемных артикулов
"""

import sys
import os

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.api.wildberries_client import WildberriesAPIClient
from stock_tracker.core.calculator import is_real_warehouse
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name, is_marketplace_warehouse

def check_api_warehouse_names():
    """Проверка реальных названий складов из API"""
    
    print("=" * 100)
    print("PROVERKA REALNYH NAZVANIY SKLADOV IZ API")
    print("=" * 100)
    print()
    
    # Загружаем конфигурацию
    config = get_config()
    
    # Создаем клиент API
    client = WildberriesAPIClient(config)
    
    # Проблемные артикулы
    problematic_articles = ["Its2/50g", "ItsSport2/50g"]
    working_articles = ["Its2/50g+Aks5/20g.FBS"]
    
    print("[INFO] Zagruzka dannyh iz Statistics API...")
    
    try:
        # Получаем данные из Statistics API (FBO)
        stats_data = client.get_statistics()
        
        print("[OK] Polucheno {} zapisej iz Statistics API".format(len(stats_data)))
        print()
        
        # Анализируем проблемные артикулы
        print("PROBLEMNNYE ARTIKULY:")
        print("-" * 100)
        
        for article in problematic_articles:
            print("\nArticle: {}".format(article))
            article_data = [item for item in stats_data if item.get('subject') == article]
            
            if article_data:
                print("  [OK] Najdeno {} zapisej".format(len(article_data)))
                
                # Собираем уникальные склады
                warehouses = set()
                for item in article_data:
                    wh = item.get('warehouseName', '')
                    if wh:
                        warehouses.add(wh)
                
                print("  Unikalnye sklady (vsego {}):".format(len(warehouses)))
                for wh in sorted(warehouses):
                    normalized = normalize_warehouse_name(wh)
                    is_real = is_real_warehouse(wh)
                    is_mp = is_marketplace_warehouse(wh)
                    
                    status = "[FBS]" if (is_real and is_mp) else "[FBO]" if is_real else "[SKIP]"
                    print("    {} '{}' -> normalized='{}' | real={} | marketplace={}".format(
                        status, wh, normalized, is_real, is_mp))
            else:
                print("  [WARN] Net zapisej v Statistics API")
        
        print()
        print("RABOCHIE ARTIKULY:")
        print("-" * 100)
        
        for article in working_articles:
            print("\nArticle: {}".format(article))
            article_data = [item for item in stats_data if item.get('subject') == article]
            
            if article_data:
                print("  [OK] Najdeno {} zapisej".format(len(article_data)))
                
                # Собираем уникальные склады
                warehouses = set()
                for item in article_data:
                    wh = item.get('warehouseName', '')
                    if wh:
                        warehouses.add(wh)
                
                print("  Unikalnye sklady (vsego {}):".format(len(warehouses)))
                for wh in sorted(warehouses):
                    normalized = normalize_warehouse_name(wh)
                    is_real = is_real_warehouse(wh)
                    is_mp = is_marketplace_warehouse(wh)
                    
                    status = "[FBS]" if (is_real and is_mp) else "[FBO]" if is_real else "[SKIP]"
                    print("    {} '{}' -> normalized='{}' | real={} | marketplace={}".format(
                        status, wh, normalized, is_real, is_mp))
            else:
                print("  [WARN] Net zapisej v Statistics API")
        
    except Exception as e:
        print("[ERROR] Oshibka pri poluchenii dannyh iz API:")
        print(str(e))
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    
    # Теперь проверяем Marketplace API (FBS)
    print()
    print("=" * 100)
    print("PROVERKA MARKETPLACE API (FBS)")
    print("=" * 100)
    print()
    
    try:
        # Получаем склады из Marketplace API
        print("[INFO] Zagruzka dannyh iz Marketplace API...")
        marketplace_data = client.get_stocks()
        
        print("[OK] Polucheno {} zapisej iz Marketplace API".format(len(marketplace_data)))
        print()
        
        # Анализируем проблемные артикулы
        print("PROBLEMNNYE ARTIKULY:")
        print("-" * 100)
        
        for article in problematic_articles:
            print("\nArticle: {}".format(article))
            article_data = [item for item in marketplace_data if item.get('subject') == article]
            
            if article_data:
                print("  [OK] Najdeno {} zapisej".format(len(article_data)))
                
                # Собираем уникальные склады
                warehouses = set()
                for item in article_data:
                    wh = item.get('warehouseName', '')
                    if wh:
                        warehouses.add(wh)
                
                print("  Unikalnye sklady (vsego {}):".format(len(warehouses)))
                for wh in sorted(warehouses):
                    normalized = normalize_warehouse_name(wh)
                    is_real = is_real_warehouse(wh)
                    is_mp = is_marketplace_warehouse(wh)
                    
                    status = "[FBS]" if (is_real and is_mp) else "[FBO]" if is_real else "[SKIP]"
                    print("    {} '{}' (repr: {}) -> normalized='{}' | real={} | marketplace={}".format(
                        status, wh, repr(wh), normalized, is_real, is_mp))
                    
                    # Детальный анализ каждого символа
                    if wh:
                        print("      Bytes: {}".format([hex(ord(c)) for c in wh]))
            else:
                print("  [WARN] Net zapisej v Marketplace API")
        
        print()
        print("RABOCHIE ARTIKULY:")
        print("-" * 100)
        
        for article in working_articles:
            print("\nArticle: {}".format(article))
            article_data = [item for item in marketplace_data if item.get('subject') == article]
            
            if article_data:
                print("  [OK] Najdeno {} zapisej".format(len(article_data)))
                
                # Собираем уникальные склады
                warehouses = set()
                for item in article_data:
                    wh = item.get('warehouseName', '')
                    if wh:
                        warehouses.add(wh)
                
                print("  Unikalnye sklady (vsego {}):".format(len(warehouses)))
                for wh in sorted(warehouses):
                    normalized = normalize_warehouse_name(wh)
                    is_real = is_real_warehouse(wh)
                    is_mp = is_marketplace_warehouse(wh)
                    
                    status = "[FBS]" if (is_real and is_mp) else "[FBO]" if is_real else "[SKIP]"
                    print("    {} '{}' (repr: {}) -> normalized='{}' | real={} | marketplace={}".format(
                        status, wh, repr(wh), normalized, is_real, is_mp))
                    
                    # Детальный анализ каждого символа
                    if wh:
                        print("      Bytes: {}".format([hex(ord(c)) for c in wh]))
            else:
                print("  [WARN] Net zapisej v Marketplace API")
                
    except Exception as e:
        print("[ERROR] Oshibka pri poluchenii dannyh iz Marketplace API:")
        print(str(e))
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print("=" * 100)
    print("PROVERKA ZAVERSHENA")
    print("=" * 100)
    
    return 0


if __name__ == "__main__":
    sys.exit(check_api_warehouse_names())
