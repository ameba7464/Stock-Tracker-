"""
Детальная проверка логики нормализации имен складов и записи остатков
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name, is_marketplace_warehouse

def test_warehouse_normalization():
    """Проверка нормализации имен складов"""
    
    print("\n" + "="*100)
    print("ПРОВЕРКА НОРМАЛИЗАЦИИ ИМЕН СКЛАДОВ")
    print("="*100)
    
    # Тестовые варианты названий складов из реальных данных
    test_cases = [
        # FBS склады
        ("Fulllog FBS", "Маркетплейс"),
        ("Маркетплейс", "Маркетплейс"),
        ("FBS", "Маркетплейс"),
        ("Склад продавца", "Маркетплейс"),
        
        # Проблемный случай - разные варианты одного склада
        ("Новосемейкино", "?"),
        ("Самара (Новосемейкино)", "?"),
        ("Новосемейкино (FBO)", "?"),
        
        # Другие склады WB
        ("Чехов 1", "?"),
        ("Рязань (Тюшевское)", "?"),
        ("Электросталь", "?"),
        ("Краснодар", "?"),
        ("Котовск", "?"),
        ("Подольск 3", "?"),
    ]
    
    print("\nТестирование нормализации:")
    print(f"{'Исходное название':<40} {'Нормализованное':<30} {'FBS?':<10}")
    print("-" * 80)
    
    for original, expected in test_cases:
        normalized = normalize_warehouse_name(original)
        is_fbs = is_marketplace_warehouse(original)
        
        status = ""
        if expected != "?":
            status = "[OK]" if normalized == expected else f"[FAIL] expected: {expected}"
        
        print(f"{original:<40} {normalized:<30} {str(is_fbs):<10} {status}")
    
    print("\n" + "="*100)
    print("АНАЛИЗ ПРОБЛЕМЫ")
    print("="*100)
    
    # Проверяем конкретную проблему
    name1 = "Новосемейкино"
    name2 = "Самара (Новосемейкино)"
    
    norm1 = normalize_warehouse_name(name1)
    norm2 = normalize_warehouse_name(name2)
    
    print(f"\nПроблемный случай:")
    print(f"  '{name1}' -> '{norm1}'")
    print(f"  '{name2}' -> '{norm2}'")
    
    if norm1 != norm2:
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА] Разные названия для одного склада!")
        print(f"  Это приводит к дублированию остатков!")
        print(f"  WB CSV использует: '{name2}'")
        print(f"  Tracker может получить от API: '{name1}'")
        print(f"  Результат: склад появляется дважды с разными остатками")
    else:
        print(f"\n[OK] Оба варианта нормализуются одинаково: '{norm1}'")

if __name__ == '__main__':
    test_warehouse_normalization()
