import pandas as pd
import numpy as np
from collections import defaultdict

# Загрузка данных WB с правильными параметрами
# Проверяем разделитель и кодировку
try:
    wb_df = pd.read_csv('27-10-2025 История остатков с 21-10-2025 по 27-10-2025_export.csv', 
                         encoding='utf-8-sig', sep=',')
except:
    wb_df = pd.read_csv('27-10-2025 История остатков с 21-10-2025 по 27-10-2025_export.csv', 
                         encoding='cp1251', sep=',')

# Загрузка данных Stock Tracker
st_df = pd.read_csv('Stock Tracker - Stock Tracker (1).csv', encoding='utf-8')

print("="*80)
print("АНАЛИЗ ДАННЫХ ИЗ WILDBERRIES")
print("="*80)

# Агрегируем данные WB по артикулам
wb_grouped = wb_df.groupby('Артикул продавца').agg({
    'Заказали, шт': 'sum',
    'Остатки на текущий день, шт': 'sum',
    'Склад': lambda x: ', '.join(sorted(set(x.dropna())))
}).reset_index()

wb_grouped.columns = ['Артикул продавца', 'Заказы WB', 'Остатки WB', 'Склады WB']

print("\nАгрегированные данные WB:")
print(wb_grouped.to_string(index=False))

print("\n" + "="*80)
print("АНАЛИЗ ДАННЫХ ИЗ STOCK TRACKER")
print("="*80)
print("\nДанные Stock Tracker:")
print(st_df[['Артикул продавца', 'Артикул товара', 'Заказы (всего)', 'Остатки (всего)']].to_string(index=False))

print("\n" + "="*80)
print("СРАВНЕНИЕ ДАННЫХ")
print("="*80)

# Объединяем данные для сравнения
comparison = pd.merge(
    wb_grouped[['Артикул продавца', 'Заказы WB', 'Остатки WB']], 
    st_df[['Артикул продавца', 'Артикул товара', 'Заказы (всего)', 'Остатки (всего)']], 
    on='Артикул продавца', 
    how='outer'
)

# Преобразуем в числа
comparison['Заказы (всего)'] = pd.to_numeric(comparison['Заказы (всего)'], errors='coerce').fillna(0)
comparison['Остатки (всего)'] = pd.to_numeric(comparison['Остатки (всего)'], errors='coerce').fillna(0)

# Рассчитываем отклонения
comparison['Разница заказов'] = comparison['Заказы WB'] - comparison['Заказы (всего)']
comparison['% отклонение заказов'] = np.where(
    comparison['Заказы WB'] != 0,
    (comparison['Разница заказов'] / comparison['Заказы WB'] * 100).round(2),
    0
)

comparison['Разница остатков'] = comparison['Остатки WB'] - comparison['Остатки (всего)']
comparison['% отклонение остатков'] = np.where(
    comparison['Остатки WB'] != 0,
    (comparison['Разница остатков'] / comparison['Остатки WB'] * 100).round(2),
    0
)

print("\nДетальное сравнение:")
print(comparison.to_string(index=False))

print("\n" + "="*80)
print("КРИТИЧЕСКИЕ РАСХОЖДЕНИЯ (более 5-10%)")
print("="*80)

problems = []

# Проверяем расхождения в заказах
orders_issues = comparison[abs(comparison['% отклонение заказов']) > 5]
if not orders_issues.empty:
    print("\n🔴 ПРОБЛЕМЫ С ЗАКАЗАМИ:")
    for _, row in orders_issues.iterrows():
        problem = {
            'type': 'orders',
            'article': row['Артикул продавца'],
            'wb_value': row['Заказы WB'],
            'st_value': row['Заказы (всего)'],
            'diff': row['Разница заказов'],
            'percent': row['% отклонение заказов']
        }
        problems.append(problem)
        print(f"\n  Артикул: {row['Артикул продавца']}")
        print(f"  WB показывает: {row['Заказы WB']} заказов")
        print(f"  Stock Tracker: {row['Заказы (всего)']} заказов")
        print(f"  Разница: {row['Разница заказов']} ({row['% отклонение заказов']}%)")
else:
    print("\n✅ Расхождений в заказах не обнаружено")

# Проверяем расхождения в остатках
stock_issues = comparison[abs(comparison['% отклонение остатков']) > 5]
if not stock_issues.empty:
    print("\n🔴 ПРОБЛЕМЫ С ОСТАТКАМИ:")
    for _, row in stock_issues.iterrows():
        problem = {
            'type': 'stock',
            'article': row['Артикул продавца'],
            'wb_value': row['Остатки WB'],
            'st_value': row['Остатки (всего)'],
            'diff': row['Разница остатков'],
            'percent': row['% отклонение остатков']
        }
        problems.append(problem)
        print(f"\n  Артикул: {row['Артикул продавца']}")
        print(f"  WB показывает: {row['Остатки WB']} шт")
        print(f"  Stock Tracker: {row['Остатки (всего)']} шт")
        print(f"  Разница: {row['Разница остатков']} ({row['% отклонение остатков']}%)")
else:
    print("\n✅ Расхождений в остатках не обнаружено")

# Проверяем отсутствующие артикулы
missing_in_st = comparison[comparison['Заказы (всего)'].isna() | (comparison['Заказы (всего)'] == 0)]
if not missing_in_st.empty and not missing_in_st['Заказы WB'].isna().all():
    print("\n⚠️ АРТИКУЛЫ ОТСУТСТВУЮТ ИЛИ НЕ СИНХРОНИЗИРОВАНЫ В STOCK TRACKER:")
    for _, row in missing_in_st.iterrows():
        if pd.notna(row['Заказы WB']) and row['Заказы WB'] > 0:
            print(f"\n  Артикул: {row['Артикул продавца']}")
            print(f"  WB показывает: {row['Заказы WB']} заказов, {row['Остатки WB']} остатков")
            print(f"  Stock Tracker: нет данных")

print("\n" + "="*80)
print("РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ ПРОБЛЕМ")
print("="*80)

if len(problems) > 0:
    print("\n1. СИНХРОНИЗАЦИЯ ДАННЫХ:")
    print("   - Проверьте корректность API-запросов к Wildberries")
    print("   - Убедитесь, что скрипт sync_stock_data.py корректно агрегирует данные")
    print("   - Проверьте временные метки синхронизации - возможно данные устарели")
    
    print("\n2. ПРОВЕРКА ФИЛЬТРОВ:")
    print("   - Убедитесь, что все склады учитываются при расчете")
    print("   - Проверьте, не фильтруются ли некоторые типы заказов/остатков")
    
    print("\n3. ФОРМУЛЫ В GOOGLE SHEETS:")
    print("   - Проверьте формулы суммирования в колонках 'Заказы (всего)' и 'Остатки (всего)'")
    print("   - Убедитесь, что все строки склада включены в расчет")
    
    print("\n4. ЛОГИКА ГРУППИРОВКИ:")
    print("   - WB предоставляет данные по каждому складу отдельно")
    print("   - Stock Tracker должен суммировать все склады для артикула")
    print("   - Проверьте функции warehouse_filtering.py и table_generation.py")
    
    print("\n5. НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ:")
    print("   - Запустите run_full_sync.py для полной пересинхронизации")
    print("   - Проверьте логи на наличие ошибок при получении данных от API")
    print("   - Сравните данные из API напрямую с данными в таблице")
else:
    print("\n✅ Критических расхождений не обнаружено!")
    print("   Данные синхронизированы корректно.")

print("\n" + "="*80)

# Сохраняем детальный отчет
comparison.to_csv('comparison_report.csv', index=False, encoding='utf-8-sig')
print("\n📊 Детальный отчет сохранен в файл: comparison_report.csv")
