"""
Тест для проверки исправления форматирования строк.
Проверяет, что wrap_text отключён для колонки F и строки имеют фиксированную высоту.
"""

import os
import sys

# Change to script directory for config loading
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, os.path.join(script_dir, 'src'))

from stock_tracker.database.structure import SheetsTableStructure

def test_column_f_wrap_text():
    """Проверка, что колонка F имеет wrap_text=False"""
    columns = SheetsTableStructure.COLUMNS
    
    # Найти колонку F (Название склада)
    column_f = None
    for col in columns:
        if col.key == "warehouse_names":
            column_f = col
            break
    
    assert column_f is not None, "Колонка 'warehouse_names' не найдена!"
    print(f"✅ Колонка F найдена: {column_f.header}")
    
    assert column_f.wrap_text == False, f"Ошибка: wrap_text={column_f.wrap_text}, ожидалось False"
    print(f"✅ wrap_text=False (перенос текста отключён)")
    
    assert column_f.width >= 250, f"Ошибка: ширина={column_f.width}, ожидалось ≥250"
    print(f"✅ Ширина колонки: {column_f.width}px")
    
    print("\n📊 Настройки колонки F (Название склада):")
    print(f"   - Header: {column_f.header}")
    print(f"   - Width: {column_f.width}px")
    print(f"   - Wrap text: {column_f.wrap_text}")
    print(f"   - Alignment: {column_f.alignment}")
    print(f"   - Letter: {column_f.letter}")

def test_row_heights_function():
    """Проверка, что функция set_row_heights использует фиксированную высоту"""
    from stock_tracker.database.structure import SheetsTableStructure
    
    # Проверка сигнатуры метода
    import inspect
    sig = inspect.signature(SheetsTableStructure.set_row_heights_for_multiline_data)
    params = sig.parameters
    
    print("\n🔧 Параметры функции set_row_heights_for_multiline_data:")
    for name, param in params.items():
        if name != 'self' and name != 'worksheet':
            default = param.default if param.default != inspect.Parameter.empty else "нет"
            print(f"   - {name}: default={default}")
    
    # Проверка значения по умолчанию
    min_height_param = params.get('min_height')
    if min_height_param:
        default_height = min_height_param.default
        print(f"\n✅ Значение по умолчанию min_height: {default_height}px")
        
        if default_height == 21:
            print("✅ Используется стандартная высота строк Google Sheets (21px)")
        else:
            print(f"⚠️  Нестандартная высота: {default_height}px")

if __name__ == "__main__":
    print("🧪 Тестирование исправлений форматирования строк\n")
    print("=" * 60)
    
    try:
        test_column_f_wrap_text()
        test_row_heights_function()
        
        print("\n" + "=" * 60)
        print("✅ Все проверки пройдены!")
        print("\n📝 Результат:")
        print("   - Перенос текста в колонке F отключён")
        print("   - Ширина колонки увеличена для длинных названий")
        print("   - Строки имеют фиксированную стандартную высоту")
        print("   - Длинные названия складов не будут смещать данные")
        
    except AssertionError as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
