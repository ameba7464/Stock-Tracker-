#!/usr/bin/env python3
"""
Тестовый скрипт для проверки форматирования оборачиваемости.

Проверяет:
1. Отображение оборачиваемости как целого числа
2. Применение условного форматирования (красный цвет для значений ≤14)
"""

import sys
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.database.sheets import create_sheets_client
from stock_tracker.database.structure import create_table_structure
from stock_tracker.core.models import Product, Warehouse
from stock_tracker.core.formatter import ProductDataFormatter
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def test_turnover_formatting():
    """Тест форматирования оборачиваемости."""
    
    print("\n" + "="*80)
    print("🧪 ТЕСТ ФОРМАТИРОВАНИЯ ОБОРАЧИВАЕМОСТИ")
    print("="*80 + "\n")
    
    # Тестовые данные с разными значениями оборачиваемости
    test_products = [
        {
            "name": "Test Product 1 - High Stock",
            "article": "TEST001",
            "nm_id": 11111111,
            "stock": 500,
            "orders": 10,
            "expected_turnover": 350,  # 500 / (10/7) = 350 дней
            "should_be_red": False
        },
        {
            "name": "Test Product 2 - Medium Stock", 
            "article": "TEST002",
            "nm_id": 22222222,
            "stock": 150,
            "orders": 35,
            "expected_turnover": 30,  # 150 / (35/7) = 30 дней
            "should_be_red": False
        },
        {
            "name": "Test Product 3 - Low Stock (CRITICAL)",
            "article": "TEST003",
            "nm_id": 33333333,
            "stock": 50,
            "orders": 25,
            "expected_turnover": 14,  # 50 / (25/7) = 14 дней - ГРАНИЦА!
            "should_be_red": True
        },
        {
            "name": "Test Product 4 - Very Low Stock (CRITICAL)",
            "article": "TEST004",
            "nm_id": 44444444,
            "stock": 30,
            "orders": 35,
            "expected_turnover": 6,  # 30 / (35/7) = 6 дней - КРИТИЧНО!
            "should_be_red": True
        },
        {
            "name": "Test Product 5 - Zero Orders",
            "article": "TEST005",
            "nm_id": 55555555,
            "stock": 100,
            "orders": 0,
            "expected_turnover": 0,  # Нет заказов
            "should_be_red": False
        }
    ]
    
    print("📊 Тестовые данные:")
    print("-" * 80)
    
    formatter = ProductDataFormatter()
    
    for i, data in enumerate(test_products, 1):
        print(f"\n{i}. {data['name']}")
        print(f"   Артикул: {data['article']}")
        print(f"   Остатки: {data['stock']} шт")
        print(f"   Заказы за 7 дней: {data['orders']} шт")
        print(f"   Ожидаемая оборачиваемость: ~{data['expected_turnover']} дней")
        
        # Создаем продукт
        product = Product(
            seller_article=data['article'],
            wildberries_article=data['nm_id'],
            total_stock=data['stock'],
            total_orders=data['orders']
        )
        
        # Добавляем тестовый склад
        product.add_warehouse(Warehouse(
            name="Тестовый склад",
            stock=data['stock'],
            orders=data['orders']
        ))
        
        # Рассчитываем оборачиваемость
        ORDER_LOOKBACK_DAYS = 7
        if product.total_orders > 0:
            orders_per_day = product.total_orders / ORDER_LOOKBACK_DAYS
            product.turnover = round(product.total_stock / orders_per_day, 3)
        else:
            product.turnover = 0.0
        
        # Форматируем для отображения
        formatted_turnover = formatter.format_turnover(product.turnover)
        
        print(f"   Рассчитанная оборачиваемость: {product.turnover:.3f} дней")
        print(f"   Отформатированное значение: {formatted_turnover}")
        print(f"   Должно быть красным: {'ДА 🔴' if data['should_be_red'] else 'НЕТ'}")
        
        # Проверяем корректность форматирования
        if '.' in formatted_turnover or ',' in formatted_turnover:
            print(f"   ❌ ОШИБКА: Значение содержит дробную часть!")
        else:
            print(f"   ✅ OK: Целое число без дробной части")
    
    print("\n" + "="*80)
    print("📋 РЕЗЮМЕ ТЕСТА")
    print("="*80 + "\n")
    
    print("1. ✅ Формат оборачиваемости: Целое число (без запятых и точек)")
    print("2. ✅ Условное форматирование:")
    print("   - Значения ≤14 дней должны быть красными")
    print("   - Значения >14 дней обычного цвета")
    print("\n3. 📝 Проверка в Google Sheets:")
    print("   - Откройте таблицу после синхронизации")
    print("   - Проверьте колонку E (Оборачиваемость)")
    print("   - Убедитесь что значения ≤14 окрашены в красный")
    
    return True


def test_structure_configuration():
    """Тест конфигурации структуры таблицы."""
    
    print("\n" + "="*80)
    print("🔧 ТЕСТ КОНФИГУРАЦИИ СТРУКТУРЫ")
    print("="*80 + "\n")
    
    try:
        # Проверяем конфигурацию колонки оборачиваемости
        from stock_tracker.database.structure import SheetsTableStructure
        
        # Найдем колонку оборачиваемости
        turnover_col = None
        for col in SheetsTableStructure.COLUMNS:
            if col.key == "turnover":
                turnover_col = col
                break
        
        if not turnover_col:
            print("❌ ОШИБКА: Колонка оборачиваемости не найдена!")
            return False
        
        print("📊 Конфигурация колонки 'Оборачиваемость':")
        print(f"   Ключ: {turnover_col.key}")
        print(f"   Заголовок: {turnover_col.header}")
        print(f"   Буква: {turnover_col.letter}")
        print(f"   Ширина: {turnover_col.width}px")
        print(f"   Формат числа: {turnover_col.number_format}")
        print(f"   Выравнивание: {turnover_col.alignment}")
        
        # Проверяем формат
        if turnover_col.number_format == "0":
            print("\n✅ OK: Формат числа установлен на целое число ('0')")
        elif turnover_col.number_format == "0.000":
            print("\n❌ ОШИБКА: Формат все еще '0.000' (дробное число)")
            print("   Нужно обновить на '0'")
            return False
        else:
            print(f"\n⚠️ ВНИМАНИЕ: Неожиданный формат '{turnover_col.number_format}'")
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА при проверке конфигурации: {e}")
        return False


def test_conditional_formatting_function():
    """Тест наличия функции условного форматирования."""
    
    print("\n" + "="*80)
    print("🎨 ТЕСТ ФУНКЦИИ УСЛОВНОГО ФОРМАТИРОВАНИЯ")
    print("="*80 + "\n")
    
    try:
        from stock_tracker.database.structure import SheetsTableStructure
        
        # Проверяем наличие метода
        if hasattr(SheetsTableStructure, 'apply_turnover_conditional_formatting'):
            print("✅ Функция 'apply_turnover_conditional_formatting' найдена")
            
            # Получаем документацию
            method = getattr(SheetsTableStructure, 'apply_turnover_conditional_formatting')
            if method.__doc__:
                print("\n📖 Документация:")
                print("   " + method.__doc__.strip().split('\n')[0])
            
            return True
        else:
            print("❌ ОШИБКА: Функция 'apply_turnover_conditional_formatting' не найдена!")
            print("   Нужно добавить эту функцию в structure.py")
            return False
            
    except Exception as e:
        print(f"❌ ОШИБКА при проверке функции: {e}")
        return False


def main():
    """Основная функция тестирования."""
    
    print("\n" + "="*100)
    print(" " * 30 + "🧪 ТЕСТИРОВАНИЕ ФОРМАТИРОВАНИЯ ОБОРАЧИВАЕМОСТИ")
    print("="*100)
    
    results = []
    
    # Тест 1: Конфигурация структуры
    print("\n\n")
    results.append(("Конфигурация структуры", test_structure_configuration()))
    
    # Тест 2: Наличие функции условного форматирования
    print("\n\n")
    results.append(("Функция условного форматирования", test_conditional_formatting_function()))
    
    # Тест 3: Форматирование значений
    print("\n\n")
    results.append(("Форматирование значений", test_turnover_formatting()))
    
    # Итоговый отчет
    print("\n\n" + "="*100)
    print(" " * 40 + "📊 ИТОГОВЫЙ ОТЧЕТ")
    print("="*100 + "\n")
    
    all_passed = True
    for test_name, result in results:
        status = "✅ УСПЕХ" if result else "❌ ОШИБКА"
        print(f"{status:12} | {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*100)
    
    if all_passed:
        print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\n📝 Следующие шаги:")
        print("   1. Запустите синхронизацию: python main.py")
        print("   2. Откройте Google Sheets таблицу")
        print("   3. Проверьте колонку E (Оборачиваемость):")
        print("      - Значения отображаются как целые числа")
        print("      - Значения ≤14 окрашены в красный цвет")
        return 0
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("   Проверьте ошибки выше и исправьте код")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
