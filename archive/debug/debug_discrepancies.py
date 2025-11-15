#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальная диагностика расхождений - прямые запросы к API WB
"""

import asyncio
import sys
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.insert(0, 'c:/Users/miros/Downloads/Stock Tracker/Stock-Tracker/src')

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher
from stock_tracker.utils.config import get_config
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.database.sheets import GoogleSheetsClient

# Настройка кодировки
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Получаем конфигурацию
config = get_config()

# Артикулы с расхождениями
PROBLEM_ARTICLES = [
    {
        'supplier_article': 'Its1_2_3/50g',
        'nm_id': 163383326,
        'wb_orders': 65,
        'tracker_orders': 103,
        'wb_stock': 3275,
        'tracker_stock': 3184
    },
    {
        'supplier_article': 'Its2/50g',
        'nm_id': 163383327,
        'wb_orders': 52,
        'tracker_orders': 61,
        'wb_stock': 2370,
        'tracker_stock': 2072
    },
    {
        'supplier_article': 'Its2/50g+Aks5/20g',
        'nm_id': 262310317,
        'wb_orders': 16,
        'tracker_orders': 22,
        'wb_stock': None,  # Нужно узнать
        'tracker_stock': 185
    }
]


async def debug_article(article_info):
    """Детальная проверка одного артикула"""
    print("=" * 100)
    print(f"🔍 АНАЛИЗ: {article_info['supplier_article']} (NM ID: {article_info['nm_id']})")
    print("=" * 100)
    print()
    
    # Инициализируем клиенты
    wb_client = WildberriesAPIClient(config.wildberries_api_key)
    dual_api = DualAPIStockFetcher(config.wildberries_api_key)
    
    # 1. Получаем заказы через Supplier Orders API
    print("📦 1. ЗАКАЗЫ (Supplier Orders API v1)")
    print("-" * 100)
    
    date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    date_to = datetime.now().strftime('%Y-%m-%d')
    
    try:
        orders_list = await wb_client.get_supplier_orders(date_from=date_from)
        
        # orders_list - это уже список заказов
        article_orders = [
            order for order in orders_list
            if order.get('nmId') == article_info['nm_id']
        ]
        
        # Считаем только незавершённые заказы
        active_orders = []
        cancelled_orders = []
        
        for order in article_orders:
            is_cancel = order.get('isCancel', False)
            status = order.get('status', '')
            
            if is_cancel or status in ['Отменён клиентом', 'Отменён продавцом', 'Отменён']:
                cancelled_orders.append(order)
            else:
                active_orders.append(order)
        
        print(f"   ✅ Всего заказов в API: {len(article_orders)}")
        print(f"   ✅ Активных заказов: {len(active_orders)}")
        print(f"   ❌ Отменённых заказов: {len(cancelled_orders)}")
        print()
        
        if len(active_orders) > 0:
            print(f"   📋 Первые 5 активных заказов:")
            for i, order in enumerate(active_orders[:5], 1):
                order_date = order.get('date', 'N/A')
                warehouse = order.get('warehouseName', 'N/A')
                status = order.get('status', 'N/A')
                print(f"      {i}. Дата: {order_date}, Склад: {warehouse}, Статус: {status}")
        
        print()
        print(f"   📊 Сравнение заказов:")
        print(f"      WB Статистика (24-30 окт): {article_info['wb_orders']}")
        print(f"      Tracker (Google Sheets):   {article_info['tracker_orders']}")
        print(f"      API (активные заказы):     {len(active_orders)}")
        print()
        
        # Анализ расхождения
        if len(active_orders) == article_info['tracker_orders']:
            print(f"   ✅ TRACKER СОВПАДАЕТ С API! ({len(active_orders)} заказов)")
        elif len(active_orders) == article_info['wb_orders']:
            print(f"   ✅ WB СТАТИСТИКА СОВПАДАЕТ С API! ({len(active_orders)} заказов)")
        else:
            print(f"   ⚠️  РАСХОЖДЕНИЕ: API показывает {len(active_orders)} заказов")
        
        print()
        
    except Exception as e:
        print(f"   ❌ ОШИБКА при получении заказов: {e}")
        print()
    
    # 2. Получаем остатки через Dual API (FBO + FBS)
    print("📦 2. ОСТАТКИ (Dual API: Statistics v1 + Marketplace v3)")
    print("-" * 100)
    
    try:
        # Получаем комбинированные остатки (СИНХРОННЫЙ метод)
        combined_stocks = dual_api.get_combined_stocks_by_article(
            supplier_article=article_info['supplier_article']
        )
        
        if combined_stocks:
            print(f"   ✅ Найдено складов в API: {len(combined_stocks)}")
            print()
            
            # Считаем общие остатки
            total_fbo = 0
            total_fbs = 0
            
            print(f"   📋 Остатки по складам:")
            for i, stock in enumerate(list(combined_stocks)[:10], 1):  # Первые 10
                warehouse = stock.get('warehouse_name', 'N/A')
                qty = stock.get('quantity', 0)
                source = stock.get('source', 'N/A')
                
                if source == 'FBO':
                    total_fbo += qty
                else:
                    total_fbs += qty
                
                print(f"      {i}. {warehouse:40} | {qty:6} шт | {source}")
            
            if len(combined_stocks) > 10:
                print(f"      ... ещё {len(combined_stocks) - 10} складов")
            
            print()
            total_api = total_fbo + total_fbs
            print(f"   📊 Итого в API:")
            print(f"      FBO (WB склады):     {total_fbo:,} шт".replace(',', ' '))
            print(f"      FBS (Seller склады): {total_fbs:,} шт".replace(',', ' '))
            print(f"      ВСЕГО:               {total_api:,} шт".replace(',', ' '))
            print()
            
            print(f"   📊 Сравнение остатков:")
            print(f"      WB Статистика (30 окт): {article_info['wb_stock']:,} шт".replace(',', ' ') if article_info['wb_stock'] else "      WB Статистика: N/A")
            print(f"      Tracker (Google Sheets): {article_info['tracker_stock']:,} шт".replace(',', ' '))
            print(f"      API (сейчас):            {total_api:,} шт".replace(',', ' '))
            print()
            
            # Анализ расхождения
            if abs(total_api - article_info['tracker_stock']) <= 50:
                print(f"   ✅ TRACKER ПОЧТИ СОВПАДАЕТ С API! (разница: {total_api - article_info['tracker_stock']:+d})")
            elif article_info['wb_stock'] and abs(total_api - article_info['wb_stock']) <= 50:
                print(f"   ✅ WB СТАТИСТИКА ПОЧТИ СОВПАДАЕТ С API! (разница: {total_api - article_info['wb_stock']:+d})")
            else:
                diff_tracker = total_api - article_info['tracker_stock']
                diff_wb = total_api - article_info['wb_stock'] if article_info['wb_stock'] else None
                print(f"   ⚠️  РАСХОЖДЕНИЕ:")
                print(f"       vs Tracker: {diff_tracker:+d} шт")
                if diff_wb is not None:
                    print(f"       vs WB Stats: {diff_wb:+d} шт")
            
        else:
            print(f"   ❌ Остатки не найдены в API!")
        
        print()
        
    except Exception as e:
        print(f"   ❌ ОШИБКА при получении остатков: {e}")
        print()
    
    # 3. Проверяем данные в Google Sheets
    print("📊 3. ДАННЫЕ В GOOGLE SHEETS")
    print("-" * 100)
    
    try:
        sheets_client = GoogleSheetsClient()  # Uses config internally
        sheets_ops = SheetsOperations(sheets_client)
        
        # Получаем все данные из таблицы
        all_data = sheets_ops.get_all_products(config.google_sheets.sheet_id)
        
        # Ищем наш артикул
        article_data = None
        for row in all_data:
            if row.get('supplier_article') == article_info['supplier_article']:
                article_data = row
                break
        
        if article_data:
            print(f"   ✅ Артикул найден в Google Sheets:")
            print(f"      Артикул продавца: {article_data.get('supplier_article')}")
            print(f"      NM ID: {article_data.get('nm_id')}")
            print(f"      Заказы (всего): {article_data.get('total_orders', 0)}")
            print(f"      Остатки (всего): {article_data.get('total_stock', 0)}")
            print(f"      Оборачиваемость: {article_data.get('turnover', 0)}")
            
            # Проверяем warehouse_details
            warehouse_details = article_data.get('warehouse_details', {})
            if warehouse_details:
                warehouses = warehouse_details.get('warehouses', [])
                print(f"      Складов в деталях: {len(warehouses)}")
                
                if warehouses:
                    print(f"      Первые 5 складов:")
                    for i, wh in enumerate(warehouses[:5], 1):
                        print(f"         {i}. {wh.get('name', 'N/A'):40} | Заказы: {wh.get('orders', 0):3} | Остатки: {wh.get('stock', 0):6}")
            
        else:
            print(f"   ❌ Артикул НЕ найден в Google Sheets!")
        
        print()
        
    except Exception as e:
        print(f"   ❌ ОШИБКА при чтении Google Sheets: {e}")
        print()
    
    print()


async def main():
    """Главная функция"""
    print("=" * 100)
    print("🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА РАСХОЖДЕНИЙ")
    print("=" * 100)
    print()
    print("Анализируем 3 артикула с расхождениями между WB статистикой и Tracker")
    print()
    
    for article in PROBLEM_ARTICLES:
        await debug_article(article)
        print()
        print()
    
    print("=" * 100)
    print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 100)


if __name__ == '__main__':
    asyncio.run(main())
