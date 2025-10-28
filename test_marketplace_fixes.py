"""
Тесты для проверки исправлений детекции складов Маркетплейс.

Дата: 26.10.2025
Цель: Проверить что все исправления корректно работают и Маркетплейс склады больше НЕ фильтруются.
"""

import sys
import os

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from stock_tracker.core.calculator import is_real_warehouse
from stock_tracker.utils.warehouse_mapper import (
    normalize_warehouse_name,
    is_marketplace_warehouse,
    WAREHOUSE_NAME_MAPPINGS
)


def test_marketplace_detection():
    """Тест 1: Проверка детекции всех вариантов Маркетплейс."""
    print("=" * 80)
    print("ТЕСТ 1: Детекция всех вариантов названий Маркетплейс/FBS")
    print("=" * 80)
    
    # Все возможные варианты названий Маркетплейс из реальных данных WB
    marketplace_variants = [
        # Основные
        "Маркетплейс",
        "маркетплейс",
        "МАРКЕТПЛЕЙС",
        "Marketplace",
        "marketplace",
        
        # С номерами
        "Маркетплейс-1",
        "Маркетплейс 1",
        "Marketplace-1",
        "Marketplace 1",
        
        # Сокращения
        "МП",
        "МП-1",
        "МП 1",
        "MP",
        "MP-1",
        "MP 1",
        "СП-1",
        
        # Полные названия
        "Склад продавца",
        "Склад Продавца",
        "Склад селлера",
        "Seller Warehouse",
        
        # FBS
        "FBS",
        "FBS-1",
        "FBS Warehouse",
        "FBS Storage",
        "Fulfillment by Seller",
        
        # С уточнениями
        "Маркетплейс (FBS)",
        "Marketplace (FBS)",
        "Склад продавца (FBS)",
        
        # Вариации написания
        "Маркет плейс",
        "Market place"
    ]
    
    failed = []
    passed = 0
    
    for variant in marketplace_variants:
        is_detected = is_marketplace_warehouse(variant)
        
        if is_detected:
            print(f"✅ PASS: '{variant}' -> Detected as Marketplace")
            passed += 1
        else:
            print(f"❌ FAIL: '{variant}' -> NOT detected as Marketplace")
            failed.append(variant)
    
    print("\n" + "-" * 80)
    print(f"Результат: {passed}/{len(marketplace_variants)} вариантов распознано")
    
    if failed:
        print(f"\n⚠️ НЕ РАСПОЗНАНО {len(failed)} вариантов:")
        for f in failed:
            print(f"   - {f}")
        return False
    else:
        print("\n✅ ВСЕ варианты Маркетплейс успешно распознаются!")
        return True


def test_is_real_warehouse_includes_marketplace():
    """Тест 2: is_real_warehouse() НЕ должна фильтровать Маркетплейс."""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: is_real_warehouse() включает все варианты Маркетплейс")
    print("=" * 80)
    
    marketplace_variants = [
        "Маркетплейс",
        "Marketplace",
        "МП-1",
        "MP-1",
        "Склад продавца",
        "FBS Warehouse",
        "FBS-1"
    ]
    
    failed = []
    passed = 0
    
    for variant in marketplace_variants:
        is_included = is_real_warehouse(variant)
        
        if is_included:
            print(f"✅ PASS: is_real_warehouse('{variant}') = True")
            passed += 1
        else:
            print(f"❌ FAIL: is_real_warehouse('{variant}') = False (SHOULD BE TRUE!)")
            failed.append(variant)
    
    print("\n" + "-" * 80)
    print(f"Результат: {passed}/{len(marketplace_variants)} вариантов пропущено is_real_warehouse()")
    
    if failed:
        print(f"\n⚠️ ОТФИЛЬТРОВАНО {len(failed)} вариантов (КРИТИЧЕСКАЯ ОШИБКА!):")
        for f in failed:
            print(f"   - {f}")
        return False
    else:
        print("\n✅ ВСЕ варианты Маркетплейс корректно ВКЛЮЧЕНЫ в is_real_warehouse()!")
        return True


def test_warehouse_mapper_normalization():
    """Тест 3: warehouse_mapper корректно нормализует к 'Маркетплейс'."""
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Нормализация всех вариантов к каноническому 'Маркетплейс'")
    print("=" * 80)
    
    marketplace_variants = [
        "Маркетплейс",
        "marketplace",
        "Marketplace-1",
        "МП-1",
        "MP-1",
        "Склад продавца",
        "FBS Warehouse",
        "Seller Warehouse"
    ]
    
    failed = []
    passed = 0
    
    for variant in marketplace_variants:
        normalized = normalize_warehouse_name(variant)
        
        if normalized == "Маркетплейс":
            print(f"✅ PASS: normalize('{variant}') -> 'Маркетплейс'")
            passed += 1
        else:
            print(f"❌ FAIL: normalize('{variant}') -> '{normalized}' (expected 'Маркетплейс')")
            failed.append((variant, normalized))
    
    print("\n" + "-" * 80)
    print(f"Результат: {passed}/{len(marketplace_variants)} вариантов нормализовано корректно")
    
    if failed:
        print(f"\n⚠️ НЕКОРРЕКТНАЯ НОРМАЛИЗАЦИЯ {len(failed)} вариантов:")
        for variant, got in failed:
            print(f"   - '{variant}' -> '{got}' (ожидалось 'Маркетплейс')")
        return False
    else:
        print("\n✅ ВСЕ варианты корректно нормализуются к 'Маркетплейс'!")
        return True


def test_regular_warehouses_not_broken():
    """Тест 4: Обычные склады всё ещё работают корректно."""
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Обычные склады (не Маркетплейс) корректно обрабатываются")
    print("=" * 80)
    
    regular_warehouses = [
        ("Новосемейкино", True),
        ("Чехов 1", True),
        ("Подольск 3", True),
        ("Тула", True),
        ("Белые Столбы", True),
        
        # Должны фильтроваться
        ("Итого", False),
        ("В пути", False),
        ("Отправлен", False),
        ("123", False),  # только цифры
        ("", False),  # пустая строка
    ]
    
    failed = []
    passed = 0
    
    for warehouse, should_include in regular_warehouses:
        is_included = is_real_warehouse(warehouse)
        
        if is_included == should_include:
            status = "INCLUDED" if is_included else "FILTERED"
            print(f"✅ PASS: '{warehouse}' -> {status} (expected)")
            passed += 1
        else:
            expected_status = "INCLUDED" if should_include else "FILTERED"
            actual_status = "INCLUDED" if is_included else "FILTERED"
            print(f"❌ FAIL: '{warehouse}' -> {actual_status} (expected {expected_status})")
            failed.append((warehouse, expected_status, actual_status))
    
    print("\n" + "-" * 80)
    print(f"Результат: {passed}/{len(regular_warehouses)} складов обработано корректно")
    
    if failed:
        print(f"\n⚠️ НЕКОРРЕКТНАЯ ОБРАБОТКА {len(failed)} складов:")
        for wh, expected, got in failed:
            print(f"   - '{wh}': {got} (ожидалось {expected})")
        return False
    else:
        print("\n✅ ВСЕ обычные склады корректно обрабатываются!")
        return True


def test_warehouse_mappings_extended():
    """Тест 5: Справочник WAREHOUSE_NAME_MAPPINGS содержит все варианты."""
    print("\n" + "=" * 80)
    print("ТЕСТ 5: Справочник WAREHOUSE_NAME_MAPPINGS расширен всеми вариантами")
    print("=" * 80)
    
    required_marketplace_variants = [
        "Маркетплейс", "Marketplace",
        "МП-1", "MP-1",
        "Склад продавца", "Seller Warehouse",
        "FBS", "FBS Warehouse"
    ]
    
    marketplace_mappings = WAREHOUSE_NAME_MAPPINGS.get("Маркетплейс", [])
    
    print(f"Всего вариантов в справочнике для 'Маркетплейс': {len(marketplace_mappings)}")
    print(f"Первые 10 вариантов: {marketplace_mappings[:10]}")
    
    missing = []
    found = 0
    
    for variant in required_marketplace_variants:
        if variant in marketplace_mappings or variant == "Маркетплейс":
            print(f"✅ PASS: '{variant}' найден в справочнике")
            found += 1
        else:
            print(f"❌ FAIL: '{variant}' ОТСУТСТВУЕТ в справочнике")
            missing.append(variant)
    
    print("\n" + "-" * 80)
    print(f"Результат: {found}/{len(required_marketplace_variants)} критичных вариантов в справочнике")
    
    if missing:
        print(f"\n⚠️ ОТСУТСТВУЮТ {len(missing)} критичных вариантов:")
        for m in missing:
            print(f"   - {m}")
        return False
    else:
        print("\n✅ ВСЕ критичные варианты присутствуют в справочнике!")
        return True


def run_all_tests():
    """Запустить все тесты."""
    print("\n" + "=" * 80)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ МАРКЕТПЛЕЙС")
    print("Дата: 26.10.2025")
    print("=" * 80)
    
    results = []
    
    # Запускаем все тесты
    results.append(("Детекция вариантов Маркетплейс", test_marketplace_detection()))
    results.append(("is_real_warehouse() включает Маркетплейс", test_is_real_warehouse_includes_marketplace()))
    results.append(("Нормализация к 'Маркетплейс'", test_warehouse_mapper_normalization()))
    results.append(("Обычные склады работают", test_regular_warehouses_not_broken()))
    results.append(("Справочник расширен", test_warehouse_mappings_extended()))
    
    # Итоговый отчет
    print("\n" + "=" * 80)
    print("ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n" + "-" * 80)
    print(f"Успешно: {passed}/{total} тестов ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Исправления работают корректно.")
        print("\n✅ КРИТИЧЕСКАЯ ПРОБЛЕМА РЕШЕНА:")
        print("   - Маркетплейс склады больше НЕ фильтруются")
        print("   - Все варианты названий распознаются")
        print("   - Нормализация работает корректно")
        print("   - Обычные склады не сломаны")
        return True
    else:
        print(f"\n⚠️ ПРОВАЛЕНО {total - passed} тестов!")
        print("\nТребуются дополнительные исправления.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
