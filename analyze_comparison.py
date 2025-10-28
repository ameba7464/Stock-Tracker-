import pandas as pd
import numpy as np

print("="*80)
print("ЧТЕНИЕ ФАЙЛОВ")
print("="*80)

# Читаем CSV из вложения напрямую - используем структуру из attachment
wb_data = {
    'Its1_2_3/50g': {'orders': 98, 'stock': 485},  # 20+18+13+13+11+10+5+4+2+2 = 98 заказов из детального CSV
    'Its2/50g': {'orders': 72, 'stock': 500},       # 24+23+8+7+6+3+1 = 72 заказа
    'ItsSport2/50g': {'orders': 34, 'stock': 250},  # 9+9+7+5+1+1+1+1 = 34 заказа
    'Its2/50g+Aks5/20g': {'orders': 20, 'stock': 0},
    'Its1_2_3/50g+Aks5/20g': {'orders': 10, 'stock': 0},
    'Its1_2_3/50g+Aks5/20g.FBS': {'orders': 4, 'stock': 0},
    'ItsSport2/50g+Aks5/20g': {'orders': 8, 'stock': 0},
    'Its1_2_3/50g+AksPoly/20g': {'orders': 5, 'stock': 96},
    'Its1_2_3/50g+AksRecov/20g': {'orders': 0, 'stock': 2},
    'Its2/50g+AksDef/20g': {'orders': 3, 'stock': 0},
    'ItsSport2/50g+Aks5/20g.FBS': {'orders': 2, 'stock': 0},
    'Its2/50g+Aks5/20g.FBS': {'orders': 3, 'stock': 0},
}

# Читаем Stock Tracker данные
st_df = pd.read_csv('Stock Tracker - Stock Tracker (1).csv', encoding='utf-8')

print("\nДанные из Stock Tracker:")
print(st_df[['Артикул продавца', 'Заказы (всего)', 'Остатки (всего)']].to_string(index=False))

print("\n" + "="*80)
print("СРАВНЕНИЕ ДАННЫХ")
print("="*80)

problems = []
total_issues = 0

for article, wb_values in wb_data.items():
    st_row = st_df[st_df['Артикул продавца'] == article]
    
    if st_row.empty:
        print(f"\n⚠️ Артикул {article} не найден в Stock Tracker")
        continue
    
    st_orders = float(str(st_row['Заказы (всего)'].values[0]).replace(',', '.'))
    st_stock = float(str(st_row['Остатки (всего)'].values[0]).replace(',', '.'))
    
    wb_orders = wb_values['orders']
    wb_stock = wb_values['stock']
    
    # Рассчитываем отклонения
    orders_diff = wb_orders - st_orders
    stock_diff = wb_stock - st_stock
    
    orders_percent = (orders_diff / wb_orders * 100) if wb_orders != 0 else 0
    stock_percent = (stock_diff / wb_stock * 100) if wb_stock != 0 else 0
    
    has_issue = False
    
    print(f"\n{'='*60}")
    print(f"Артикул: {article}")
    print(f"{'='*60}")
    
    # Проверяем заказы
    if abs(orders_percent) > 5:
        has_issue = True
        total_issues += 1
        print(f"🔴 ПРОБЛЕМА С ЗАКАЗАМИ:")
        print(f"   WB:           {wb_orders} заказов")
        print(f"   Stock Tracker: {st_orders} заказов")
        print(f"   Разница:       {orders_diff} ({orders_percent:.2f}%)")
        problems.append({
            'article': article,
            'type': 'orders',
            'wb': wb_orders,
            'st': st_orders,
            'diff': orders_diff,
            'percent': orders_percent
        })
    else:
        print(f"✅ Заказы: WB={wb_orders}, ST={st_orders} (разница {orders_percent:.2f}%)")
    
    # Проверяем остатки
    if abs(stock_percent) > 5:
        has_issue = True
        total_issues += 1
        print(f"🔴 ПРОБЛЕМА С ОСТАТКАМИ:")
        print(f"   WB:            {wb_stock} шт")
        print(f"   Stock Tracker: {st_stock} шт")
        print(f"   Разница:       {stock_diff} ({stock_percent:.2f}%)")
        problems.append({
            'article': article,
            'type': 'stock',
            'wb': wb_stock,
            'st': st_stock,
            'diff': stock_diff,
            'percent': stock_percent
        })
    else:
        print(f"✅ Остатки: WB={wb_stock}, ST={st_stock} (разница {stock_percent:.2f}%)")

print("\n" + "="*80)
print(f"ИТОГОВЫЙ РЕЗУЛЬТАТ: Обнаружено {total_issues} проблем(ы)")
print("="*80)

if len(problems) > 0:
    print("\n" + "="*80)
    print("РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ ПРОБЛЕМ")
    print("="*80)
    
    print("\n1️⃣ СИНХРОНИЗАЦИЯ ДАННЫХ:")
    print("   • Запустите полную ре-синхронизацию: python run_full_sync.py")
    print("   • Проверьте API токен и права доступа к Wildberries API")
    print("   • Убедитесь, что sync_stock_data.py корректно работает")
    
    print("\n2️⃣ ПРОВЕРКА ФИЛЬТРОВ:")
    print("   • Файл warehouse_filtering.py - проверьте логику фильтрации складов")
    print("   • Убедитесь, что все типы складов учитываются (Баланс, Актуальный, Неликвид)")
    print("   • Проверьте, не исключаются ли склады с маленькими остатками")
    
    print("\n3️⃣ ФОРМУЛЫ В GOOGLE SHEETS:")
    print("   • Колонка 'Заказы (всего)' должна суммировать ВСЕ строки склада")
    print("   • Колонка 'Остатки (всего)' должна суммировать ВСЕ остатки по складам")
    print("   • Проверьте диапазоны SUMIF/SUMIFS формул")
    
    print("\n4️⃣ ЛОГИКА ГРУППИРОВКИ ДАННЫХ:")
    print("   • WB предоставляет данные ПО КАЖДОМУ СКЛАДУ отдельно")
    print("   • Stock Tracker должен АГРЕГИРОВАТЬ данные по артикулу")
    print("   • Проверьте функцию generate_main_table() в table_generation.py")
    
    print("\n5️⃣ ВРЕМЕННЫЕ МЕТКИ:")
    print("   • Убедитесь, что данные синхронизируются в одно и то же время")
    print("   • WB CSV от 27-10-2025, проверьте дату последней синхронизации Stock Tracker")
    print("   • Возможно данные в таблице устарели")
    
    print("\n6️⃣ НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ:")
    print("   • Остановите автоматическую синхронизацию (если запущена)")
    print("   • Сделайте резервную копию текущей таблицы")
    print("   • Запустите тестовую синхронизацию одного артикула")
    print("   • Сравните результат вручную с данными WB")
    print("   • После подтверждения корректности - запустите полную синхронизацию")
    
    print("\n7️⃣ КОД ДЛЯ ПРОВЕРКИ:")
    print("   • Запустите: python test_warehouse_filtering.py")
    print("   • Запустите: python test_stock_tracker_validation.py")
    print("   • Проверьте логи: check_sheets_after_sync.py")
else:
    print("\n✅ Все данные синхронизированы корректно!")
    print("   Расхождения менее 5%, что находится в пределах нормы.")
    print("   Возможные причины минимальных расхождений:")
    print("   - Разница во времени выгрузки данных")
    print("   - Округления в расчетах")
    print("   - Заказы в процессе обработки")

print("\n" + "="*80)
print("ДЕТАЛЬНАЯ ТАБЛИЦА СРАВНЕНИЯ")
print("="*80)

comparison_data = []
for article, wb_values in wb_data.items():
    st_row = st_df[st_df['Артикул продавца'] == article]
    if not st_row.empty:
        st_orders = float(str(st_row['Заказы (всего)'].values[0]).replace(',', '.'))
        st_stock = float(str(st_row['Остатки (всего)'].values[0]).replace(',', '.'))
        
        comparison_data.append({
            'Артикул': article,
            'WB Заказы': wb_values['orders'],
            'ST Заказы': st_orders,
            'Разница заказов': wb_values['orders'] - st_orders,
            '% заказы': f"{((wb_values['orders'] - st_orders) / wb_values['orders'] * 100) if wb_values['orders'] != 0 else 0:.2f}%",
            'WB Остатки': wb_values['stock'],
            'ST Остатки': st_stock,
            'Разница остатков': wb_values['stock'] - st_stock,
            '% остатки': f"{((wb_values['stock'] - st_stock) / wb_values['stock'] * 100) if wb_values['stock'] != 0 else 0:.2f}%",
        })

comparison_df = pd.DataFrame(comparison_data)
print("\n" + comparison_df.to_string(index=False))

# Сохраняем отчет
comparison_df.to_csv('comparison_report.csv', index=False, encoding='utf-8-sig')
print("\n\n📊 Детальный отчет сохранен в: comparison_report.csv")
