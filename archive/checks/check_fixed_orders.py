#!/usr/bin/env python3
"""
Проверка результатов исправления дублирования заказов.
Сравнивает НОВЫЕ данные Stock Tracker с эталонными значениями WB.
"""

import pandas as pd

print("="*80)
print("🎯 ПРОВЕРКА ИСПРАВЛЕНИЯ ДУБЛИРОВАНИЯ ЗАКАЗОВ")
print("="*80)

# Эталонные данные из WB API (из предыдущего анализа)
wb_reference = {
    "Its1_2_3/50g": {"orders": 7, "stock": 192},
    "Its2/50g": {"orders": 9, "stock": 132},
    "ItsSport2/50g": {"orders": 5, "stock": 185}
}

print("\n📊 Загрузка ОБНОВЛЕННЫХ данных Stock Tracker...")
st_df = pd.read_csv('Stock Tracker - Stock Tracker (1).csv')

# Обновляем CSV из Google Sheets перед проверкой
print("⚠️  ВНИМАНИЕ: Убедитесь, что CSV файл был скачан ПОСЛЕ синхронизации!")
print("   File → Download → Comma Separated Values (.csv)")
input("\nНажмите Enter после обновления CSV файла или Ctrl+C для выхода...")

st_df = pd.read_csv('Stock Tracker - Stock Tracker (1).csv')
print(f"✅ Загружено {len(st_df)} строк\n")

print("="*80)
print("📋 РЕЗУЛЬТАТЫ ПРОВЕРКИ")
print("="*80)

issues_found = []
success_count = 0

for article, expected in wb_reference.items():
    print(f"\n📦 {article}")
    print("-"*60)
    
    # Находим строку в ST
    st_row = st_df[st_df['Артикул продавца'] == article]
    
    if len(st_row) == 0:
        print(f"   ❌ Артикул не найден в Stock Tracker!")
        issues_found.append({
            "article": article,
            "issue": "not_found"
        })
        continue
    
    st_row = st_row.iloc[0]
    st_orders = int(st_row['Заказы (всего)']) if pd.notna(st_row['Заказы (всего)']) else 0
    st_stock = int(st_row['Остатки (всего)']) if pd.notna(st_row['Остатки (всего)']) else 0
    
    print(f"   WB Эталон:     {expected['orders']} заказов, {expected['stock']} остатков")
    print(f"   Stock Tracker: {st_orders} заказов, {st_stock} остатков")
    
    # Проверка заказов
    orders_match = st_orders == expected['orders']
    stock_match = st_stock == expected['stock']
    
    if orders_match and stock_match:
        print(f"   ✅ ИДЕАЛЬНОЕ СОВПАДЕНИЕ!")
        success_count += 1
    else:
        issue = {
            "article": article,
            "wb_orders": expected['orders'],
            "st_orders": st_orders,
            "wb_stock": expected['stock'],
            "st_stock": st_stock
        }
        issues_found.append(issue)
        
        if not orders_match:
            diff = st_orders - expected['orders']
            pct = (diff / expected['orders'] * 100) if expected['orders'] > 0 else 0
            
            if diff > 0:
                print(f"   ⚠️  ЗАКАЗЫ: +{diff} ({pct:+.1f}%) - ВСЕ ЕЩЕ ЗАВЫШЕНЫ")
            else:
                print(f"   ⚠️  ЗАКАЗЫ: {diff} ({pct:.1f}%) - ЗАНИЖЕНЫ")
        
        if not stock_match:
            diff = st_stock - expected['stock']
            pct = (diff / expected['stock'] * 100) if expected['stock'] > 0 else 0
            print(f"   ⚠️  ОСТАТКИ: {diff:+d} ({pct:+.1f}%)")

print("\n" + "="*80)
print("📈 ИТОГОВАЯ СТАТИСТИКА")
print("="*80)

print(f"\n✅ Успешно исправлено: {success_count}/3 продуктов ({success_count/3*100:.1f}%)")

if issues_found:
    print(f"❌ Проблемы обнаружены: {len(issues_found)}/3 продуктов")
    print("\n⚠️  ДЕТАЛИ ПРОБЛЕМ:")
    for issue in issues_found:
        if issue.get("issue") == "not_found":
            print(f"   • {issue['article']}: НЕ НАЙДЕН")
        else:
            print(f"   • {issue['article']}:")
            if issue['st_orders'] != issue['wb_orders']:
                print(f"     - Заказы: {issue['st_orders']} вместо {issue['wb_orders']}")
            if issue['st_stock'] != issue['wb_stock']:
                print(f"     - Остатки: {issue['st_stock']} вместо {issue['wb_stock']}")
else:
    print("\n🎉 ВСЕ ОТЛИЧНО!")
    print("✅ Дублирование заказов ПОЛНОСТЬЮ УСТРАНЕНО")
    print("✅ Данные Stock Tracker на 100% соответствуют WB API")

print("\n" + "="*80)

if success_count == 3:
    print("\n🎊 УСПЕХ! Исправления работают корректно!")
    print("📋 Рекомендация: Дождаться восстановления API quota и обновить оставшиеся 9 продуктов")
    exit(0)
else:
    print("\n⚠️  Требуется дополнительная проверка")
    print("📋 Рекомендация: Проверить логи синхронизации и код дедупликации")
    exit(1)
