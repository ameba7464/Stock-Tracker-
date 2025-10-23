#!/usr/bin/env python3
"""
Тест маппинга данных API v2 на 8-колоночную структуру таблицы.

Проверяет, что данные из Analytics API v2 правильно маппятся на 
изначальную структуру из 8 колонок без добавления лишних полей.
"""

import asyncio
import sys
import os

# Добавляем путь к источникам
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.api.client import create_wildberries_client
from stock_tracker.core.models import Product, Warehouse
from stock_tracker.core.formatter import ProductDataFormatter
from stock_tracker.database.structure import SheetsTableStructure
from stock_tracker.utils.config import get_config


def test_api_v2_data_structure():
    """Тест структуры данных API v2."""
    print("🔍 Тестирование структуры данных API v2...")
    
    # Создаем тестовые данные, имитирующие ответ API v2
    api_v2_item = {
        "nmID": 12345678,
        "supplierArticle": "WB001",
        "ordersCount": 95,
        "stockCount": 1107,
        "subjectID": 123,
        "brandName": "Test Brand",
        "tagID": 456,
        # другие поля API v2...
    }
    
    # Создаем продукт из данных API v2
    product = Product.from_api_v2_data(api_v2_item)
    
    # Добавляем тестовые склады
    product.add_warehouse(Warehouse(name="СЦ Волгоград", orders=32, stock=654))
    product.add_warehouse(Warehouse(name="СЦ Москва", orders=60, stock=453))
    
    print(f"✅ Создан продукт: {product.seller_article} ({product.wildberries_article})")
    print(f"   Дополнительные поля API v2:")
    print(f"   - subject_id: {product.subject_id}")
    print(f"   - brand_name: {product.brand_name}")
    print(f"   - tag_id: {product.tag_id}")
    print(f"   - Складов: {len(product.warehouses)}")
    
    return product


def test_table_structure():
    """Тест структуры таблицы - должно быть строго 8 колонок."""
    print("\n📊 Тестирование структуры таблицы...")
    
    # Проверяем определение колонок
    columns = SheetsTableStructure.COLUMNS
    print(f"✅ Количество колонок: {len(columns)}")
    
    if len(columns) != 8:
        print(f"❌ ОШИБКА: Ожидалось 8 колонок, получено {len(columns)}")
        return False
    
    # Выводим структуру колонок
    print("   Структура колонок:")
    for i, col in enumerate(columns):
        print(f"   {chr(ord('A') + i)}: {col.header} ({col.key})")
    
    return True


def test_data_formatting():
    """Тест форматирования данных - должна создаваться строка из 8 элементов."""
    print("\n🔧 Тестирование форматирования данных...")
    
    # Создаем тестовый продукт
    product = test_api_v2_data_structure()
    
    # Форматируем для Google Sheets
    formatter = ProductDataFormatter()
    row_data = formatter.format_product_for_sheets(product)
    
    print(f"✅ Размер строки: {len(row_data)} элементов")
    
    if len(row_data) != 8:
        print(f"❌ ОШИБКА: Ожидалось 8 элементов, получено {len(row_data)}")
        return False
    
    # Выводим содержимое строки
    print("   Содержимое строки:")
    column_names = [
        "Артикул продавца", "Артикул товара", "Заказы (всего)", 
        "Остатки (всего)", "Оборачиваемость", "Название склада",
        "Заказы со склада", "Остатки на складе"
    ]
    
    for i, (name, value) in enumerate(zip(column_names, row_data)):
        print(f"   {chr(ord('A') + i)} - {name}: {repr(value)}")
    
    # Проверяем, что дополнительные поля API v2 НЕ включены в строку
    row_str = str(row_data)
    if any(field in row_str for field in ["subject_id", "brand_name", "tag_id"]):
        print("❌ ОШИБКА: Дополнительные поля API v2 обнаружены в строке таблицы!")
        return False
    else:
        print("✅ Дополнительные поля API v2 НЕ включены в строку таблицы")
    
    return True


async def test_api_connection():
    """Тест подключения к API v2."""
    print("\n🌐 Тестирование подключения к API v2...")
    
    try:
        client = create_wildberries_client()
        
        # Проверяем конфигурацию
        print(f"   Base URL: {client.base_url}")
        print(f"   Есть API ключ: {bool(client.api_key)}")
        
        # Тестируем подключение
        result = client.test_connection()
        
        if result["success"]:
            print("✅ Подключение к API v2 успешно")
            print(f"   API версия: {result['api_version']}")
            print(f"   Endpoint: {result['endpoint']}")
            print(f"   Есть тестовые данные: {result['sample_data']}")
            return True
        else:
            print(f"❌ Ошибка подключения: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение при тестировании API: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()


def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестов маппинга API v2 на 8-колоночную структуру")
    print("=" * 60)
    
    tests = [
        ("Структура таблицы", test_table_structure),
        ("Форматирование данных", test_data_formatting),
        ("Подключение к API", lambda: asyncio.run(test_api_connection()))
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    # Результаты
    print("\n" + "=" * 60)
    print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    
    all_passed = True
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\n🎯 Общий результат: {'✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if all_passed else '❌ ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ'}")
    
    if all_passed:
        print("\n✨ Структура данных корректна:")
        print("   - API v2 данные правильно маппятся на 8 колонок")
        print("   - Дополнительные поля API v2 не добавляются как колонки")
        print("   - Используется изначальная запроектированная структура")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)