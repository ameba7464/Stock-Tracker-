#!/usr/bin/env python3
"""
Проверка расчета оборачиваемости
"""

# Примеры из логов:
products = [
    {"name": "Its2/50g", "orders": 79, "stock": 2512},
    {"name": "Its1_2_3/50g", "orders": 109, "stock": 3456},
    {"name": "ItsSport2/50g+Aks5/20g", "orders": 10, "stock": 191},
]

print("\n" + "="*80)
print("📊 ПРОВЕРКА РАСЧЕТА ОБОРАЧИВАЕМОСТИ")
print("="*80 + "\n")

print("Формула: Оборачиваемость = Остатки / Заказы\n")

for product in products:
    name = product["name"]
    orders = product["orders"]
    stock = product["stock"]
    
    if orders > 0:
        turnover = round(stock / orders, 3)
    else:
        turnover = 0.0
    
    print(f"{name}:")
    print(f"  Остатки: {stock:>6} шт")
    print(f"  Заказы:  {orders:>6} шт")
    print(f"  Оборачиваемость: {turnover:>7.3f}")
    print(f"  Интерпретация: На каждый заказ приходится {turnover:.1f} единиц остатков")
    print()

print("="*80)
print("💡 Пояснение:")
print("  - Высокая оборачиваемость (>30): много остатков относительно заказов")
print("  - Средняя оборачиваемость (10-30): сбалансированное соотношение")
print("  - Низкая оборачиваемость (<10): мало остатков, товар быстро продается")
print("="*80 + "\n")
