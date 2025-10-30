#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностический скрипт для выявления проблемы с FBS остатками

Проверяет каждый этап обработки данных для артикулов:
- Its2/50g (проблемный)
- Its2/50g+Aks5/20g.FBS (рабочий)
"""

import sys
import json
from pathlib import Path

# Добавляем путь к модулям проекта
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.utils.warehouse_mapper import (
    normalize_warehouse_name,
    is_marketplace_warehouse
)
from stock_tracker.core.calculator import is_real_warehouse

def diagnose_warehouse_processing():
    """Диагностика обработки складов для проблемных артикулов"""
    
    print("=" * 100)
    print("DIAGNOSTIKA FBS PROBLEMY")
    print("=" * 100)
    print()
    
    # Тестовые варианты названий склада "Маркетплейс"
    test_variants = [
        "Маркетплейс",
        "маркетплейс",
        "Marketplace",
        "marketplace",
        "Маркетплейс ",  # с пробелом
        " Маркетплейс",  # с пробелом в начале
        "Маркетплейс\t",  # с табом
        "МП",
        "мп",
        "MP",
        "mp",
        "Склад продавца",
        "склад продавца",
        "Seller warehouse",
        "FBS",
        "fbs",
    ]
    
    print("📋 ТЕСТ 1: Проверка normalize_warehouse_name()")
    print("-" * 100)
    
    for variant in test_variants:
        normalized = normalize_warehouse_name(variant)
        is_in_map = normalized == "Маркетплейс"
        status = "✅" if is_in_map else "❌"
        
        print(f"{status} '{variant}' -> '{normalized}' | in map: {is_in_map}")
    
    print()
    print("📋 ТЕСТ 2: Проверка is_marketplace_warehouse()")
    print("-" * 100)
    
    for variant in test_variants:
        is_marketplace = is_marketplace_warehouse(variant)
        status = "✅" if is_marketplace else "❌"
        
        print(f"{status} '{variant}' -> is_marketplace: {is_marketplace}")
    
    print()
    print("📋 ТЕСТ 3: Проверка is_real_warehouse()")
    print("-" * 100)
    
    for variant in test_variants:
        is_real = is_real_warehouse(variant)
        status = "✅" if is_real else "❌"
        
        print(f"{status} '{variant}' -> is_real: {is_real}")
    
    print()
    print("📋 ТЕСТ 4: Полный цикл обработки")
    print("-" * 100)
    
    for variant in test_variants:
        print(f"\n🔍 Обработка: '{variant}' (repr: {repr(variant)})")
        
        # Шаг 1: Нормализация
        normalized = normalize_warehouse_name(variant)
        print(f"   1. normalize_warehouse_name() -> '{normalized}'")
        
        # Шаг 2: Проверка реальности
        is_real = is_real_warehouse(normalized)
        print(f"   2. is_real_warehouse() -> {is_real}")
        
        if is_real:
            # Шаг 3: Проверка маркетплейса
            is_marketplace = is_marketplace_warehouse(normalized)
            print(f"   3. is_marketplace_warehouse() -> {is_marketplace}")
            
            if is_marketplace:
                print(f"   ✅ РЕЗУЛЬТАТ: Склад будет ВКЛЮЧЕН как FBS")
            else:
                print(f"   ⚠️  РЕЗУЛЬТАТ: Склад будет включен как обычный")
        else:
            print(f"   ❌ РЕЗУЛЬТАТ: Склад будет ИСКЛЮЧЕН")
    
    print()
    print("=" * 100)
    print("📊 ПРИМЕЧАНИЕ: Проверка внутренней карты складов")
    print("=" * 100)
    print()
    
    print("Карта складов находится в src/stock_tracker/utils/warehouse_mapper.py")
    print("Для детальной проверки см. файл напрямую")
    
    print()
    print("=" * 100)
    print("🔍 АНАЛИЗ ВОЗМОЖНЫХ ПРОБЛЕМ")
    print("=" * 100)
    print()
    
    problems_found = [
        {
            "severity": "HIGH",
            "issue": "Возможно отсутствуют варианты с пробелами",
            "impact": "Если API возвращает 'Маркетплейс ' (с пробелом) - оно может не распознаваться",
            "solution": "Проверить наличие вариантов с пробелами в карте"
        },
        {
            "severity": "MEDIUM",
            "issue": "Возможно отсутствуют короткие варианты (МП, mp)",
            "impact": "Если API использует сокращения - они могут не распознаваться",
            "solution": "Проверить наличие коротких вариантов в карте"
        }
    ]
    
    if problems_found:
        print("⚠️ ОБНАРУЖЕНЫ ПОТЕНЦИАЛЬНЫЕ ПРОБЛЕМЫ:")
        print()
        for i, problem in enumerate(problems_found, 1):
            print(f"{i}. [{problem['severity']}] {problem['issue']}")
            print(f"   Влияние: {problem['impact']}")
            print(f"   Решение: {problem['solution']}")
            print()
    else:
        print("✅ Проблем в картах не обнаружено")
    
    print()
    print("=" * 100)
    print("💡 РЕКОМЕНДАЦИИ")
    print("=" * 100)
    print()
    
    print("1. Добавить детальное логирование в group_data_by_product():")
    print("   - Логировать RAW названия складов из API")
    print("   - Логировать результат normalize_warehouse_name()")
    print("   - Логировать результат is_real_warehouse()")
    print()
    
    print("2. Запустить синхронизацию с логированием:")
    print("   python update_table_fixed.py")
    print("   (Искать в логах артикулы Its2/50g и ItsSport2/50g)")
    print()
    
    print("3. Анализировать логи на предмет:")
    print("   - Какое RAW название приходит из API")
    print("   - Проходит ли normalize_warehouse_name()")
    print("   - Проходит ли is_real_warehouse()")
    print()
    
    print("4. После выявления причины применить одно из решений:")
    print("   - Расширить CANONICAL_WAREHOUSE_MAP")
    print("   - Добавить нечеткое сравнение в normalize_warehouse_name()")
    print("   - Добавить fallback в is_real_warehouse()")
    print()


def test_with_mock_api_data():
    """Тест с имитацией данных API"""
    
    print("=" * 100)
    print("🧪 ТЕСТ С ИМИТАЦИЕЙ API ДАННЫХ")
    print("=" * 100)
    print()
    
    # Имитация данных для проблемного артикула
    mock_data_problem = {
        "nmId": 163383327,
        "vendorCode": "Its2/50g",
        "warehouses": [
            {"warehouseName": "Маркетплейс", "quantity": 1884},
            {"warehouseName": "Чехов 1", "quantity": 212},
            {"warehouseName": "Рязань (Тюшевское)", "quantity": 87},
        ]
    }
    
    # Имитация данных для рабочего артикула
    mock_data_working = {
        "nmId": 552086752,
        "vendorCode": "Its2/50g+Aks5/20g.FBS",
        "warehouses": [
            {"warehouseName": "Маркетплейс", "quantity": 175},
        ]
    }
    
    print("📦 ПРОБЛЕМНЫЙ АРТИКУЛ: Its2/50g")
    print("-" * 100)
    process_mock_product(mock_data_problem)
    
    print()
    print("📦 РАБОЧИЙ АРТИКУЛ: Its2/50g+Aks5/20g.FBS")
    print("-" * 100)
    process_mock_product(mock_data_working)


def process_mock_product(product_data):
    """Обработка имитации данных продукта"""
    
    vendor_code = product_data["vendorCode"]
    nm_id = product_data["nmId"]
    
    print(f"Артикул: {vendor_code} (nmId: {nm_id})")
    print()
    
    included_warehouses = []
    excluded_warehouses = []
    
    for warehouse in product_data["warehouses"]:
        wh_name_raw = warehouse["warehouseName"]
        quantity = warehouse["quantity"]
        
        print(f"🔍 Обработка склада: '{wh_name_raw}' (qty: {quantity})")
        
        # Шаг 1: Нормализация
        wh_name_normalized = normalize_warehouse_name(wh_name_raw)
        print(f"   1. Нормализация: '{wh_name_raw}' -> '{wh_name_normalized}'")
        
        # Шаг 2: Проверка реальности
        is_real = is_real_warehouse(wh_name_normalized)
        print(f"   2. is_real_warehouse(): {is_real}")
        
        if is_real:
            # Шаг 3: Проверка маркетплейса
            is_marketplace = is_marketplace_warehouse(wh_name_normalized)
            print(f"   3. is_marketplace_warehouse(): {is_marketplace}")
            
            included_warehouses.append({
                "raw": wh_name_raw,
                "normalized": wh_name_normalized,
                "quantity": quantity,
                "is_fbs": is_marketplace
            })
            
            status = "FBS" if is_marketplace else "FBO"
            print(f"   ✅ ВКЛЮЧЕН как {status}")
        else:
            excluded_warehouses.append({
                "raw": wh_name_raw,
                "normalized": wh_name_normalized,
                "quantity": quantity
            })
            print(f"   ❌ ИСКЛЮЧЕН")
        
        print()
    
    # Итоги
    print("📊 ИТОГИ ОБРАБОТКИ:")
    print(f"   Включено складов: {len(included_warehouses)}")
    print(f"   Исключено складов: {len(excluded_warehouses)}")
    
    total_stock = sum(wh["quantity"] for wh in included_warehouses)
    fbs_stock = sum(wh["quantity"] for wh in included_warehouses if wh["is_fbs"])
    fbo_stock = total_stock - fbs_stock
    
    print(f"   Всего остатков: {total_stock}")
    print(f"   FBS остатки: {fbs_stock}")
    print(f"   FBO остатки: {fbo_stock}")
    
    if excluded_warehouses:
        excluded_stock = sum(wh["quantity"] for wh in excluded_warehouses)
        print(f"   ⚠️ ПОТЕРЯНО остатков: {excluded_stock}")


if __name__ == "__main__":
    diagnose_warehouse_processing()
    print("\n" * 2)
    test_with_mock_api_data()
