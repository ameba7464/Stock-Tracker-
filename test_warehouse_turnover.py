#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности оборачиваемости по складам.

Этот скрипт тестирует:
1. Расчет оборачиваемости для склада
2. Форматирование данных для Google Sheets
3. Парсинг данных из Google Sheets
"""

from stock_tracker.core.models import Product, Warehouse
from stock_tracker.core.formatter import ProductDataFormatter


def test_warehouse_turnover_calculation():
    """Тест расчета оборачиваемости для склада."""
    print("\n" + "="*80)
    print("ТЕСТ 1: Расчет оборачиваемости для склада")
    print("="*80)
    
    # Создаем склад с заказами и остатками
    warehouse1 = Warehouse(name="СЦ Волгоград", orders=32, stock=654)
    
    print(f"Склад: {warehouse1.name}")
    print(f"  Заказы: {warehouse1.orders}")
    print(f"  Остатки: {warehouse1.stock}")
    print(f"  Оборачиваемость: {warehouse1.turnover}")
    print(f"  Ожидаемая: {32//654}")
    
    assert warehouse1.turnover == 32//654, "Оборачиваемость рассчитана неверно!"
    print("✅ Расчет оборачиваемости корректен")
    
    # Тест с нулевыми остатками
    warehouse2 = Warehouse(name="СЦ Москва", orders=10, stock=0)
    print(f"\nСклад с нулевыми остатками: {warehouse2.name}")
    print(f"  Заказы: {warehouse2.orders}")
    print(f"  Остатки: {warehouse2.stock}")
    print(f"  Оборачиваемость: {warehouse2.turnover}")
    
    assert warehouse2.turnover == 0, "При нулевых остатках оборачиваемость должна быть 0!"
    print("✅ Обработка нулевых остатков корректна")


def test_warehouse_turnover_formatting():
    """Тест форматирования оборачиваемости по складам."""
    print("\n" + "="*80)
    print("ТЕСТ 2: Форматирование для Google Sheets")
    print("="*80)
    
    # Создаем продукт с несколькими складами
    product = Product(seller_article="TEST-001", wildberries_article=12345678)
    
    warehouse1 = Warehouse(name="СЦ Волгоград", orders=32, stock=654)
    warehouse2 = Warehouse(name="СЦ Москва", orders=60, stock=453)
    warehouse3 = Warehouse(name="СЦ Екатеринбург", orders=15, stock=200)
    
    product.add_warehouse(warehouse1)
    product.add_warehouse(warehouse2)
    product.add_warehouse(warehouse3)
    
    # Форматируем для Sheets
    formatter = ProductDataFormatter()
    row_data = formatter.format_product_for_sheets(product)
    
    print(f"\nПродукт: {product.seller_article}")
    print(f"  Всего складов: {len(product.warehouses)}")
    print(f"  Колонок в строке: {len(row_data)}")
    
    assert len(row_data) == 9, f"Ожидается 9 колонок, получено {len(row_data)}"
    print("✅ Количество колонок корректно")
    
    # Проверяем колонку I (индекс 8) - оборачиваемость по складам
    warehouse_turnover_str = row_data[8]
    print(f"\nКолонка I (Оборачиваемость по складам):")
    print(f"{warehouse_turnover_str}")
    
    # Проверяем что есть данные
    assert warehouse_turnover_str, "Оборачиваемость по складам не должна быть пустой!"
    
    # Проверяем количество строк (должно быть 3 склада с двойными переносами)
    lines = [line.strip() for line in warehouse_turnover_str.split('\n') if line.strip()]
    assert len(lines) == 3, f"Ожидается 3 значения оборачиваемости, получено {len(lines)}"
    print(f"✅ Количество значений корректно: {len(lines)}")
    
    # Проверяем формат значений (должны быть целые числа)
    for i, line in enumerate(lines):
        try:
            value = int(line)
            print(f"  Склад {i+1}: {value}")
        except ValueError:
            raise AssertionError(f"Значение '{line}' не является целым числом!")
    
    print("✅ Все значения в правильном формате")


def test_warehouse_turnover_parsing():
    """Тест парсинга оборачиваемости из Google Sheets."""
    print("\n" + "="*80)
    print("ТЕСТ 3: Парсинг из Google Sheets")
    print("="*80)
    
    # Симулируем данные из Google Sheets (9 колонок)
    row_data = [
        "TEST-001",                           # A: Артикул продавца
        "12345678",                           # B: Артикул товара
        "107",                                # C: Заказы (всего)
        "1307",                               # D: Остатки (всего)
        "0",                                  # E: Оборачиваемость
        "СЦ Волгоград\n\nСЦ Москва\n\nСЦ Екатеринбург",  # F: Названия складов
        "32\n\n60\n\n15",                     # G: Заказы со склада
        "654\n\n453\n\n200",                  # H: Остатки на складе
        "0\n\n0\n\n0"                         # I: Оборачиваемость по складам (целые числа)
    ]
    
    formatter = ProductDataFormatter()
    product = formatter.parse_product_from_sheets_row(row_data, row_number=2)
    
    assert product is not None, "Не удалось распарсить продукт!"
    print(f"✅ Продукт распарсен: {product.seller_article}")
    
    assert len(product.warehouses) == 3, f"Ожидается 3 склада, получено {len(product.warehouses)}"
    print(f"✅ Количество складов корректно: {len(product.warehouses)}")
    
    # Проверяем оборачиваемость каждого склада (целые числа)
    expected_turnovers = [0, 0, 0]  # 32//654=0, 60//453=0, 15//200=0
    for i, (warehouse, expected) in enumerate(zip(product.warehouses, expected_turnovers)):
        print(f"\nСклад {i+1}: {warehouse.name}")
        print(f"  Заказы: {warehouse.orders}")
        print(f"  Остатки: {warehouse.stock}")
        print(f"  Оборачиваемость: {warehouse.turnover}")
        print(f"  Ожидаемая: {expected}")
        
        assert warehouse.turnover == expected, \
            f"Оборачиваемость склада {warehouse.name} неверна!"
    
    print("\n✅ Все значения оборачиваемости корректны")


def test_product_method():
    """Тест нового метода get_warehouse_turnover()."""
    print("\n" + "="*80)
    print("ТЕСТ 4: Метод Product.get_warehouse_turnover()")
    print("="*80)
    
    product = Product(seller_article="TEST-002", wildberries_article=87654321)
    
    warehouse1 = Warehouse(name="Склад 1", orders=10, stock=100)
    warehouse2 = Warehouse(name="Склад 2", orders=25, stock=150)
    
    product.add_warehouse(warehouse1)
    product.add_warehouse(warehouse2)
    
    turnover_str = product.get_warehouse_turnover()
    print(f"Результат метода get_warehouse_turnover():")
    print(f"{turnover_str}")
    
    lines = [line.strip() for line in turnover_str.split('\n') if line.strip()]
    assert len(lines) == 2, f"Ожидается 2 значения, получено {len(lines)}"
    
    # Проверяем значения (целые числа)
    expected = [0, 0]  # 10//100=0, 25//150=0
    for i, (line, exp) in enumerate(zip(lines, expected)):
        value = int(line)
        print(f"  Склад {i+1}: {value} (ожидается {exp})")
        assert value == exp, f"Значение {value} не совпадает с ожидаемым {exp}"
    
    print("✅ Метод get_warehouse_turnover() работает корректно")


def run_all_tests():
    """Запуск всех тестов."""
    print("\n" + "="*80)
    print("ЗАПУСК ТЕСТОВ: Оборачиваемость по складам")
    print("="*80)
    
    try:
        test_warehouse_turnover_calculation()
        test_warehouse_turnover_formatting()
        test_warehouse_turnover_parsing()
        test_product_method()
        
        print("\n" + "="*80)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("="*80 + "\n")
        
        return True
        
    except AssertionError as e:
        print("\n" + "="*80)
        print(f"❌ ТЕСТ ПРОВАЛЕН: {e}")
        print("="*80 + "\n")
        return False
    
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ ОШИБКА ПРИ ВЫПОЛНЕНИИ ТЕСТА: {e}")
        print("="*80 + "\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
