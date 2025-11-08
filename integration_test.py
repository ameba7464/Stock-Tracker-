#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End интеграционный тест для Stock Tracker
Тестирует полный цикл синхронизации данных от API до Google Sheets

Проверяет:
1. Загрузку данных из Wildberries API (FBO + FBS + Orders)
2. Обработку и валидацию данных
3. Синхронизацию с Google Sheets
4. Целостность данных в таблице
5. Производительность и оптимизацию
"""

import sys
import os
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Установка кодировки UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


class IntegrationTest:
    """End-to-End интеграционный тест"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.results = {}
        self.test_data = {}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Запустить все тесты"""
        self.start_time = datetime.now()
        
        print("="*80)
        print("🧪 END-TO-END ИНТЕГРАЦИОННЫЙ ТЕСТ")
        print("="*80)
        print(f"Начало: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        # Тест 1: Загрузка конфигурации
        await self.test_configuration()
        
        # Тест 2: Загрузка данных из Wildberries API
        await self.test_api_data_loading()
        
        # Тест 3: Обработка и валидация данных
        await self.test_data_processing()
        
        # Тест 4: Синхронизация с Google Sheets
        await self.test_sheets_synchronization()
        
        # Тест 5: Проверка целостности данных
        await self.test_data_integrity()
        
        # Тест 6: Тест производительности
        await self.test_performance()
        
        self.end_time = datetime.now()
        
        return self.generate_report()
    
    async def test_configuration(self):
        """Тест 1: Загрузка конфигурации"""
        print("\n🔍 ТЕСТ 1: Загрузка конфигурации")
        print("-"*80)
        
        test_start = time.time()
        
        try:
            from stock_tracker.utils.config import get_config
            
            config = get_config()
            
            # Проверяем критические настройки
            checks = {
                "Wildberries API Key": bool(config.wildberries.api_key),
                "Google Sheets ID": bool(config.google_sheets.sheet_id),
                "Service Account": Path(config.google_sheets.service_account_key_path).exists(),
                "Log Level": config.app.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"],
                "Base URLs": all([
                    config.wildberries.base_url,
                    config.wildberries.statistics_base_url
                ])
            }
            
            all_passed = all(checks.values())
            
            for check_name, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"{status} {check_name}")
            
            self.results['configuration'] = {
                "passed": all_passed,
                "duration": time.time() - test_start,
                "checks": checks
            }
            
            if all_passed:
                print("✅ Конфигурация загружена успешно")
            else:
                print("❌ Ошибки в конфигурации")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            self.results['configuration'] = {
                "passed": False,
                "duration": time.time() - test_start,
                "error": str(e)
            }
    
    async def test_api_data_loading(self):
        """Тест 2: Загрузка данных из API"""
        print("\n🔍 ТЕСТ 2: Загрузка данных из Wildberries API")
        print("-"*80)
        
        test_start = time.time()
        
        try:
            from stock_tracker.api.wildberries_client import WildberriesClient
            from stock_tracker.utils.config import get_config
            
            config = get_config()
            wb_client = WildberriesClient(config.wildberries.api_key)
            
            # Загрузка данных
            print("📥 Загрузка остатков FBO (Statistics API)...")
            stocks_fbo = await wb_client.get_stocks()
            fbo_count = len(stocks_fbo) if stocks_fbo else 0
            print(f"   Получено: {fbo_count} записей")
            
            print("📥 Загрузка остатков FBS (Marketplace API v3)...")
            stocks_fbs = await wb_client.get_marketplace_stocks()
            fbs_count = len(stocks_fbs) if stocks_fbs else 0
            print(f"   Получено: {fbs_count} записей")
            
            print("📥 Загрузка заказов (Orders API)...")
            orders = await wb_client.get_supplier_orders()
            orders_count = len(orders) if orders else 0
            print(f"   Получено: {orders_count} записей")
            
            # Сохраняем данные для следующих тестов
            self.test_data['stocks_fbo'] = stocks_fbo
            self.test_data['stocks_fbs'] = stocks_fbs
            self.test_data['orders'] = orders
            
            total_records = fbo_count + fbs_count + orders_count
            
            self.results['api_loading'] = {
                "passed": total_records > 0,
                "duration": time.time() - test_start,
                "fbo_count": fbo_count,
                "fbs_count": fbs_count,
                "orders_count": orders_count,
                "total_records": total_records
            }
            
            if total_records > 0:
                print(f"✅ Загружено {total_records} записей из всех API")
            else:
                print("❌ Не удалось загрузить данные из API")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки данных из API: {e}")
            self.results['api_loading'] = {
                "passed": False,
                "duration": time.time() - test_start,
                "error": str(e)
            }
    
    async def test_data_processing(self):
        """Тест 3: Обработка и валидация данных"""
        print("\n🔍 ТЕСТ 3: Обработка и валидация данных")
        print("-"*80)
        
        test_start = time.time()
        
        try:
            # Проверяем структуру данных
            checks = {}
            
            # FBO данные
            if 'stocks_fbo' in self.test_data and self.test_data['stocks_fbo']:
                fbo_sample = self.test_data['stocks_fbo'][0]
                fbo_fields = ['nmId', 'warehouseName', 'quantity']
                checks['FBO структура'] = all(field in fbo_sample for field in fbo_fields)
                print(f"✅ FBO данные имеют корректную структуру")
            else:
                checks['FBO структура'] = False
                print(f"⚠️  Нет FBO данных для проверки")
            
            # FBS данные
            if 'stocks_fbs' in self.test_data and self.test_data['stocks_fbs']:
                fbs_sample = self.test_data['stocks_fbs'][0]
                fbs_fields = ['nmId', 'warehouseName', 'quantity']
                checks['FBS структура'] = all(field in fbs_sample for field in fbs_fields)
                print(f"✅ FBS данные имеют корректную структуру")
            else:
                checks['FBS структура'] = False
                print(f"⚠️  Нет FBS данных для проверки")
            
            # Orders данные
            if 'orders' in self.test_data and self.test_data['orders']:
                order_sample = self.test_data['orders'][0]
                order_fields = ['srid', 'nmId', 'warehouseName']
                checks['Orders структура'] = all(field in order_sample for field in order_fields)
                print(f"✅ Orders данные имеют корректную структуру")
                
                # Проверяем фильтрацию отменённых заказов
                cancelled_orders = [o for o in self.test_data['orders'] if o.get('isCancel', False)]
                checks['Отменённые заказы отфильтрованы'] = len(cancelled_orders) == 0
                if len(cancelled_orders) == 0:
                    print(f"✅ Отменённые заказы отфильтрованы")
                else:
                    print(f"⚠️  Найдены отменённые заказы: {len(cancelled_orders)}")
            else:
                checks['Orders структура'] = False
                print(f"⚠️  Нет Orders данных для проверки")
            
            all_passed = all(checks.values())
            
            self.results['data_processing'] = {
                "passed": all_passed,
                "duration": time.time() - test_start,
                "checks": checks
            }
            
            if all_passed:
                print("✅ Все данные обработаны корректно")
            else:
                print("❌ Обнаружены проблемы в обработке данных")
            
        except Exception as e:
            print(f"❌ Ошибка обработки данных: {e}")
            self.results['data_processing'] = {
                "passed": False,
                "duration": time.time() - test_start,
                "error": str(e)
            }
    
    async def test_sheets_synchronization(self):
        """Тест 4: Синхронизация с Google Sheets"""
        print("\n🔍 ТЕСТ 4: Синхронизация с Google Sheets")
        print("-"*80)
        
        test_start = time.time()
        
        try:
            from stock_tracker.services.product_service import ProductService
            from stock_tracker.utils.config import get_config
            from stock_tracker.core.models import SyncStatus
            
            config = get_config()
            product_service = ProductService(config)
            
            print("🔄 Выполняется синхронизация...")
            sync_session = await product_service.sync_from_dual_api_to_sheets(skip_existence_check=True)
            
            is_success = sync_session and sync_session.status == SyncStatus.COMPLETED
            
            if is_success:
                print(f"✅ Синхронизация завершена успешно")
                print(f"   Обработано: {sync_session.products_processed}/{sync_session.products_total}")
                print(f"   Ошибок: {sync_session.products_failed}")
                print(f"   Длительность: {sync_session.duration_seconds:.1f}s")
            else:
                print(f"❌ Синхронизация не удалась")
                if sync_session:
                    print(f"   Статус: {sync_session.status.value}")
                    if sync_session.last_error:
                        print(f"   Ошибка: {sync_session.last_error}")
            
            self.results['sheets_sync'] = {
                "passed": is_success,
                "duration": time.time() - test_start,
                "products_processed": sync_session.products_processed if sync_session else 0,
                "products_total": sync_session.products_total if sync_session else 0,
                "products_failed": sync_session.products_failed if sync_session else 0,
                "sync_duration": sync_session.duration_seconds if sync_session else 0
            }
            
            # Сохраняем результат для следующих тестов
            self.test_data['sync_session'] = sync_session
            
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
            self.results['sheets_sync'] = {
                "passed": False,
                "duration": time.time() - test_start,
                "error": str(e)
            }
    
    async def test_data_integrity(self):
        """Тест 5: Проверка целостности данных"""
        print("\n🔍 ТЕСТ 5: Проверка целостности данных")
        print("-"*80)
        
        test_start = time.time()
        
        try:
            from stock_tracker.database.sheets import GoogleSheetsClient
            from stock_tracker.utils.config import get_config
            
            config = get_config()
            
            # Подключаемся к таблице
            sheets_client = GoogleSheetsClient(config.google_sheets.service_account_key_path)
            spreadsheet = sheets_client.open_by_id(config.google_sheets.sheet_id)
            worksheet = spreadsheet.worksheet(config.google_sheets.sheet_name)
            
            # Читаем данные
            all_values = worksheet.get_all_values()
            
            if not all_values:
                print("❌ Таблица пустая")
                self.results['data_integrity'] = {
                    "passed": False,
                    "duration": time.time() - test_start,
                    "error": "Empty spreadsheet"
                }
                return
            
            # Проверяем заголовки
            headers = all_values[0] if all_values else []
            expected_headers = [
                'Артикул', 'Наименование', 'Размер', 'Баркод',
                'Остатки на складах', 'Оборот', 'Заказы'
            ]
            
            headers_valid = all(h in headers for h in expected_headers)
            
            if headers_valid:
                print(f"✅ Заголовки таблицы корректны")
            else:
                print(f"❌ Заголовки таблицы некорректны")
                missing = [h for h in expected_headers if h not in headers]
                print(f"   Отсутствуют: {missing}")
            
            # Проверяем данные
            data_rows = all_values[1:]  # Пропускаем заголовок
            row_count = len(data_rows)
            
            print(f"📊 Строк данных в таблице: {row_count}")
            
            # Проверяем наличие данных в критических колонках
            if row_count > 0:
                # Проверяем первую строку данных
                first_row = data_rows[0]
                artikul_col = headers.index('Артикул') if 'Артикул' in headers else -1
                warehouse_col = headers.index('Остатки на складах') if 'Остатки на складах' in headers else -1
                
                has_artikul = artikul_col >= 0 and len(first_row) > artikul_col and first_row[artikul_col]
                has_warehouse = warehouse_col >= 0 and len(first_row) > warehouse_col
                
                if has_artikul:
                    print(f"✅ Данные артикулов присутствуют")
                else:
                    print(f"❌ Данные артикулов отсутствуют")
                
                if has_warehouse:
                    print(f"✅ Данные остатков присутствуют")
                else:
                    print(f"❌ Данные остатков отсутствуют")
            
            checks = {
                "headers_valid": headers_valid,
                "has_data": row_count > 0,
                "row_count": row_count
            }
            
            all_passed = headers_valid and row_count > 0
            
            self.results['data_integrity'] = {
                "passed": all_passed,
                "duration": time.time() - test_start,
                "checks": checks,
                "row_count": row_count
            }
            
            if all_passed:
                print(f"✅ Целостность данных подтверждена")
            else:
                print(f"❌ Проблемы с целостностью данных")
            
        except Exception as e:
            print(f"❌ Ошибка проверки целостности: {e}")
            self.results['data_integrity'] = {
                "passed": False,
                "duration": time.time() - test_start,
                "error": str(e)
            }
    
    async def test_performance(self):
        """Тест 6: Проверка производительности"""
        print("\n🔍 ТЕСТ 6: Проверка производительности")
        print("-"*80)
        
        test_start = time.time()
        
        try:
            # Анализируем время выполнения предыдущих тестов
            durations = {
                name: result.get('duration', 0)
                for name, result in self.results.items()
            }
            
            total_duration = sum(durations.values())
            
            print(f"⏱️  Общее время выполнения: {total_duration:.2f}s")
            print(f"\nДетализация по тестам:")
            for name, duration in durations.items():
                percentage = (duration / total_duration * 100) if total_duration > 0 else 0
                print(f"   • {name}: {duration:.2f}s ({percentage:.1f}%)")
            
            # Проверяем производительность синхронизации
            if 'sheets_sync' in self.results:
                sync_result = self.results['sheets_sync']
                if sync_result.get('passed'):
                    sync_duration = sync_result.get('sync_duration', 0)
                    products_total = sync_result.get('products_total', 1)
                    time_per_product = sync_duration / products_total if products_total > 0 else 0
                    
                    print(f"\n📈 Производительность синхронизации:")
                    print(f"   • Время на продукт: {time_per_product:.3f}s")
                    print(f"   • Продуктов в секунду: {1/time_per_product:.2f}" if time_per_product > 0 else "   • N/A")
            
            # Оценка производительности
            performance_good = total_duration < 300  # Менее 5 минут
            
            self.results['performance'] = {
                "passed": performance_good,
                "duration": time.time() - test_start,
                "total_duration": total_duration,
                "durations": durations
            }
            
            if performance_good:
                print(f"\n✅ Производительность хорошая")
            else:
                print(f"\n⚠️  Производительность может быть улучшена")
            
        except Exception as e:
            print(f"❌ Ошибка проверки производительности: {e}")
            self.results['performance'] = {
                "passed": False,
                "duration": time.time() - test_start,
                "error": str(e)
            }
    
    def generate_report(self) -> Dict[str, Any]:
        """Сгенерировать финальный отчёт"""
        print("\n" + "="*80)
        print("📊 ИТОГОВЫЙ ОТЧЁТ")
        print("="*80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r.get('passed', False))
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"\nВсего тестов: {total_tests}")
        print(f"✅ Пройдено: {passed_tests}")
        print(f"❌ Провалено: {failed_tests}")
        print(f"📈 Процент успеха: {success_rate:.1f}%")
        print(f"⏱️  Общее время: {total_duration:.2f}s")
        
        print(f"\nДетализация:")
        for name, result in self.results.items():
            status = "✅" if result.get('passed') else "❌"
            duration = result.get('duration', 0)
            print(f"{status} {name}: {duration:.2f}s")
            if 'error' in result:
                print(f"   Ошибка: {result['error']}")
        
        print("="*80)
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": success_rate,
                "total_duration": total_duration,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat()
            },
            "results": self.results
        }


async def main():
    """Главная функция"""
    test = IntegrationTest()
    report = await test.run_all_tests()
    
    # Сохраняем отчёт
    import json
    report_file = Path(__file__).parent / "integration_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Отчёт сохранён: {report_file}")
    
    # Возвращаем код выхода
    if report['summary']['failed'] > 0:
        return 1
    else:
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
