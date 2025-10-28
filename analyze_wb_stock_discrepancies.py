"""
Глубокий анализ расхождений между Stock Tracker и официальным отчетом Wildberries.

Этот скрипт детально анализирует CSV файл с данными WB и сравнивает его с логикой
приложения Stock Tracker для выявления причин расхождений.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import re


class WBDiscrepancyAnalyzer:
    """Анализатор расхождений между WB отчетом и Stock Tracker."""
    
    def __init__(self, csv_file_path: str):
        """
        Инициализация анализатора.
        
        Args:
            csv_file_path: Путь к CSV файлу с данными WB
        """
        self.csv_file_path = csv_file_path
        self.wb_data = []
        self.products = {}
        self.warehouses_by_product = defaultdict(dict)
        self.warehouse_names = set()
        
    def load_csv_data(self):
        """Загрузить и распарсить CSV файл WB."""
        print(f"📂 Загрузка данных из: {self.csv_file_path}")
        
        # Читаем файл построчно чтобы пропустить первую строку если нужно
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            # Пробуем определить правильный формат
            first_line = f.readline()
            
            # Если первая строка содержит "Остатки по КТ" - это заголовок таблицы, пропускаем
            if 'Остатки по КТ' in first_line or 'Остатки по' in first_line:
                print("   ⚠️ Пропускаем заголовок таблицы WB")
                # Следующая строка - настоящие колонки
                pass
            else:
                # Возвращаемся в начало если это был CSV заголовок
                f.seek(0)
            
            reader = csv.DictReader(f)
            for row in reader:
                self.wb_data.append(row)
        
        print(f"   ✅ Загружено {len(self.wb_data)} записей")
        
        # Отладочный вывод колонок
        if self.wb_data:
            print(f"   📋 Обнаружены колонки: {list(self.wb_data[0].keys())[:5]}...")
        
    def analyze_warehouse_names(self):
        """Анализ всех уникальных названий складов."""
        print("\n🏪 Анализ складов в WB отчете:")
        
        # Извлекаем все уникальные склады
        for row in self.wb_data:
            warehouse_name = row.get('Склад', '').strip()
            if warehouse_name:
                self.warehouse_names.add(warehouse_name)
        
        print(f"   Всего уникальных складов: {len(self.warehouse_names)}")
        
        # Категоризация складов
        marketplace_warehouses = []
        regular_warehouses = []
        virtual_warehouses = []
        unknown_warehouses = []
        
        for warehouse in sorted(self.warehouse_names):
            warehouse_lower = warehouse.lower()
            
            # Маркетплейс/FBS склады
            if any(indicator in warehouse_lower for indicator in 
                   ['маркетплейс', 'marketplace', 'склад продавца', 'fbs']):
                marketplace_warehouses.append(warehouse)
            # Виртуальные склады
            elif 'виртуальный' in warehouse_lower:
                virtual_warehouses.append(warehouse)
            # Обычные склады (города)
            elif any(char.isalpha() for char in warehouse):
                regular_warehouses.append(warehouse)
            else:
                unknown_warehouses.append(warehouse)
        
        print(f"\n   📊 Категории складов:")
        print(f"      • Маркетплейс/FBS: {len(marketplace_warehouses)}")
        for wh in marketplace_warehouses:
            print(f"         - {wh}")
        
        print(f"\n      • Обычные склады WB: {len(regular_warehouses)}")
        for wh in regular_warehouses[:10]:  # Показываем первые 10
            print(f"         - {wh}")
        if len(regular_warehouses) > 10:
            print(f"         ... и ещё {len(regular_warehouses) - 10}")
        
        print(f"\n      • Виртуальные склады: {len(virtual_warehouses)}")
        for wh in virtual_warehouses:
            print(f"         - {wh}")
        
        if unknown_warehouses:
            print(f"\n      • Неопознанные: {len(unknown_warehouses)}")
            for wh in unknown_warehouses:
                print(f"         - {wh}")
        
        return {
            'marketplace': marketplace_warehouses,
            'regular': regular_warehouses,
            'virtual': virtual_warehouses,
            'unknown': unknown_warehouses
        }
    
    def group_by_product(self):
        """Группировка данных по артикулам."""
        print("\n📦 Группировка данных по артикулам:")
        
        for row in self.wb_data:
            seller_article = row.get('Артикул продавца', '').strip()
            wb_article = row.get('Артикул WB', '').strip()
            warehouse = row.get('Склад', '').strip()
            region = row.get('Регион', '').strip()
            availability = row.get('Доступность', '').strip()
            
            # Заказы и остатки
            orders_str = row.get('Заказали, шт', '').strip()
            stock_str = row.get('Остатки на текущий день, шт', '').strip()
            
            try:
                orders = int(orders_str) if orders_str and orders_str.isdigit() else 0
            except (ValueError, AttributeError):
                orders = 0
            
            try:
                stock = int(stock_str) if stock_str and stock_str.isdigit() else 0
            except (ValueError, AttributeError):
                stock = 0
            
            if not seller_article or not wb_article:
                continue
            
            # Создаем ключ продукта
            product_key = (seller_article, wb_article)
            
            # Инициализируем продукт если нужно
            if product_key not in self.products:
                self.products[product_key] = {
                    'seller_article': seller_article,
                    'wb_article': wb_article,
                    'total_orders': 0,
                    'total_stock': 0,
                    'warehouses': {}
                }
            
            # Добавляем склад
            if warehouse not in self.products[product_key]['warehouses']:
                self.products[product_key]['warehouses'][warehouse] = {
                    'region': region,
                    'availability': availability,
                    'orders': 0,
                    'stock': 0
                }
            
            # Обновляем данные по складу
            self.products[product_key]['warehouses'][warehouse]['orders'] += orders
            self.products[product_key]['warehouses'][warehouse]['stock'] += stock
            
            # Обновляем итоги
            self.products[product_key]['total_orders'] += orders
            self.products[product_key]['total_stock'] += stock
        
        print(f"   ✅ Обработано {len(self.products)} уникальных артикулов")
        
    def analyze_marketplace_impact(self):
        """Анализ влияния склада Маркетплейс на остатки и заказы."""
        print("\n💼 Анализ влияния склада Маркетплейс:")
        
        marketplace_products = []
        total_marketplace_stock = 0
        total_marketplace_orders = 0
        
        for product_key, product_data in self.products.items():
            seller_article = product_data['seller_article']
            
            # Ищем Маркетплейс среди складов
            marketplace_data = None
            for warehouse_name, warehouse_data in product_data['warehouses'].items():
                if 'маркетплейс' in warehouse_name.lower() or 'marketplace' in warehouse_name.lower():
                    marketplace_data = warehouse_data
                    break
            
            if marketplace_data:
                mp_stock = marketplace_data['stock']
                mp_orders = marketplace_data['orders']
                total_stock = product_data['total_stock']
                
                if mp_stock > 0 or mp_orders > 0:
                    percentage = (mp_stock / total_stock * 100) if total_stock > 0 else 0
                    
                    marketplace_products.append({
                        'article': seller_article,
                        'mp_stock': mp_stock,
                        'mp_orders': mp_orders,
                        'total_stock': total_stock,
                        'percentage': percentage
                    })
                    
                    total_marketplace_stock += mp_stock
                    total_marketplace_orders += mp_orders
        
        # Сортируем по проценту
        marketplace_products.sort(key=lambda x: x['percentage'], reverse=True)
        
        print(f"\n   📊 Продукты со складом Маркетплейс: {len(marketplace_products)}")
        print(f"   📦 Общие остатки на Маркетплейс: {total_marketplace_stock}")
        print(f"   📋 Общие заказы с Маркетплейс: {total_marketplace_orders}")
        
        print("\n   🔝 ТОП-10 продуктов по доле Маркетплейс:")
        for i, product in enumerate(marketplace_products[:10], 1):
            print(f"      {i}. {product['article']}")
            print(f"         Остатки МП: {product['mp_stock']} из {product['total_stock']} ({product['percentage']:.1f}%)")
            print(f"         Заказы МП: {product['mp_orders']}")
        
        return marketplace_products
    
    def check_warehouse_filtering_logic(self, warehouse_categories: Dict[str, List[str]]):
        """Проверка логики фильтрации складов в приложении."""
        print("\n🔍 Проверка логики фильтрации складов:")
        
        # Эмулируем логику is_real_warehouse из calculator.py
        def is_real_warehouse_emulated(warehouse_name: str) -> bool:
            """Эмуляция функции is_real_warehouse из приложения."""
            if not warehouse_name:
                return False
            
            warehouse_lower = warehouse_name.lower()
            
            # Исключения из реального кода
            delivery_statuses = {
                "в пути до получателей",
                "в пути возврата на склад wb",
                "всего находится на складах",
                "в пути возврата с пвз",
                "в пути с пвз покупателю",
                "удержания и возмещения",
                "к доплате",
                "общий итог"
            }
            
            if warehouse_name in delivery_statuses:
                return False
            
            if any(word in warehouse_lower for word in ["итог", "всего", "общий"]):
                return False
            
            if "в пути" in warehouse_lower:
                return False
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: Маркетплейс
            marketplace_indicators = [
                "маркетплейс", "marketplace",
                "склад продавца", "склад селлера",
                "fbs", "мп ", "mp "
            ]
            
            if any(indicator in warehouse_lower for indicator in marketplace_indicators):
                return True
            
            # Базовая проверка на название города (русские буквы)
            if re.match(r'^[А-Яа-я]', warehouse_name):
                return True
            
            return False
        
        # Проверяем каждую категорию
        print("\n   📋 Проверка фильтрации по категориям:")
        
        for category_name, warehouses in warehouse_categories.items():
            print(f"\n      {category_name.upper()}: {len(warehouses)} складов")
            
            filtered_in = []
            filtered_out = []
            
            for warehouse in warehouses:
                if is_real_warehouse_emulated(warehouse):
                    filtered_in.append(warehouse)
                else:
                    filtered_out.append(warehouse)
            
            print(f"         ✅ Будут включены: {len(filtered_in)}")
            if filtered_in and len(filtered_in) <= 5:
                for wh in filtered_in:
                    print(f"            - {wh}")
            
            print(f"         ❌ Будут отфильтрованы: {len(filtered_out)}")
            if filtered_out:
                for wh in filtered_out[:3]:
                    print(f"            - {wh}")
                if len(filtered_out) > 3:
                    print(f"            ... и ещё {len(filtered_out) - 3}")
    
    def compare_orders_logic(self):
        """Сравнение логики подсчета заказов."""
        print("\n📊 Анализ логики подсчета заказов:")
        
        # Группируем заказы по артикулам
        orders_by_article = defaultdict(lambda: {'warehouses': defaultdict(int), 'total': 0})
        
        for row in self.wb_data:
            seller_article = row.get('Артикул продавца', '').strip()
            warehouse = row.get('Склад', '').strip()
            orders_str = row.get('Заказали, шт', '').strip()
            
            try:
                orders = int(orders_str) if orders_str and orders_str.isdigit() else 0
            except (ValueError, AttributeError):
                orders = 0
            
            if orders > 0 and seller_article:
                orders_by_article[seller_article]['warehouses'][warehouse] += orders
                orders_by_article[seller_article]['total'] += orders
        
        print(f"\n   📦 Артикулов с заказами: {len(orders_by_article)}")
        
        # Проверяем несоответствия
        print("\n   🔍 Проверка соответствия суммы заказов по складам:")
        discrepancies = []
        
        for article, data in orders_by_article.items():
            warehouse_sum = sum(data['warehouses'].values())
            total = data['total']
            
            if warehouse_sum != total:
                discrepancies.append({
                    'article': article,
                    'total': total,
                    'warehouse_sum': warehouse_sum,
                    'diff': abs(total - warehouse_sum)
                })
        
        if discrepancies:
            print(f"      ⚠️ Найдено {len(discrepancies)} несоответствий:")
            for disc in discrepancies[:5]:
                print(f"         - {disc['article']}: итого={disc['total']}, сумма={disc['warehouse_sum']}, разница={disc['diff']}")
        else:
            print(f"      ✅ Все артикулы: сумма по складам = общему итогу")
    
    def generate_detailed_report(self):
        """Генерация детального отчета."""
        print("\n" + "="*80)
        print("📄 ДЕТАЛЬНЫЙ ОТЧЕТ О РАСХОЖДЕНИЯХ")
        print("="*80)
        
        report = {
            'summary': {
                'total_products': len(self.products),
                'total_warehouses': len(self.warehouse_names),
                'total_stock': sum(p['total_stock'] for p in self.products.values()),
                'total_orders': sum(p['total_orders'] for p in self.products.values())
            },
            'products': []
        }
        
        # Детальный анализ по каждому продукту
        for product_key, product_data in self.products.items():
            seller_article = product_data['seller_article']
            wb_article = product_data['wb_article']
            
            # Проверяем наличие Маркетплейс
            has_marketplace = any('маркетплейс' in wh.lower() or 'marketplace' in wh.lower() 
                                for wh in product_data['warehouses'].keys())
            
            # Подсчитываем склады по типам
            marketplace_warehouses = []
            regular_warehouses = []
            virtual_warehouses = []
            
            for warehouse_name, warehouse_data in product_data['warehouses'].items():
                wh_lower = warehouse_name.lower()
                
                if 'маркетплейс' in wh_lower or 'marketplace' in wh_lower:
                    marketplace_warehouses.append({
                        'name': warehouse_name,
                        'stock': warehouse_data['stock'],
                        'orders': warehouse_data['orders']
                    })
                elif 'виртуальный' in wh_lower:
                    virtual_warehouses.append({
                        'name': warehouse_name,
                        'stock': warehouse_data['stock'],
                        'orders': warehouse_data['orders']
                    })
                else:
                    regular_warehouses.append({
                        'name': warehouse_name,
                        'stock': warehouse_data['stock'],
                        'orders': warehouse_data['orders']
                    })
            
            product_report = {
                'seller_article': seller_article,
                'wb_article': wb_article,
                'total_stock': product_data['total_stock'],
                'total_orders': product_data['total_orders'],
                'total_warehouses': len(product_data['warehouses']),
                'has_marketplace': has_marketplace,
                'marketplace_warehouses': marketplace_warehouses,
                'regular_warehouses_count': len(regular_warehouses),
                'virtual_warehouses_count': len(virtual_warehouses)
            }
            
            report['products'].append(product_report)
        
        # Сохраняем отчет в JSON
        report_path = Path('wb_discrepancy_analysis_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Детальный отчет сохранен в: {report_path}")
        
        # Выводим ключевые находки
        print("\n🔑 КЛЮЧЕВЫЕ НАХОДКИ:")
        
        products_with_marketplace = sum(1 for p in report['products'] if p['has_marketplace'])
        print(f"   • Артикулов со складом Маркетплейс: {products_with_marketplace} из {len(report['products'])}")
        
        marketplace_stock_total = sum(
            sum(wh['stock'] for wh in p['marketplace_warehouses'])
            for p in report['products']
        )
        print(f"   • Остатки на Маркетплейс: {marketplace_stock_total}")
        
        marketplace_orders_total = sum(
            sum(wh['orders'] for wh in p['marketplace_warehouses'])
            for p in report['products']
        )
        print(f"   • Заказы с Маркетплейс: {marketplace_orders_total}")
        
        return report
    
    def run_full_analysis(self):
        """Запустить полный анализ."""
        print("\n" + "🔬" * 40)
        print("ГЛУБОКИЙ АНАЛИЗ РАСХОЖДЕНИЙ WB STOCK TRACKER")
        print("🔬" * 40 + "\n")
        
        # 1. Загрузка данных
        self.load_csv_data()
        
        # 2. Анализ складов
        warehouse_categories = self.analyze_warehouse_names()
        
        # 3. Группировка по продуктам
        self.group_by_product()
        
        # 4. Анализ Маркетплейс
        marketplace_products = self.analyze_marketplace_impact()
        
        # 5. Проверка логики фильтрации
        self.check_warehouse_filtering_logic(warehouse_categories)
        
        # 6. Анализ заказов
        self.compare_orders_logic()
        
        # 7. Генерация отчета
        report = self.generate_detailed_report()
        
        print("\n" + "="*80)
        print("✅ АНАЛИЗ ЗАВЕРШЕН")
        print("="*80 + "\n")
        
        return report


def main():
    """Основная функция."""
    # Путь к CSV файлу
    csv_path = r"c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker\26-10-2025 История остатков с 20-10-2025 по 26-10-2025_export.csv"
    
    # Создаем анализатор
    analyzer = WBDiscrepancyAnalyzer(csv_path)
    
    # Запускаем полный анализ
    report = analyzer.run_full_analysis()
    
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("   1. Проверить что склад 'Маркетплейс' корректно обрабатывается в calculator.py")
    print("   2. Убедиться что все склады из WB API попадают в группировку")
    print("   3. Проверить логику фильтрации виртуальных складов")
    print("   4. Добавить детальное логирование загрузки складов из API")
    

if __name__ == "__main__":
    main()
