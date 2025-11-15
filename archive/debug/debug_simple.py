#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая диагностика - прямые запросы к API WB
"""

import asyncio
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, 'c:/Users/miros/Downloads/Stock Tracker/Stock-Tracker/src')

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher
from stock_tracker.utils.config import get_config

# Настройка кодировки
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

config = get_config()

# Артикулы с расхождениями
ARTICLES = [
    {'supplier_article': 'Its1_2_3/50g', 'nm_id': 163383326, 'wb_orders': 65, 'tracker_orders': 103},
    {'supplier_article': 'Its2/50g', 'nm_id': 163383327, 'wb_orders': 52, 'tracker_orders': 61},
    {'supplier_article': 'Its2/50g+Aks5/20g', 'nm_id': 262310317, 'wb_orders': 16, 'tracker_orders': 22},
]


async def analyze_orders(article_info):
    """Анализ заказов"""
    print("=" * 100)
    print(f"🔍 {article_info['supplier_article']} (NM ID: {article_info['nm_id']})")
    print("=" * 100)
    print()
    
    wb_client = WildberriesAPIClient(config.wildberries_api_key)
    
    print("📦 ЗАКАЗЫ (последние 7 дней)")
    print("-" * 100)
    
    date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    try:
        orders_list = await wb_client.get_supplier_orders(date_from=date_from)
        
        # Фильтруем заказы по NM ID
        article_orders = [o for o in orders_list if o.get('nmId') == article_info['nm_id']]
        
        # Считаем активные заказы
        active = []
        cancelled = []
        
        for order in article_orders:
            is_cancel = order.get('isCancel', False)
            if is_cancel:
                cancelled.append(order)
            else:
                active.append(order)
        
        print(f"✅ Всего заказов в API: {len(article_orders)}")
        print(f"✅ Активных: {len(active)}")
        print(f"❌ Отменённых: {len(cancelled)}")
        print()
        
        print(f"📊 СРАВНЕНИЕ:")
        print(f"   WB Статистика (24-30 окт): {article_info['wb_orders']}")
        print(f"   Tracker (Google Sheets):   {article_info['tracker_orders']}")
        print(f"   API (активные сейчас):     {len(active)}")
        print()
        
        # Анализ
        if len(active) == article_info['tracker_orders']:
            print(f"   ✅ ✅ ✅ TRACKER СОВПАДАЕТ С API ({len(active)} заказов)")
            print(f"   💡 Причина расхождения: WB статистика показывает период 24-30 окт ({article_info['wb_orders']} заказов)")
            print(f"       Tracker обновлён позже и включает более свежие заказы (+{len(active) - article_info['wb_orders']} заказов)")
        elif len(active) == article_info['wb_orders']:
            print(f"   ✅ WB СТАТИСТИКА СОВПАДАЕТ С API ({len(active)} заказов)")
        else:
            print(f"   ⚠️ РАСХОЖДЕНИЕ: API={len(active)}, WB Stats={article_info['wb_orders']}, Tracker={article_info['tracker_orders']}")
        
        # Показываем примеры активных заказов
        if active:
            print()
            print("   📋 Примеры активных заказов (первые 3):")
            for i, order in enumerate(active[:3], 1):
                date = order.get('date', 'N/A')[:10]
                warehouse = order.get('warehouseName', 'N/A')
                status = order.get('finishedPrice', 0) / 100
                print(f"      {i}. Дата: {date}, Склад: {warehouse}, Цена: {status} руб")
        
        print()
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


def analyze_stocks(article_info):
    """Анализ остатков"""
    print()
    print("📦 ОСТАТКИ (Dual API: FBO + FBS)")
    print("-" * 100)
    
    try:
        dual_api = DualAPIStockFetcher(config.wildberries_api_key)
        
        # Получаем комбинированные остатки по артикулу
        result = dual_api.get_combined_stocks_by_article(
            supplier_article=article_info['supplier_article']
        )
        
        if result:
            print(f"✅ Найдено артикулов в ответе: {len(result)}")
            print()
            
            # Выводим данные по каждому найденному артикулу
            for art, data in result.items():
                print(f"   📦 Артикул: {art}")
                print(f"      NM ID: {data.get('nm_id', 'N/A')}")
                print(f"      FBO остатки: {data.get('fbo_stock', 0):,} шт".replace(',', ' '))
                print(f"      FBS остатки: {data.get('fbs_stock', 0):,} шт".replace(',', ' '))
                print(f"      ВСЕГО: {data.get('total_stock', 0):,} шт".replace(',', ' '))
                print(f"      Складов FBO: {len(data.get('fbo_details', []))}")
                print(f"      Складов FBS: {len(data.get('fbs_details', []))}")
                
                # Показываем первые 5 складов
                fbo_details = data.get('fbo_details', [])
                if fbo_details:
                    print(f"      Первые FBO склады:")
                    for i, detail in enumerate(fbo_details[:5], 1):
                        wh = detail.get('warehouseName', 'N/A')
                        qty = detail.get('quantityFull', 0)
                        print(f"         {i}. {wh:40} {qty:6} шт")
                
                print()
        else:
            print("❌ Артикул не найден в API!")
        
        print()
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("=" * 100)
    print("🔍 ДИАГНОСТИКА РАСХОЖДЕНИЙ - ПРЯМЫЕ ЗАПРОСЫ К API WB")
    print("=" * 100)
    print()
    
    for article in ARTICLES:
        await analyze_orders(article)
        analyze_stocks(article)
        print()
        print()


if __name__ == '__main__':
    asyncio.run(main())
