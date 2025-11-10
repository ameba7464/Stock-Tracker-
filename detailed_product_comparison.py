#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальное сравнение данных по конкретному товару между официальной выгрузкой WB и таблицей Stock Tracker.
"""

import csv
import sys
import os
from collections import defaultdict

# Установка кодировки UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Пути к файлам
OFFICIAL_TSV = r"c:\Users\miros\Downloads\8-11-2025 История остатков с 02-11-2025 по 08-11-2025_export.tsv"
USER_TSV = r"c:\Users\miros\Downloads\Stock Tracker - Stock Tracker (4).tsv"

def parse_official_data(filepath, target_article):
    """Парсинг официальной выгрузки WB для конкретного товара."""
    data = {
        'warehouses': {},
        'total_orders': 0,
        'total_stock': 0
    }
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        for row in reader:
            article = row.get('Артикул продавца', '').strip()
            
            if article == target_article:
                warehouse = row.get('Склад', '').strip()
                orders = int(row.get('Заказали, шт', '0').strip() or '0')
                stock = int(row.get('Остатки на текущий день, шт', '0').strip() or '0')
                
                data['warehouses'][warehouse] = {
                    'orders': orders,
                    'stock': stock,
                    'region': row.get('Регион', '').strip()
                }
                
                data['total_orders'] += orders
                data['total_stock'] += stock
    
    return data

def parse_user_data(filepath, target_article):
    """Парсинг таблицы Stock Tracker для конкретного товара."""
    data = {
        'warehouses': {},
        'total_orders': 0,
        'total_stock': 0
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        for row in reader:
            article = row.get('Артикул продавца', '').strip()
            
            if article == target_article:
                # Парсинг общих данных
                # Убираем обычные и неразрывные пробелы
                total_orders_str = row.get('Заказы (всего)', '0').strip().replace(' ', '').replace('\xa0', '')
                total_stock_str = row.get('Остатки (всего)', '0').strip().replace(' ', '').replace('\xa0', '')
                data['total_orders'] = int(total_orders_str)
                data['total_stock'] = int(total_stock_str)
                
                # Парсинг складов
                warehouses_str = row.get('Название склада', '').strip()
                orders_str = row.get('Заказы со склада', '').strip()
                stock_str = row.get('Остатки на складе', '').strip()
                
                # Разделение по двум или более пробелам
                warehouses = [w.strip() for w in warehouses_str.split('  ') if w.strip()]
                orders_list = [o.strip() for o in orders_str.split('  ') if o.strip()]
                stock_list = [s.strip() for s in stock_str.split('  ') if s.strip()]
                
                # Создание словаря по складам
                for i, wh in enumerate(warehouses):
                    if i < len(orders_list) and i < len(stock_list):
                        data['warehouses'][wh] = {
                            'orders': int(orders_list[i].replace(' ', '')),
                            'stock': int(stock_list[i].replace(' ', ''))
                        }
                
                break
    
    return data

def normalize_warehouse_name(name):
    """Нормализация названия склада для сравнения."""
    # Убрать префиксы "СЦ "
    name = name.replace('СЦ ', '')
    # Убрать скобки
    name = name.replace('(', '').replace(')', '')
    # Нормализовать пробелы
    name = ' '.join(name.split())
    return name.strip()

def compare_products(official, user, article):
    """Детальное сравнение данных по товару."""
    print("=" * 120)
    print(f"📊 ДЕТАЛЬНОЕ СРАВНЕНИЕ ДЛЯ ТОВАРА: {article}")
    print("=" * 120)
    
    # Сравнение итогов
    print(f"\n{'':50} {'ОФИЦИАЛЬНО':>20} {'ТАБЛИЦА':>20} {'РАЗНИЦА':>20}")
    print("-" * 120)
    
    orders_diff = user['total_orders'] - official['total_orders']
    stock_diff = user['total_stock'] - official['total_stock']
    
    print(f"{'ИТОГО ЗАКАЗОВ:':<50} {official['total_orders']:>20} {user['total_orders']:>20} {orders_diff:>20}")
    print(f"{'ИТОГО ОСТАТКОВ:':<50} {official['total_stock']:>20} {user['total_stock']:>20} {stock_diff:>20}")
    
    # Детальное сравнение по складам
    print("\n" + "=" * 120)
    print("📦 ДЕТАЛЬНОЕ СРАВНЕНИЕ ПО СКЛАДАМ:")
    print("=" * 120)
    
    # Собираем все уникальные склады
    all_warehouses = set()
    all_warehouses.update(official['warehouses'].keys())
    all_warehouses.update(user['warehouses'].keys())
    
    # Нормализуем для сопоставления
    normalized_mapping = {}
    for wh in all_warehouses:
        norm = normalize_warehouse_name(wh)
        if norm not in normalized_mapping:
            normalized_mapping[norm] = []
        normalized_mapping[norm].append(wh)
    
    print(f"\n{'СКЛАД':<40} {'ОФИЦИАЛЬНО':>15} {'ТАБЛИЦА':>15} {'РАЗНИЦА':>15}")
    print(f"{'':40} {'Заказы/Остатки':>15} {'Заказы/Остатки':>15} {'Заказы/Остатки':>15}")
    print("-" * 120)
    
    # Критические расхождения
    critical_issues = []
    marketplace_analysis = []
    
    for norm_name, warehouse_variants in sorted(normalized_mapping.items()):
        # Найти склад в официальных данных
        official_wh = None
        for variant in warehouse_variants:
            if variant in official['warehouses']:
                official_wh = official['warehouses'][variant]
                break
        
        # Найти склад в пользовательских данных
        user_wh = None
        for variant in warehouse_variants:
            if variant in user['warehouses']:
                user_wh = user['warehouses'][variant]
                break
        
        # Получить значения
        off_orders = official_wh['orders'] if official_wh else 0
        off_stock = official_wh['stock'] if official_wh else 0
        user_orders = user_wh['orders'] if user_wh else 0
        user_stock = user_wh['stock'] if user_wh else 0
        
        # Разница
        diff_orders = user_orders - off_orders
        diff_stock = user_stock - off_stock
        
        # Определение статуса
        status = "✅"
        if abs(diff_orders) > 5 or abs(diff_stock) > 50:
            status = "🔴"
            critical_issues.append({
                'warehouse': norm_name,
                'official_orders': off_orders,
                'user_orders': user_orders,
                'official_stock': off_stock,
                'user_stock': user_stock,
                'diff_orders': diff_orders,
                'diff_stock': diff_stock
            })
        
        # Специальный анализ Маркетплейс
        if 'маркетплейс' in norm_name.lower() or 'marketplace' in norm_name.lower():
            marketplace_analysis.append({
                'warehouse': norm_name,
                'official_orders': off_orders,
                'user_orders': user_orders,
                'official_stock': off_stock,
                'user_stock': user_stock,
                'variants': warehouse_variants
            })
        
        # Вывод строки
        warehouse_display = norm_name[:38] + '..' if len(norm_name) > 40 else norm_name
        print(f"{status} {warehouse_display:<38} "
              f"{off_orders:>7}/{off_stock:>7} "
              f"{user_orders:>7}/{user_stock:>7} "
              f"{diff_orders:>7}/{diff_stock:>7}")
    
    # Анализ критических проблем
    if critical_issues:
        print("\n" + "=" * 120)
        print("🔴 КРИТИЧЕСКИЕ РАСХОЖДЕНИЯ (>5 заказов или >50 остатков):")
        print("=" * 120)
        
        for issue in critical_issues:
            print(f"\n📍 Склад: {issue['warehouse']}")
            print(f"   Заказы:  официально {issue['official_orders']:>5}, таблица {issue['user_orders']:>5}, разница {issue['diff_orders']:>+6}")
            print(f"   Остатки: официально {issue['official_stock']:>5}, таблица {issue['user_stock']:>5}, разница {issue['diff_stock']:>+6}")
            
            # Анализ причин
            if issue['user_orders'] > issue['official_orders'] * 2:
                print(f"   ⚠️  ПРОБЛЕМА: Таблица показывает в {issue['user_orders'] / max(issue['official_orders'], 1):.1f}x раз больше заказов!")
                print(f"       Возможная причина: Пропорциональное распределение или включение дополнительных событий")
            
            if issue['user_stock'] > 0 and issue['official_stock'] == 0:
                print(f"   ⚠️  ПРОБЛЕМА: В таблице {issue['user_stock']} остатков, официально 0!")
                print(f"       Возможная причина: Устаревшие данные из кэша")
            
            if issue['warehouse'] == 'Чехов 1' and issue['user_stock'] == 1:
                print(f"   ⚠️  КРИТИЧЕСКАЯ ПРОБЛЕМА: Склад отображается как '1'!")
                print(f"       Возможная причина: Некорректный парсинг названия склада")
    
    # Анализ Маркетплейс
    if marketplace_analysis:
        print("\n" + "=" * 120)
        print("🏪 АНАЛИЗ СКЛАДА 'МАРКЕТПЛЕЙС':")
        print("=" * 120)
        
        for mp in marketplace_analysis:
            print(f"\n📍 Варианты названия: {', '.join(mp['variants'])}")
            print(f"   Официально: {mp['official_orders']} заказов, {mp['official_stock']} остатков")
            print(f"   Таблица:    {mp['user_orders']} заказов, {mp['user_stock']} остатков")
            
            if mp['user_orders'] > mp['official_orders']:
                multiplier = mp['user_orders'] / max(mp['official_orders'], 1)
                print(f"   🔍 Таблица показывает в {multiplier:.1f}x раз больше заказов")
                print(f"      Возможные причины:")
                print(f"      - Пропорциональное распределение заказов по остаткам")
                print(f"      - Включение заказов 'в пути' или других статусов")
                print(f"      - Агрегация из нескольких источников (FBO + FBS)")
    
    # Рекомендации
    print("\n" + "=" * 120)
    print("💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
    print("=" * 120)
    
    if any('Чехов' in issue['warehouse'] for issue in critical_issues):
        print("\n1. Проблема с 'Чехов 1' → '1':")
        print("   - Добавить валидацию названий складов (должны содержать буквы)")
        print("   - Исправить парсинг при split() в compare_official_vs_user.py")
    
    if any('Маркетплейс' in mp['warehouse'] for mp in marketplace_analysis):
        if any(mp['user_orders'] > mp['official_orders'] * 1.5 for mp in marketplace_analysis):
            print("\n2. Проблема с избыточными заказами на 'Маркетплейс':")
            print("   - Убрать пропорциональное распределение заказов")
            print("   - Использовать точный подсчет из orders_data по warehouseName")
            print("   - Проверить фильтрацию статусов заказов (isCancel, в пути, и т.д.)")
    
    if any(issue['user_stock'] > 0 and issue['official_stock'] == 0 for issue in critical_issues):
        print("\n3. Проблема с устаревшими остатками:")
        print("   - Убедиться, что clear_all_products() вызывается перед синхронизацией")
        print("   - Пропускать склады с quantity=0 из API")
        print("   - Не добавлять склады, которых нет в текущих данных API")

def main():
    """Главная функция."""
    # Список товаров для анализа
    products_to_analyze = [
        'Its2/50g',           # Проблема: 3 vs 81 заказов на Маркетплейс
        'Its1_2_3/50g',       # Проблема: 3 vs 16 заказов на Маркетплейс
        'ItsSport2/50g',      # Проблема: 1 vs 14 заказов на Маркетплейс
    ]
    
    for article in products_to_analyze:
        official_data = parse_official_data(OFFICIAL_TSV, article)
        user_data = parse_user_data(USER_TSV, article)
        
        if not official_data['warehouses'] and not user_data['warehouses']:
            print(f"\n⚠️  Товар {article} не найден ни в одном из файлов")
            continue
        
        compare_products(official_data, user_data, article)
        print("\n\n")

if __name__ == "__main__":
    main()
