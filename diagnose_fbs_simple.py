#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая диагностика FBS проблемы без эмодзи
"""

import sys
import os

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.utils.warehouse_mapper import (
    normalize_warehouse_name,
    is_marketplace_warehouse
)
from stock_tracker.core.calculator import is_real_warehouse

def diagnose_warehouse_processing():
    """Диагностика обработки складов"""
    
    print("=" * 100)
    print("DIAGNOSTIKA FBS PROBLEMY")
    print("=" * 100)
    print()
    
    # Тестовые варианты названий склада
    test_variants = [
        "Маркетплейс",
        "маркетплейс",
        "Marketplace",
        "Маркетплейс ",  # с пробелом
        " Маркетплейс",  # с пробелом в начале
        "МП",
        "Склад продавца",
        "FBS",
    ]
    
    print("TEST 1: normalize_warehouse_name()")
    print("-" * 100)
    
    for variant in test_variants:
        normalized = normalize_warehouse_name(variant)
        is_in_map = normalized == "Маркетплейс"
        status = "[OK]" if is_in_map else "[FAIL]"
        
        print("{} '{}' -> '{}' | in map: {}".format(
            status, variant, normalized, is_in_map))
    
    print()
    print("TEST 2: is_marketplace_warehouse()")
    print("-" * 100)
    
    for variant in test_variants:
        is_marketplace = is_marketplace_warehouse(variant)
        status = "[OK]" if is_marketplace else "[FAIL]"
        
        print("{} '{}' -> is_marketplace: {}".format(
            status, variant, is_marketplace))
    
    print()
    print("TEST 3: is_real_warehouse()")
    print("-" * 100)
    
    for variant in test_variants:
        is_real = is_real_warehouse(variant)
        status = "[OK]" if is_real else "[FAIL]"
        
        print("{} '{}' -> is_real: {}".format(
            status, variant, is_real))
    
    print()
    print("TEST 4: Full processing cycle")
    print("-" * 100)
    
    for variant in test_variants:
        print("\nProcessing: '{}' (repr: {})".format(variant, repr(variant)))
        
        # Step 1: Normalization
        normalized = normalize_warehouse_name(variant)
        print("   1. normalize_warehouse_name() -> '{}'".format(normalized))
        
        # Step 2: Is real?
        is_real = is_real_warehouse(normalized)
        print("   2. is_real_warehouse() -> {}".format(is_real))
        
        if is_real:
            # Step 3: Is marketplace?
            is_marketplace = is_marketplace_warehouse(normalized)
            print("   3. is_marketplace_warehouse() -> {}".format(is_marketplace))
            
            if is_marketplace:
                print("   [OK] RESULT: Will be included as FBS")
            else:
                print("   [WARN] RESULT: Will be included as regular warehouse")
        else:
            print("   [FAIL] RESULT: Will be EXCLUDED (not real warehouse)")


def test_with_mock_api_data():
    """Тест с моковыми данными из API"""
    
    print("\n")
    print("=" * 100)
    print("TEST WITH MOCK API DATA")
    print("=" * 100)
    print()
    
    # Проблемные артикулы из анализа
    problematic_articles = [
        "Its2/50g",
        "ItsSport2/50g"
    ]
    
    # Рабочий артикул
    working_articles = [
        "Its2/50g+Aks5/20g.FBS"
    ]
    
    # Тестовые данные как будто из API
    mock_warehouse_names = [
        "Маркетплейс",      # стандартное название
        "Коледино",         # обычный склад WB
        "Подольск",         # обычный склад WB
    ]
    
    print("PROBLEMATIC ARTICLES (missing FBS stocks):")
    print("-" * 100)
    for article in problematic_articles:
        print("\nArticle: {}".format(article))
        for warehouse in mock_warehouse_names:
            normalized = normalize_warehouse_name(warehouse)
            is_real = is_real_warehouse(normalized)
            is_marketplace = is_marketplace_warehouse(normalized) if is_real else False
            
            result = "[FBS]" if (is_real and is_marketplace) else "[FBO]" if is_real else "[SKIP]"
            print("  {} warehouse='{}' -> normalized='{}' -> real={} marketplace={}".format(
                result, warehouse, normalized, is_real, is_marketplace))
    
    print()
    print("WORKING ARTICLES (correct FBS stocks):")
    print("-" * 100)
    for article in working_articles:
        print("\nArticle: {}".format(article))
        for warehouse in mock_warehouse_names:
            normalized = normalize_warehouse_name(warehouse)
            is_real = is_real_warehouse(normalized)
            is_marketplace = is_marketplace_warehouse(normalized) if is_real else False
            
            result = "[FBS]" if (is_real and is_marketplace) else "[FBO]" if is_real else "[SKIP]"
            print("  {} warehouse='{}' -> normalized='{}' -> real={} marketplace={}".format(
                result, warehouse, normalized, is_real, is_marketplace))


def main():
    """Основная функция"""
    print("\n")
    print("###" * 33)
    print("###  FBS STOCK LOSS DIAGNOSTIC TOOL")
    print("###" * 33)
    print()
    
    try:
        diagnose_warehouse_processing()
        test_with_mock_api_data()
        
        print("\n")
        print("=" * 100)
        print("DIAGNOSTIC COMPLETED")
        print("=" * 100)
        
    except Exception as e:
        print("\n[ERROR] Exception occurred:")
        print(str(e))
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
