#!/usr/bin/env python3
"""
Проверка периода синхронизации.
"""

from datetime import datetime, timedelta

def get_week_start() -> str:
    """Получить дату начала текущей недели (понедельник)"""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    return start_of_week.strftime("%Y-%m-%dT00:00:00")

print("=" * 80)
print("ПРОВЕРКА ПЕРИОДА СИНХРОНИЗАЦИИ")
print("=" * 80)

today = datetime.now()
print(f"\nСегодня: {today.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"День недели: {today.weekday()} (0=понедельник)")

week_start = get_week_start()
print(f"\nНачало текущей недели: {week_start}")

# Проверка: это должен быть понедельник
week_start_dt = datetime.fromisoformat(week_start)
print(f"День недели начала: {week_start_dt.weekday()} (должен быть 0)")

# Сколько дней назад
days_ago = (today - week_start_dt).days
print(f"Дней назад: {days_ago}")

print("\n" + "=" * 80)
print("WB GROUND TRUTH")
print("=" * 80)
print("Период: 22-28 октября (7 дней, вся неделя)")
print("- Its1_2_3/50g: 97 заказов")
print("- Its2/50g: 68 заказов")
print("- ItsSport2/50g: 23 заказов")

print("\n" + "=" * 80)
print("НАШ ПЕРИОД")
print("=" * 80)
print(f"Период: {week_start} - сегодня")
print(f"Это {days_ago} дней вместо 7 дней")

if days_ago < 7:
    expected_orders = 188 * (days_ago / 7)
    print(f"\nОжидаемое кол-во заказов: ~{expected_orders:.0f} (вместо 188)")
    print(f"Фактически в таблице: 41")
    
    diff = abs(41 - expected_orders) / expected_orders * 100 if expected_orders > 0 else 0
    print(f"Расхождение: {diff:.1f}%")
    
    if diff <= 10:
        print("✅ Это НОРМАЛЬНО! Период короче недели")
    else:
        print("⚠️ Есть расхождение даже с учётом периода")

print("\n" + "=" * 80)
print("РЕШЕНИЕ")
print("=" * 80)
print("ВАРИАНТ 1: Изменить get_week_start() на фиксированную дату 22 октября")
print("ВАРИАНТ 2: Использовать period_days=7 для полной недели назад")
print("ВАРИАНТ 3: Подождать до понедельника и проверить снова")
