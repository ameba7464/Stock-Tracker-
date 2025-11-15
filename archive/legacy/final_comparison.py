#!/usr/bin/env python3#!/usr/bin/env python3

# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-

""""""

ФИНАЛЬНОЕ СРАВНЕНИЕ: Свежие данные из Google Sheets vs Официальная статистика WBФинальное сравнение данных после всех исправлений

Дата: 30 октября 2025Сравнивает актуальный CSV от 30.10.2025 с текущим состоянием Stock Tracker

""""""



import pandas as pdimport csv

from collections import defaultdictfrom collections import defaultdict



# Файлыdef parse_number(value):

wb_file = r"c:\Users\miros\Downloads\30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv_export (1).tsv"    """Парсинг числовых значений из строк"""

tracker_file = r"c:\Users\miros\Downloads\Stock Tracker - Stock Tracker (1).tsv"    if not value or value == '':

        return 0

print("="*100)    # Убираем пробелы и заменяем запятую на точку

print("ФИНАЛЬНОЕ СРАВНЕНИЕ: Google Sheets (СВЕЖИЕ) vs Официальная статистика WB")    value = str(value).replace(' ', '').replace(',', '.')

print("="*100)    try:

        return float(value)

# Загружаем данные    except:

wb_df = pd.read_csv(wb_file, sep='\t', encoding='utf-8')        return 0

tracker_df = pd.read_csv(tracker_file, sep='\t', encoding='utf-8')

def load_wb_csv(filepath):

print(f"\n[+] Загружено данных:")    """Загрузка данных из актуального WB CSV"""

print(f"  - WB статистика: {len(wb_df)} строк")    wb_data = defaultdict(lambda: {'stock': 0, 'warehouses': {}})

print(f"  - Stock-Tracker (LIVE): {len(tracker_df)} строк")    

    with open(filepath, 'r', encoding='utf-8') as f:

# Группируем WB данные по артикулам        # Пропускаем первую строку (заголовок раздела)

wb_grouped = defaultdict(lambda: {        next(f)

    'nm_id': None,        reader = csv.DictReader(f)

    'total_orders': 0,        

    'total_stock': 0,        for row in reader:

    'warehouses': []            article = row.get('Артикул продавца', '')

})            if not article:

                continue

for _, row in wb_df.iterrows():            

    article = str(row.get('Артикул продавца', '')).strip()            warehouse = row.get('Склад', '')

    nm_id = row.get('Артикул WB', None)            stock_str = row.get('Остатки на текущий день, шт', '0')

    warehouse = str(row.get('Склад', '')).strip()            stock = int(stock_str) if stock_str and stock_str.strip() else 0

                

    # Заказы и остатки - обрабатываем как числа            wb_data[article]['stock'] += stock

    try:            if warehouse and stock > 0:

        orders = float(row.get('Заказали, шт', 0) or 0)                if warehouse not in wb_data[article]['warehouses']:

    except:                    wb_data[article]['warehouses'][warehouse] = 0

        orders = 0                wb_data[article]['warehouses'][warehouse] += stock

        

    try:    return wb_data

        stock = float(row.get('Остатки на текущий день, шт', 0) or 0)

    except:def load_tracker_csv(filepath):

        stock = 0    """Загрузка данных из экспорта Stock Tracker"""

        tracker_data = {}

    if article:    

        wb_grouped[article]['nm_id'] = nm_id    with open(filepath, 'r', encoding='utf-8') as f:

        wb_grouped[article]['total_orders'] += orders        # Читаем весь файл

        wb_grouped[article]['total_stock'] += stock        content = f.read()

        if warehouse:    

            wb_grouped[article]['warehouses'].append({    # Разбираем вручную, учитывая многострочные ячейки

                'name': warehouse,    lines = content.split('\n')

                'orders': orders,    

                'stock': stock    # Находим строки с артикулами (начинаются с Its)

            })    i = 1  # Пропускаем заголовок

    while i < len(lines):

# Группируем Tracker данные        line = lines[i].strip()

tracker_grouped = {}        if not line:

for _, row in tracker_df.iterrows():            i += 1

    article = str(row.get('Артикул продавца', '')).strip()            continue

            

    if article:        # Проверяем, начинается ли строка с артикула

        # Парсим числа с пробелами (неразрывными)        if line.startswith('Its'):

        try:            parts = line.split(',', 4)  # Артикул, NM ID, Заказы, Остатки, остальное

            total_stock_str = str(row.get('Остатки (всего)', '0'))            if len(parts) >= 4:

            total_stock = int(total_stock_str.replace(' ', '').replace('\xa0', ''))                article = parts[0]

        except:                stock_str = parts[3].replace(' ', '').replace('"', '')

            total_stock = 0                stock = int(parse_number(stock_str))

                            

        try:                # Ищем склады в следующих строках (они в кавычках)

            total_orders_str = str(row.get('Заказы (всего)', '0'))                warehouses = {}

            total_orders = int(total_orders_str.replace(' ', '').replace('\xa0', ''))                

        except:                # Продолжаем читать, пока не встретим следующий артикул

            total_orders = 0                j = i + 1

                            warehouse_data = ""

        try:                while j < len(lines) and not lines[j].startswith('Its'):

            nm_id = int(row.get('Артикул товара', '0'))                    warehouse_data += lines[j] + "\n"

        except:                    j += 1

            nm_id = 0                

                        # Если есть данные о складах, парсим их

        tracker_grouped[article] = {                if '"' in line or warehouse_data:

            'nm_id': nm_id,                    # Извлекаем данные складов из остатка строки и следующих строк

            'total_orders': total_orders,                    full_line = line

            'total_stock': total_stock,                    if warehouse_data:

            'turnover': str(row.get('Оборачиваемость', '0'))                        full_line += "\n" + warehouse_data

        }                    

                    # Ищем остатки на складе (последний столбец)

# Сравнение                    if full_line.count('"') >= 6:  # Должно быть 3 пары кавычек (название, заказы, остатки)

print("\n" + "="*100)                        # Находим последнюю пару кавычек (остатки на складе)

print("ДЕТАЛЬНОЕ СРАВНЕНИЕ ПО АРТИКУЛАМ")                        last_quote_start = full_line.rfind('"')

print("="*100)                        if last_quote_start > 0:

                            temp = full_line[:last_quote_start]

# Общие артикулы                            prev_quote = temp.rfind('"')

wb_articles = set(wb_grouped.keys())                            if prev_quote > 0:

tracker_articles = set(tracker_grouped.keys())                                stocks_str = full_line[prev_quote+1:last_quote_start]

common_articles = wb_articles & tracker_articles                                stock_values = [s.strip() for s in stocks_str.split('\n') if s.strip()]

                                

print(f"\n[i] Артикулы:")                                # Находим предпоследнюю пару (название склада)

print(f"  - В WB статистике: {len(wb_articles)} уникальных")                                temp2 = temp[:prev_quote]

print(f"  - В Stock-Tracker: {len(tracker_articles)} уникальных")                                name_quote_end = temp2.rfind('"')

print(f"  - Общих артикулов: {len(common_articles)}")                                if name_quote_end > 0:

if wb_articles - tracker_articles:                                    temp3 = temp2[:name_quote_end]

    print(f"  - Только в WB: {wb_articles - tracker_articles}")                                    name_quote_start = temp3.rfind('"')

if tracker_articles - wb_articles:                                    if name_quote_start >= 0:

    print(f"  - Только в Tracker: {tracker_articles - wb_articles}")                                        names_str = temp2[name_quote_start+1:name_quote_end]

                                        warehouse_names = [n.strip() for n in names_str.split('\n') if n.strip()]

# Сравниваем каждый общий артикул                                        

total_wb_orders = 0                                        # Сопоставляем имена и остатки

total_tracker_orders = 0                                        for name, stock_val in zip(warehouse_names, stock_values):

total_wb_stock = 0                                            wh_stock = int(parse_number(stock_val))

total_tracker_stock = 0                                            if wh_stock > 0:

                                                warehouses[name] = wh_stock

orders_match_count = 0                

stock_match_count = 0                tracker_data[article] = {

orders_diff_list = []                    'stock': stock,

stock_diff_list = []                    'warehouses': warehouses

                }

for article in sorted(common_articles):                

    wb_data = wb_grouped[article]                i = j

    tracker_data = tracker_grouped[article]        else:

                i += 1

    wb_orders = wb_data['total_orders']    

    tracker_orders = tracker_data['total_orders']    return tracker_data

    wb_stock = wb_data['total_stock']

    tracker_stock = tracker_data['total_stock']def compare_final():

        """Финальное сравнение после исправлений"""

    total_wb_orders += wb_orders    

    total_tracker_orders += tracker_orders    print("\n" + "="*100)

    total_wb_stock += wb_stock    print("ФИНАЛЬНОЕ СРАВНЕНИЕ ДАННЫХ ПОСЛЕ ВСЕХ ИСПРАВЛЕНИЙ")

    total_tracker_stock += tracker_stock    print("="*100)

        print("\nСравнение: WB CSV (30.10.2025) vs Stock Tracker (текущее состояние)")

    orders_match = abs(wb_orders - tracker_orders) <= 1  # Допуск ±1    print()

    stock_match = abs(wb_stock - tracker_stock) <= 5  # Допуск ±5    

        # Загружаем данные

    if orders_match:    wb_data = load_wb_csv("30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv")

        orders_match_count += 1    tracker_data = load_tracker_csv("Stock Tracker - Stock Tracker (9).csv")

    else:    

        orders_diff_list.append((article, wb_orders, tracker_orders, tracker_orders - wb_orders))    # Проблемные артикулы

        target_articles = ['Its2/50g', 'ItsSport2/50g', 'Its1_2_3/50g']

    if stock_match:    

        stock_match_count += 1    total_wb_stock = 0

    else:    total_tracker_stock = 0

        stock_diff_list.append((article, wb_stock, tracker_stock, tracker_stock - wb_stock))    total_diff = 0

        

    print(f"\n{'━'*100}")    for article in target_articles:

    print(f"[*] АРТИКУЛ: {article}")        wb = wb_data.get(article, {})

    print(f"{'━'*100}")        tracker = tracker_data.get(article, {})

            

    print(f"\n  Артикул WB:")        wb_stock = wb.get('stock', 0)

    print(f"    WB:      {wb_data['nm_id']}")        tracker_stock = tracker.get('stock', 0)

    print(f"    Tracker: {tracker_data['nm_id']}")        diff = wb_stock - tracker_stock

            diff_percent = (abs(diff) / wb_stock * 100) if wb_stock > 0 else 0

    print(f"\n  ЗАКАЗЫ (период 24-30 октября):")        

    print(f"    WB:        {wb_orders:.0f} шт")        total_wb_stock += wb_stock

    print(f"    Tracker:   {tracker_orders} шт")        total_tracker_stock += tracker_stock

    if orders_match:        total_diff += abs(diff)

        print(f"    [OK] Совпадает!")        

    else:        print(f"\n{'='*100}")

        diff = tracker_orders - wb_orders        print(f"{article}")

        diff_pct = (diff / wb_orders * 100) if wb_orders > 0 else 0        print(f"{'='*100}")

        print(f"    [!] РАСХОЖДЕНИЕ: {diff:+.0f} шт ({diff_pct:+.1f}%)")        print(f"  WB CSV Total:     {wb_stock:>6d} ед.")

            print(f"  Tracker Total:    {tracker_stock:>6d} ед.")

    print(f"\n  ОСТАТКИ (на текущий день):")        print(f"  Разница:          {diff:>6d} ед. ({diff_percent:.1f}%)")

    print(f"    WB:        {wb_stock:.0f} шт")        

    print(f"    Tracker:   {tracker_stock} шт")        # Сравнение по складу Маркетплейс

    if stock_match:        wb_mp_stock = wb.get('warehouses', {}).get('Маркетплейс', 0)

        print(f"    [OK] Совпадает!")        tracker_mp_stock = tracker.get('warehouses', {}).get('Маркетплейс', 0)

    else:        

        diff = tracker_stock - wb_stock        print(f"\n  Склад 'Маркетплейс':")

        diff_pct = (diff / wb_stock * 100) if wb_stock > 0 else 0        print(f"    WB CSV:         {wb_mp_stock:>6d} ед.")

        print(f"    [!] РАСХОЖДЕНИЕ: {diff:+.0f} шт ({diff_pct:+.1f}%)")        print(f"    Tracker:        {tracker_mp_stock:>6d} ед.")

            print(f"    Разница:        {wb_mp_stock - tracker_mp_stock:>6d} ед.")

    # Показываем склады WB с активностью        

    print(f"\n  СКЛАДЫ (данные WB):")        if tracker_mp_stock > 0:

    active_warehouses = [w for w in wb_data['warehouses'] if w['orders'] > 0 or w['stock'] > 0]            print(f"    [SUCCESS] FBS склад найден в Tracker!")

    if active_warehouses:        else:

        print(f"    Активных складов: {len(active_warehouses)}")            print(f"    [FAIL] FBS склад отсутствует в Tracker!")

        for wh in active_warehouses[:10]:  # Первые 10        

            print(f"      • {wh['name']:40} | Заказы: {wh['orders']:>4.0f} | Остатки: {wh['stock']:>6.0f}")        # Детали по складам

        if len(active_warehouses) > 10:        print(f"\n  Все склады с остатками:")

            print(f"      ... и ещё {len(active_warehouses) - 10} складов")        print(f"  {'Склад':<40} {'WB CSV':>10} {'Tracker':>10} {'Разница':>10}")

            print(f"  {'-'*70}")

    print(f"\n  ОБОРАЧИВАЕМОСТЬ (Tracker): {tracker_data['turnover']} дней")        

        all_warehouses = set(wb.get('warehouses', {}).keys()) | set(tracker.get('warehouses', {}).keys())

# ИТОГОВАЯ СТАТИСТИКА        

print("\n" + "="*100)        for wh in sorted(all_warehouses):

print("ИТОГОВАЯ СТАТИСТИКА")            wb_wh = wb.get('warehouses', {}).get(wh, 0)

print("="*100)            tr_wh = tracker.get('warehouses', {}).get(wh, 0)

            diff_wh = wb_wh - tr_wh

print(f"\n[+] ИТОГО по всем артикулам:")            

print(f"\n  Заказы:")            status = "[OK]" if abs(diff_wh) <= wb_wh * 0.15 else "[!]"  # Допускаем 15% разницу

print(f"    WB:         {total_wb_orders:.0f} шт")            print(f"  {status} {wh:<35} {wb_wh:>10d} {tr_wh:>10d} {diff_wh:>10d}")

print(f"    Tracker:    {total_tracker_orders} шт")    

diff_orders = total_tracker_orders - total_wb_orders    print(f"\n{'='*100}")

diff_orders_pct = (diff_orders / total_wb_orders * 100) if total_wb_orders > 0 else 0    print(f"ИТОГОВАЯ СТАТИСТИКА")

print(f"    Разница:    {diff_orders:+.0f} шт ({diff_orders_pct:+.1f}%)")    print(f"{'='*100}")

    print(f"  Всего остатков (WB):      {total_wb_stock:>6d} ед.")

print(f"\n  Остатки:")    print(f"  Всего остатков (Tracker): {total_tracker_stock:>6d} ед.")

print(f"    WB:         {total_wb_stock:.0f} шт")    print(f"  Общая разница:            {total_diff:>6d} ед.")

print(f"    Tracker:    {total_tracker_stock} шт")    

diff_stock = total_tracker_stock - total_wb_stock    accuracy = (1 - total_diff / total_wb_stock) * 100 if total_wb_stock > 0 else 0

diff_stock_pct = (diff_stock / total_wb_stock * 100) if total_wb_stock > 0 else 0    print(f"  Точность:                 {accuracy:>6.1f}%")

print(f"    Разница:    {diff_stock:+.0f} шт ({diff_stock_pct:+.1f}%)")    

    print(f"\n{'='*100}")

print(f"\n[i] Точность данных:")    

print(f"    Артикулов с совпадением по заказам:  {orders_match_count}/{len(common_articles)} ({orders_match_count/len(common_articles)*100:.1f}%)")    # Оценка результата

print(f"    Артикулов с совпадением по остаткам: {stock_match_count}/{len(common_articles)} ({stock_match_count/len(common_articles)*100:.1f}%)")    if accuracy >= 90:

        print("[SUCCESS] Точность > 90% - система работает корректно!")

# Анализ расхождений        print("Небольшие расхождения связаны с естественными продажами между выгрузкой CSV и синхронизацией.")

if orders_diff_list:    elif accuracy >= 80:

    print(f"\n[!] Топ-5 расхождений по ЗАКАЗАМ:")        print("[WARNING] Точность 80-90% - есть небольшие расхождения")

    for article, wb_val, tr_val, diff in sorted(orders_diff_list, key=lambda x: abs(x[3]), reverse=True)[:5]:    else:

        print(f"    {article:30} | WB: {wb_val:>4.0f} | Tracker: {tr_val:>4} | Разница: {diff:+.0f}")        print("[FAIL] Точность < 80% - требуется дополнительная проверка")

    

if stock_diff_list:    print(f"{'='*100}\n")

    print(f"\n[!] Топ-5 расхождений по ОСТАТКАМ:")

    for article, wb_val, tr_val, diff in sorted(stock_diff_list, key=lambda x: abs(x[3]), reverse=True)[:5]:if __name__ == '__main__':

        print(f"    {article:30} | WB: {wb_val:>6.0f} | Tracker: {tr_val:>6} | Разница: {diff:+.0f}")    compare_final()


# ВЫВОДЫ
print("\n" + "="*100)
print("ВЫВОДЫ")
print("="*100)

if orders_match_count == len(common_articles) and stock_match_count == len(common_articles):
    print("\n[SUCCESS] ВСЕ ДАННЫЕ ПОЛНОСТЬЮ СОВПАДАЮТ!")
    print("  Трекер показывает ту же информацию, что и официальная статистика WB!")
elif orders_match_count / len(common_articles) > 0.8 and stock_match_count / len(common_articles) > 0.8:
    print("\n[GOOD] Большинство данных совпадают (>80%)!")
    print("  Небольшие расхождения могут быть связаны с:")
    print("  - Разным временем снятия данных")
    print("  - Округлением чисел")
    print("  - Служебными складами")
else:
    print("\n[WARNING] Обнаружены значительные расхождения")
    print("  Возможные причины:")
    print("  - Разные периоды учета заказов")
    print("  - Различия в учете складов")
    print("  - Проблемы с агрегацией данных")

print("\n" + "="*100)
print("Анализ завершен!")
print("="*100)
