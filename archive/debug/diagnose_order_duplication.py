#!/usr/bin/env python3
"""
Скрипт для диагностики и исправления дублирования заказов.
Проверяет уникальность заказов и выявляет источники дублирования.
"""

import asyncio
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.api.client import create_wildberries_client
from stock_tracker.core.calculator import WildberriesCalculator
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def diagnose_order_duplication():
    """Диагностика дублирования заказов"""
    
    print("="*80)
    print("🔍 ДИАГНОСТИКА ДУБЛИРОВАНИЯ ЗАКАЗОВ")
    print("="*80)
    
    try:
        # 1. Получить данные из API
        print("\n1️⃣ Получение данных из Wildberries API...")
        client = create_wildberries_client()
        fetcher = WildberriesProductDataFetcher(client)
        
        # Получаем заказы за последние 7 дней (как в CSV)
        from datetime import timedelta
        date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        print(f"   📅 Период: с {date_from} по сегодня")
        orders_data = await fetcher.fetch_supplier_orders(date_from, flag=0)
        print(f"   ✅ Получено {len(orders_data)} записей заказов")
        
        # 2. Анализ уникальности заказов
        print("\n2️⃣ Анализ уникальности заказов...")
        
        order_ids = []
        order_g_numbers = []
        order_srid = []
        
        for order in orders_data:
            # Проверяем различные ID полей
            if "gNumber" in order:
                order_g_numbers.append(order["gNumber"])
            if "srid" in order:
                order_srid.append(order["srid"])
            if "odid" in order:
                order_ids.append(order["odid"])
        
        print(f"\n   📊 Статистика ID:")
        print(f"      - gNumber найдено: {len(order_g_numbers)}")
        print(f"      - srid найдено: {len(order_srid)}")
        print(f"      - odid найдено: {len(order_ids)}")
        
        # Проверка на дубликаты
        if order_g_numbers:
            unique_g = len(set(order_g_numbers))
            total_g = len(order_g_numbers)
            duplicates_g = total_g - unique_g
            
            print(f"\n   🔍 Анализ gNumber:")
            print(f"      - Всего записей: {total_g}")
            print(f"      - Уникальных: {unique_g}")
            print(f"      - Дубликатов: {duplicates_g}")
            
            if duplicates_g > 0:
                print(f"      ⚠️  НАЙДЕНЫ ДУБЛИКАТЫ!")
                
                # Найти конкретные дубликаты
                counter = Counter(order_g_numbers)
                duplicates = {k: v for k, v in counter.items() if v > 1}
                
                print(f"\n      Примеры дубликатов:")
                for gnum, count in list(duplicates.items())[:5]:
                    print(f"         - {gnum}: встречается {count} раз")
            else:
                print(f"      ✅ Дубликаты не найдены")
        
        # 3. Анализ заказов по артикулам
        print("\n3️⃣ Анализ заказов по артикулам...")
        
        orders_by_article = defaultdict(list)
        orders_by_nmid = defaultdict(list)
        
        for order in orders_data:
            article = order.get("supplierArticle", "")
            nm_id = order.get("nmId", 0)
            
            if article:
                orders_by_article[article].append(order)
            if nm_id:
                orders_by_nmid[nm_id].append(order)
        
        print(f"   📦 Уникальных артикулов продавца: {len(orders_by_article)}")
        print(f"   📦 Уникальных nmId: {len(orders_by_nmid)}")
        
        # Проверяем топ-3 артикула с расхождениями
        test_articles = {
            "Its1_2_3/50g": 163383326,
            "Its2/50g": 163383327,
            "Its2/50g+Aks5/20g": 262310317
        }
        
        print(f"\n   🔬 Детальный анализ проблемных артикулов:")
        
        for article, nm_id in test_articles.items():
            article_orders = orders_by_article.get(article, [])
            nmid_orders = orders_by_nmid.get(nm_id, [])
            
            print(f"\n   📦 {article} (nmId: {nm_id}):")
            print(f"      По артикулу: {len(article_orders)} заказов")
            print(f"      По nmId: {len(nmid_orders)} заказов")
            
            # Проверяем уникальность для этого артикула
            if article_orders and "gNumber" in article_orders[0]:
                article_gnumbers = [o.get("gNumber") for o in article_orders if "gNumber" in o]
                unique_gnumbers = len(set(article_gnumbers))
                
                print(f"      Уникальных gNumber: {unique_gnumbers}")
                
                if unique_gnumbers != len(article_gnumbers):
                    print(f"      ⚠️  ДУБЛИКАТЫ для {article}: {len(article_gnumbers) - unique_gnumbers} шт")
                else:
                    print(f"      ✅ Дубликаты не найдены")
            
            # Анализ по складам
            warehouses = defaultdict(int)
            for order in article_orders:
                wh = order.get("warehouseName", "Unknown")
                warehouses[wh] += 1
            
            print(f"      Заказы по складам:")
            for wh, count in sorted(warehouses.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"         - {wh}: {count}")
        
        # 4. Анализ логики group_data_by_product
        print(f"\n4️⃣ Тестирование логики группировки...")
        
        # Получаем данные складов
        print(f"   📡 Получение данных остатков...")
        warehouse_task_id = await fetcher.create_warehouse_remains_task()
        await asyncio.sleep(30)  # Ждем обработки
        warehouse_data = await fetcher.download_warehouse_remains(warehouse_task_id)
        print(f"   ✅ Получено {len(warehouse_data)} записей остатков")
        
        # Группируем данные
        print(f"\n   🔄 Группировка данных...")
        grouped_data = WildberriesCalculator.group_data_by_product(
            warehouse_data, 
            orders_data
        )
        
        print(f"   ✅ Сгруппировано {len(grouped_data)} продуктов")
        
        # Проверяем проблемные артикулы
        print(f"\n   🔬 Проверка проблемных артикулов после группировки:")
        
        for article, nm_id in test_articles.items():
            key = (article, nm_id)
            if key in grouped_data:
                group = grouped_data[key]
                
                # Считаем заказы из складов
                warehouse_orders_sum = sum(wh["orders"] for wh in group["warehouses"].values())
                
                # Считаем из raw данных
                raw_orders = len([o for o in orders_data 
                                if o.get("supplierArticle") == article 
                                and o.get("nmId") == nm_id
                                and not o.get("isCancel", False)])
                
                print(f"\n   📦 {article}:")
                print(f"      Raw заказов из API: {raw_orders}")
                print(f"      Сумма по складам: {warehouse_orders_sum}")
                print(f"      Разница: {warehouse_orders_sum - raw_orders}")
                
                if warehouse_orders_sum != raw_orders:
                    print(f"      ⚠️  РАСХОЖДЕНИЕ ОБНАРУЖЕНО!")
                    print(f"      Возможные причины:")
                    print(f"         1. Дублирование заказов при группировке")
                    print(f"         2. Заказ учитывается несколько раз для разных складов")
                    print(f"         3. Отмененные заказы учитываются")
                    
                    # Детальный анализ складов
                    print(f"      Склады:")
                    for wh_name, wh_data in group["warehouses"].items():
                        if wh_data["orders"] > 0:
                            print(f"         - {wh_name}: {wh_data['orders']} заказов")
                else:
                    print(f"      ✅ Данные совпадают")
        
        # 5. Рекомендации
        print(f"\n" + "="*80)
        print(f"5️⃣ РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ")
        print(f"="*80)
        
        print(f"\n✅ Если дубликаты НЕ найдены:")
        print(f"   - Проблема в логике агрегации данных")
        print(f"   - Нужно исправить group_data_by_product()")
        print(f"   - Проверить, что заказы не считаются повторно")
        
        print(f"\n⚠️  Если дубликаты НАЙДЕНЫ:")
        print(f"   - Добавить фильтрацию по уникальным ID (gNumber)")
        print(f"   - Использовать set() для отслеживания обработанных заказов")
        print(f"   - Добавить валидацию при группировке")
        
        print(f"\n🔧 Код для исправления:")
        print(f"""
    # В методе group_data_by_product():
    processed_order_ids = set()
    
    for order in orders_data:
        order_id = order.get("gNumber")  # Уникальный ID заказа
        
        if order_id in processed_order_ids:
            logger.warning(f"Skipping duplicate order: {{order_id}}")
            continue
        
        processed_order_ids.add(order_id)
        # ... остальная логика обработки
        """)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при диагностике: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(diagnose_order_duplication())
    
    if success:
        print(f"\n✅ Диагностика завершена успешно")
        exit(0)
    else:
        print(f"\n❌ Диагностика завершилась с ошибками")
        exit(1)
