"""
Модуль для получения полных данных по товарам из Wildberries API.
Комбинирует данные из трех эндпоинтов для получения всех необходимых метрик.

Автор: Stock Tracker Team
Дата: 22 ноября 2025 г.
"""

import sys
import io
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

# Установка кодировки для вывода
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


@dataclass
class ProductMetrics:
    """Полные метрики товара из всех источников."""
    
    # Основные идентификаторы
    brand: str
    subject: str
    subject_id: int
    vendor_code: str
    nm_id: int
    
    # Заказы
    orders_total: int
    orders_wb_warehouses: int
    orders_fbs_warehouses: int
    orders_by_warehouse: Dict[str, int]
    
    # Остатки
    stocks_total: int
    stocks_wb: int
    stocks_mp: int
    stocks_by_warehouse: Dict[str, int]
    
    # Логистика
    in_transit_to_customer: int
    in_transit_to_wb_warehouse: int
    
    # Аналитика
    turnover_days: int
    avg_orders_per_day: float
    conversion_to_cart: int
    conversion_to_order: int
    buyout_percent: int
    
    # Дополнительные метрики
    avg_price: int
    order_sum_total: int
    buyout_count: int
    buyout_sum: int


class WildberriesDataCollector:
    """Класс для сбора полных данных из Wildberries API."""
    
    # Base URLs
    ANALYTICS_BASE_URL = "https://seller-analytics-api.wildberries.ru"
    STATISTICS_BASE_URL = "https://statistics-api.wildberries.ru"
    
    # Endpoints
    SALES_FUNNEL_ENDPOINT = "/api/analytics/v3/sales-funnel/products"
    WAREHOUSE_REMAINS_ENDPOINT = "/api/v1/warehouse_remains"
    WAREHOUSE_DOWNLOAD_ENDPOINT = "/api/v1/warehouse_remains/tasks/{task_id}/download"
    SUPPLIER_ORDERS_ENDPOINT = "/api/v1/supplier/orders"
    
    # Rate limits
    RATE_LIMIT_DELAY = 21  # секунд между запросами (3 req/min)
    
    def __init__(self, api_key: str):
        """
        Инициализация клиента.
        
        Args:
            api_key: API ключ Wildberries (категория Analytics)
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "StockTracker-DataCollector/1.0"
        })
        # Отключаем SSL верификацию для обхода SSL ошибок
        self.session.verify = False
        # Подавляем предупреждения о небезопасных запросах
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.last_request_time = 0
    
    def _wait_for_rate_limit(self):
        """Ожидание для соблюдения rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - elapsed
            print(f"⏳ Ожидание {sleep_time:.1f}с для соблюдения rate limit...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def get_sales_funnel_data(
        self, 
        period_start: str, 
        period_end: str,
        nm_ids: Optional[List[int]] = None,
        brand_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Получить данные из Sales Funnel API v3.
        
        Args:
            period_start: Начало периода (YYYY-MM-DD)
            period_end: Конец периода (YYYY-MM-DD)
            nm_ids: Список артикулов WB (опционально)
            brand_names: Список брендов (опционально)
            
        Returns:
            Словарь с данными о товарах
        """
        self._wait_for_rate_limit()
        
        url = self.ANALYTICS_BASE_URL + self.SALES_FUNNEL_ENDPOINT
        
        body = {
            "selectedPeriod": {
                "start": period_start,
                "end": period_end
            }
        }
        
        if nm_ids:
            body["nmIds"] = nm_ids
        if brand_names:
            body["brandNames"] = brand_names
        
        print(f"📊 Запрос Sales Funnel API: период {period_start} - {period_end}")
        if nm_ids:
            print(f"   Фильтр по артикулам: {len(nm_ids)} шт.")
        if brand_names:
            print(f"   Фильтр по брендам: {', '.join(brand_names)}")
        
        # Повторные попытки при ошибках
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.post(url, json=body, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                products_count = len(data.get('data', {}).get('products', []))
                print(f"✅ Получено товаров: {products_count}")
                
                return data
            except requests.exceptions.SSLError as e:
                print(f"⚠️ SSL ошибка (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Пауза перед повтором
                    continue
                print(f"❌ Не удалось получить данные после {max_retries} попыток")
                return {"data": {"products": []}}
            except requests.exceptions.RequestException as e:
                print(f"❌ Ошибка Sales Funnel API: {e}")
                return {"data": {"products": []}}
    
    def get_warehouse_remains(
        self,
        group_by_nm: bool = True,
        group_by_sa: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить остатки по складам из Warehouse Remains API.
        
        Args:
            group_by_nm: Группировать по артикулам WB
            group_by_sa: Группировать по артикулам продавца
            
        Returns:
            Список товаров с остатками по складам
        """
        # Шаг 1: Создать задачу на генерацию отчета
        self._wait_for_rate_limit()
        
        url = self.ANALYTICS_BASE_URL + self.WAREHOUSE_REMAINS_ENDPOINT
        params = {
            "groupByNm": str(group_by_nm).lower(),
            "groupBySa": str(group_by_sa).lower(),
            "locale": "ru"
        }
        
        print(f"📦 Создание задачи Warehouse Remains...")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            task_data = response.json()
            task_id = task_data.get('data', {}).get('taskId')
            
            if not task_id:
                print(f"❌ Не получен task_id: {task_data}")
                return []
            
            print(f"✅ Задача создана: {task_id}")
            
            # Шаг 2: Дождаться готовности и скачать результат
            print(f"⏳ Ожидание готовности отчета (5 сек)...")
            time.sleep(5)
            
            self._wait_for_rate_limit()
            
            download_url = self.ANALYTICS_BASE_URL + self.WAREHOUSE_DOWNLOAD_ENDPOINT.format(
                task_id=task_id
            )
            
            print(f"📥 Скачивание результата...")
            
            response = self.session.get(download_url, timeout=60)
            response.raise_for_status()
            remains_data = response.json()
            
            print(f"✅ Получено записей: {len(remains_data)}")
            
            return remains_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка Warehouse Remains API: {e}")
            return []
    
    def get_supplier_orders(
        self,
        date_from: str,
        flag: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получить заказы из Supplier Orders API.
        
        Args:
            date_from: Дата начала в формате RFC3339 (YYYY-MM-DD или с временем)
            flag: 0 - по lastChangeDate, 1 - по date
            
        Returns:
            Список заказов
        """
        self._wait_for_rate_limit()
        
        url = self.STATISTICS_BASE_URL + self.SUPPLIER_ORDERS_ENDPOINT
        params = {
            "dateFrom": date_from,
            "flag": flag
        }
        
        print(f"🛒 Запрос Supplier Orders: с {date_from}, flag={flag}")
        
        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            orders = response.json()
            
            print(f"✅ Получено заказов: {len(orders)}")
            
            return orders
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка Supplier Orders API: {e}")
            return []
    
    def collect_complete_data(
        self,
        period_start: str,
        period_end: str,
        nm_ids: Optional[List[int]] = None,
        brand_names: Optional[List[str]] = None
    ) -> List[ProductMetrics]:
        """
        Собрать полные данные по товарам из всех источников.
        
        Args:
            period_start: Начало периода (YYYY-MM-DD)
            period_end: Конец периода (YYYY-MM-DD)
            nm_ids: Список артикулов WB (опционально)
            brand_names: Список брендов (опционально)
            
        Returns:
            Список объектов ProductMetrics с полными данными
        """
        print("=" * 80)
        print("🚀 НАЧАЛО СБОРА ПОЛНЫХ ДАННЫХ")
        print("=" * 80)
        
        # 1. Получаем данные из Sales Funnel API
        print("\n📊 ШАГ 1/3: Sales Funnel API")
        funnel_data = self.get_sales_funnel_data(
            period_start, period_end, nm_ids, brand_names
        )
        products = funnel_data.get('data', {}).get('products', [])
        
        if not products:
            print("⚠️ Нет данных из Sales Funnel API")
            return []
        
        # 2. Получаем остатки по складам
        print("\n📦 ШАГ 2/3: Warehouse Remains API")
        warehouse_data = self.get_warehouse_remains()
        
        # Индексируем по nmId для быстрого доступа
        warehouse_by_nm = {}
        for item in warehouse_data:
            nm_id = item.get('nmId')
            if nm_id:
                warehouse_by_nm[nm_id] = item
        
        # 3. Получаем заказы
        print("\n🛒 ШАГ 3/3: Supplier Orders API")
        orders = self.get_supplier_orders(period_start)
        
        # Группируем заказы по nmId
        orders_by_nm = {}
        for order in orders:
            nm_id = order.get('nmId')
            if nm_id:
                if nm_id not in orders_by_nm:
                    orders_by_nm[nm_id] = []
                orders_by_nm[nm_id].append(order)
        
        # 4. Объединяем все данные
        print("\n🔄 Объединение данных...")
        result = []
        
        for product in products:
            product_info = product.get('product', {})
            stats = product.get('statistic', {}).get('selected', {})
            nm_id = product_info.get('nmId')
            
            if not nm_id:
                continue
            
            # Данные из Sales Funnel
            brand = product_info.get('brandName', '')
            subject = product_info.get('subjectName', '')
            subject_id = product_info.get('subjectId', 0)
            vendor_code = product_info.get('vendorCode', '')
            
            stocks = product_info.get('stocks', {})
            stocks_wb = stocks.get('wb', 0)
            stocks_mp = stocks.get('mp', 0)
            stocks_total = stocks_wb + stocks_mp
            
            orders_total = stats.get('orderCount', 0)
            turnover = stats.get('timeToReady', {})
            turnover_days = turnover.get('days', 0)
            avg_orders_per_day = stats.get('avgOrdersCountPerDay', 0.0)
            
            conversions = stats.get('conversions', {})
            conversion_to_cart = conversions.get('addToCartPercent', 0)
            conversion_to_order = conversions.get('cartToOrderPercent', 0)
            buyout_percent = conversions.get('buyoutPercent', 0)
            
            avg_price = stats.get('avgPrice', 0)
            order_sum_total = stats.get('orderSum', 0)
            buyout_count = stats.get('buyoutCount', 0)
            buyout_sum = stats.get('buyoutSum', 0)
            
            # Данные из Warehouse Remains (разбивка по складам)
            warehouse_info = warehouse_by_nm.get(nm_id, {})
            warehouses = warehouse_info.get('warehouses', [])
            
            stocks_by_warehouse = {}
            in_transit_to_wb = 0
            in_transit_to_customer = 0  # Инициализируем здесь, из данных Warehouse Remains
            
            for wh in warehouses:
                wh_name = wh.get('warehouseName', '')
                quantity = wh.get('quantity', 0)
                if wh_name:
                    stocks_by_warehouse[wh_name] = quantity
                    # "В пути до получателей" - это товары, которые едут к покупателю
                    if wh_name == 'В пути до получателей':
                        in_transit_to_customer = quantity
                    # "В пути возвраты на склад WB" - товары возвращаются на склад
                    elif 'В пути' in wh_name or 'транзит' in wh_name.lower():
                        in_transit_to_wb += quantity
            
            # Данные из Supplier Orders (разбивка заказов)
            nm_orders = orders_by_nm.get(nm_id, [])
            
            orders_wb_warehouses = 0
            orders_fbs_warehouses = 0
            orders_by_warehouse = {}
            
            for order in nm_orders:
                wh_name = order.get('warehouseName', '')
                wh_type = order.get('warehouseType', '')
                is_cancel = order.get('isCancel', False)
                
                # Считаем только не отмененные заказы
                if not is_cancel:
                    # Разбивка по типу склада
                    if wh_type == 'Склад WB':
                        orders_wb_warehouses += 1
                    elif wh_type == 'Склад продавца':
                        orders_fbs_warehouses += 1
                    
                    # Разбивка по конкретным складам
                    if wh_name:
                        orders_by_warehouse[wh_name] = orders_by_warehouse.get(wh_name, 0) + 1
            
            # Создаем объект с полными метриками
            metrics = ProductMetrics(
                brand=brand,
                subject=subject,
                subject_id=subject_id,
                vendor_code=vendor_code,
                nm_id=nm_id,
                orders_total=orders_total,
                orders_wb_warehouses=orders_wb_warehouses,
                orders_fbs_warehouses=orders_fbs_warehouses,
                orders_by_warehouse=orders_by_warehouse,
                stocks_total=stocks_total,
                stocks_wb=stocks_wb,
                stocks_mp=stocks_mp,
                stocks_by_warehouse=stocks_by_warehouse,
                in_transit_to_customer=in_transit_to_customer,
                in_transit_to_wb_warehouse=in_transit_to_wb,
                turnover_days=turnover_days,
                avg_orders_per_day=avg_orders_per_day,
                conversion_to_cart=conversion_to_cart,
                conversion_to_order=conversion_to_order,
                buyout_percent=buyout_percent,
                avg_price=avg_price,
                order_sum_total=order_sum_total,
                buyout_count=buyout_count,
                buyout_sum=buyout_sum
            )
            
            result.append(metrics)
        
        print(f"\n✅ Обработано товаров: {len(result)}")
        print("=" * 80)
        
        return result
    
    def save_to_json(self, data: List[ProductMetrics], filename: str):
        """
        Сохранить данные в JSON файл.
        
        Args:
            data: Список объектов ProductMetrics
            filename: Имя файла для сохранения
        """
        output = {
            "timestamp": datetime.now().isoformat(),
            "total_products": len(data),
            "products": [asdict(item) for item in data]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Данные сохранены в {filename}")
    
    def save_to_csv(self, data: List[ProductMetrics], filename: str):
        """
        Сохранить данные в CSV файл с группировкой колонок по складам.
        
        Args:
            data: Список объектов ProductMetrics
            filename: Имя файла для сохранения
        """
        import csv
        
        if not data:
            print("⚠️ Нет данных для сохранения")
            return
        
        # Определяем все уникальные физические склады (исключаем служебные)
        all_warehouses = set()
        service_warehouses = {
            'В пути до получателей',
            'В пути возвраты на склад WB', 
            'Всего находится на складах',
            'Остальные'
        }
        
        for item in data:
            for wh in item.stocks_by_warehouse.keys():
                if wh not in service_warehouses:
                    all_warehouses.add(wh)
            for wh in item.orders_by_warehouse.keys():
                if wh not in service_warehouses:
                    all_warehouses.add(wh)
        
        # Сортируем склады по алфавиту
        all_warehouses = sorted(all_warehouses)
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            # Строка 1: Группы колонок (как в HTML)
            header_row1 = ['', '', '', '']  # Основная информация (4 колонки)
            header_row1.extend([''] * 6)     # Общие метрики (6 колонок)
            
            for warehouse in all_warehouses:
                header_row1.extend([warehouse, '', ''])  # Каждый склад - 3 колонки
            
            # Строка 2: Названия колонок
            header_row2 = [
                'Бренд',
                'Предмет', 
                'Артикул продавца',
                'Артикул товара (nmid)'
            ]
            header_row2.extend([
                'В пути до покупателя',
                'В пути конв. на склад WB',
                'Всего заказов на складах WB',
                'Заказы (всего)',
                'Остатки (всего)',
                'Оборачиваемость (дни)'
            ])
            
            for warehouse in all_warehouses:
                header_row2.extend(['Остатки', 'Заказы', 'Оборач.'])
            
            writer.writerow(header_row1)
            writer.writerow(header_row2)
            
            # Данные
            for item in data:
                row = [
                    item.brand,
                    item.subject,
                    item.vendor_code,
                    item.nm_id,
                    item.in_transit_to_customer,
                    item.in_transit_to_wb_warehouse,
                    item.orders_wb_warehouses,
                    item.orders_total,
                    item.stocks_total,
                    item.turnover_days
                ]
                
                # Добавляем данные по каждому складу
                for warehouse in all_warehouses:
                    stocks = item.stocks_by_warehouse.get(warehouse, 0)
                    orders = item.orders_by_warehouse.get(warehouse, 0)
                    
                    # Рассчитываем оборачиваемость склада
                    if orders > 0 and stocks > 0:
                        turnover = round(stocks / orders, 1)
                    else:
                        turnover = 0
                    
                    row.extend([stocks, orders, turnover])
                
                writer.writerow(row)
        
        print(f"💾 Данные сохранены в {filename}")
    
    def save_to_html(self, data: List[ProductMetrics], filename: str):
        """
        Сохранить данные в HTML файл с красивым оформлением.
        
        Args:
            data: Список объектов ProductMetrics
            filename: Имя файла для сохранения
        """
        if not data:
            print("⚠️ Нет данных для сохранения")
            return
        
        # Определяем физические склады
        all_warehouses = set()
        service_warehouses = {
            'В пути до получателей',
            'В пути возвраты на склад WB',
            'Всего находится на складах',
            'Остальные'
        }
        
        for item in data:
            for wh in item.stocks_by_warehouse.keys():
                if wh not in service_warehouses:
                    all_warehouses.add(wh)
            for wh in item.orders_by_warehouse.keys():
                if wh not in service_warehouses:
                    all_warehouses.add(wh)
        
        all_warehouses = sorted(all_warehouses)
        
        # Генерируем HTML
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Аналитика Wildberries - {datetime.now().strftime("%d.%m.%Y")}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .table-wrapper {{
            overflow-x: auto;
            padding: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        thead tr:first-child th {{
            padding: 12px 8px;
            text-align: center;
            font-weight: 700;
            font-size: 13px;
            border-right: 1px solid rgba(255,255,255,0.3);
        }}
        thead tr:last-child th {{
            padding: 10px 8px;
            text-align: center;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-right: 1px solid rgba(255,255,255,0.3);
        }}
        tbody tr {{
            border-bottom: 1px solid #e5e7eb;
            transition: background-color 0.2s;
        }}
        tbody tr:hover {{
            background-color: #f0f4ff;
        }}
        tbody tr:last-child {{
            border-bottom: none;
        }}
        td {{
            padding: 14px 8px;
            color: #374151;
            text-align: center;
            border-right: 1px solid #f3f4f6;
        }}
        td:nth-child(-n+4) {{
            text-align: left;
            font-weight: 500;
        }}
        .turnover-good {{
            background-color: #d1fae5;
            color: #065f46;
            font-weight: 600;
        }}
        .turnover-medium {{
            background-color: #fef3c7;
            color: #92400e;
            font-weight: 600;
        }}
        .turnover-bad {{
            background-color: #fee2e2;
            color: #991b1b;
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #6b7280;
            font-size: 12px;
            background: #f9fafb;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Аналитика Wildberries - Разбивка по складам</h1>
            <p>Экспортировано: {datetime.now().strftime("%d.%m.%Y, %H:%M:%S")}</p>
            <p>Всего товаров: {len(data)}</p>
        </div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th colspan="4">Основная информация</th>
                        <th colspan="6">Общие метрики</th>
"""
        
        # Добавляем заголовки складов
        for warehouse in all_warehouses:
            html_content += f'                        <th colspan="3">{warehouse}</th>\n'
        
        html_content += """                    </tr>
                    <tr>
                        <th>Бренд</th>
                        <th>Предмет</th>
                        <th>Артикул продавца</th>
                        <th>Артикул товара (nmid)</th>
                        <th>В пути до покупателя</th>
                        <th>В пути конв. на склад WB</th>
                        <th>Всего заказов на складах WB</th>
                        <th>Заказы (всего)</th>
                        <th>Остатки (всего)</th>
                        <th>Оборачиваемость (дни)</th>
"""
        
        # Добавляем подзаголовки для каждого склада
        for _ in all_warehouses:
            html_content += '                        <th>Остатки</th><th>Заказы</th><th>Оборач.</th>\n'
        
        html_content += """                    </tr>
                </thead>
                <tbody>
"""
        
        # Добавляем строки с данными
        for item in data:
            html_content += f"""                    <tr>
                        <td>{item.brand}</td>
                        <td>{item.subject}</td>
                        <td>{item.vendor_code}</td>
                        <td>{item.nm_id}</td>
                        <td>{item.in_transit_to_customer}</td>
                        <td>{item.in_transit_to_wb_warehouse}</td>
                        <td>{item.orders_wb_warehouses}</td>
                        <td>{item.orders_total}</td>
                        <td>{item.stocks_total}</td>
                        <td>{item.turnover_days}</td>
"""
            
            # Добавляем данные по складам
            for warehouse in all_warehouses:
                stocks = item.stocks_by_warehouse.get(warehouse, 0)
                orders = item.orders_by_warehouse.get(warehouse, 0)
                
                # Рассчитываем оборачиваемость
                if orders > 0 and stocks > 0:
                    turnover = round(stocks / orders, 1)
                else:
                    turnover = 0
                
                # Определяем класс для подсветки оборачиваемости
                turnover_class = ''
                if turnover > 0:
                    if turnover <= 5:
                        turnover_class = 'turnover-good'
                    elif turnover <= 10:
                        turnover_class = 'turnover-medium'
                    else:
                        turnover_class = 'turnover-bad'
                
                html_content += f'                        <td>{stocks}</td><td>{orders}</td><td class="{turnover_class}">{turnover if turnover > 0 else "-"}</td>\n'
            
            html_content += '                    </tr>\n'
        
        html_content += """                </tbody>
            </table>
        </div>
        <div class="footer">
            Создано с помощью Wildberries Data Collector<br>
            🟢 Хорошая оборачиваемость (≤5 дней) | 🟡 Средняя (6-10 дней) | 🔴 Высокая (>10 дней)
        </div>
    </div>
</body>
</html>"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"💾 HTML сохранен в {filename}")


def main():
    """Пример использования."""
    
    # API ключ (замените на свой)
    API_KEY = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJlbnQiOjEsImV4cCI6MTc3NjM3NjUyNywiaWQiOiIwMTk5ZWM3Mi0yNGRjLTcxMjItYjk0ZC0zNDFiYzM3YmFhYTIiLCJpaWQiOjEwMjEwNTIyNSwib2lkIjoxMjc4Njk0LCJzIjoxMDczNzQyOTcyLCJzaWQiOiJiYmY1MWY5MS0zYjFhLTQ5MGMtOGE4Ni1hNzNkYjgxZTlmNjkiLCJ0IjpmYWxzZSwidWlkIjoxMDIxMDUyMjV9.mPrskzcbBDjUj5lxTcJjmjaPtt2Mx5C0aeok7HytpUk2eWRYngILZotCc1oXVoIoAWJclh-4t0E4F4xeCgOtPg"
    
    # Инициализация клиента
    collector = WildberriesDataCollector(api_key=API_KEY)
    
    # Период для анализа (последние 7 дней)
    period_end = datetime.now()
    period_start = period_end - timedelta(days=7)
    
    # Сбор данных
    products = collector.collect_complete_data(
        period_start=period_start.strftime("%Y-%m-%d"),
        period_end=period_end.strftime("%Y-%m-%d"),
        brand_names=["ITS COLLAGEN"]  # Можно указать фильтр по брендам
    )
    
    # Вывод результатов в консоль
    print("\n" + "=" * 80)
    print("📊 РЕЗУЛЬТАТЫ")
    print("=" * 80)
    
    for idx, product in enumerate(products[:3], 1):  # Показываем первые 3 товара
        print(f"\n{idx}. {product.vendor_code} (nmId: {product.nm_id})")
        print(f"   Бренд: {product.brand}")
        print(f"   Предмет: {product.subject}")
        print(f"   Заказы всего: {product.orders_total}")
        print(f"   Заказы WB: {product.orders_wb_warehouses}, FBS: {product.orders_fbs_warehouses}")
        print(f"   Остатки всего: {product.stocks_total} (WB: {product.stocks_wb}, МП: {product.stocks_mp})")
        print(f"   В пути до покупателя: {product.in_transit_to_customer}")
        print(f"   В пути на склад WB: {product.in_transit_to_wb_warehouse}")
        print(f"   Оборачиваемость: {product.turnover_days} дней")
        
        if product.stocks_by_warehouse:
            print(f"   Разбивка остатков по складам:")
            for wh, qty in sorted(product.stocks_by_warehouse.items())[:5]:
                print(f"      - {wh}: {qty} шт.")
        
        if product.orders_by_warehouse:
            print(f"   Разбивка заказов по складам:")
            for wh, qty in sorted(product.orders_by_warehouse.items())[:5]:
                print(f"      - {wh}: {qty} шт.")
    
    if len(products) > 3:
        print(f"\n... и ещё {len(products) - 3} товаров")
    
    # Сохранение в файлы
    print("\n" + "=" * 80)
    print("💾 СОХРАНЕНИЕ ДАННЫХ")
    print("=" * 80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    collector.save_to_json(products, f"complete_data_{timestamp}.json")
    
    # CSV
    collector.save_to_csv(products, f"complete_data_{timestamp}.csv")
    
    # HTML (красивая визуализация)
    collector.save_to_html(products, f"complete_data_{timestamp}.html")
    
    print("\n✅ Готово!")


if __name__ == "__main__":
    main()
