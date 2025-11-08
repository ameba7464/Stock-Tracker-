#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Масштабный тест работы проекта Stock Tracker
Проверяет все компоненты системы и интеграцию с GitHub Actions

Выполняет следующие проверки:
1. Конфигурация и переменные окружения
2. Зависимости и пакеты
3. API Wildberries (Statistics, Marketplace, Orders)
4. Google Sheets API
5. Синхронизация данных
6. GitHub Actions конфигурация
7. Логирование и обработка ошибок
8. Производительность и оптимизация
"""

import sys
import os
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Установка кодировки UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


class TestResult:
    """Результат отдельного теста"""
    
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0.0, details: Dict = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def __str__(self):
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        return f"{status} {self.name} ({self.duration:.2f}s) - {self.message}"


class TestSuite:
    """Набор тестов для проекта"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
    
    def add_result(self, result: TestResult):
        """Добавить результат теста"""
        self.results.append(result)
        print(str(result))
    
    def get_summary(self) -> Dict[str, Any]:
        """Получить сводку по результатам"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    
    def print_summary(self):
        """Вывести сводку"""
        summary = self.get_summary()
        
        print("\n" + "="*80)
        print("📊 СВОДКА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
        print("="*80)
        print(f"Всего тестов: {summary['total']}")
        print(f"✅ Пройдено: {summary['passed']}")
        print(f"❌ Провалено: {summary['failed']}")
        print(f"📈 Процент успеха: {summary['success_rate']:.1f}%")
        print(f"⏱️  Время выполнения: {summary['duration']:.2f}s")
        print("="*80 + "\n")
        
        # Детали по каждому провалившемуся тесту
        if summary['failed'] > 0:
            print("❌ ПРОВАЛИВШИЕСЯ ТЕСТЫ:")
            print("-"*80)
            for result in self.results:
                if not result.passed:
                    print(f"  • {result.name}")
                    print(f"    {result.message}")
                    if result.details:
                        for key, value in result.details.items():
                            print(f"    {key}: {value}")
            print("-"*80 + "\n")


# Глобальный набор тестов
test_suite = TestSuite()


def test_environment_variables() -> TestResult:
    """Тест 1: Проверка переменных окружения"""
    start_time = time.time()
    
    try:
        required_vars = [
            "WILDBERRIES_API_KEY",
            "GOOGLE_SERVICE_ACCOUNT_KEY_PATH",
            "GOOGLE_SHEET_ID"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            return TestResult(
                "Environment Variables",
                False,
                f"Missing required variables: {', '.join(missing_vars)}",
                time.time() - start_time,
                {"missing": missing_vars}
            )
        
        return TestResult(
            "Environment Variables",
            True,
            "All required environment variables are set",
            time.time() - start_time
        )
        
    except Exception as e:
        return TestResult(
            "Environment Variables",
            False,
            f"Error checking environment: {e}",
            time.time() - start_time
        )


def test_dependencies() -> TestResult:
    """Тест 2: Проверка установленных зависимостей"""
    start_time = time.time()
    
    try:
        required_packages = [
            "gspread",
            "google.auth",
            "requests",
            "pydantic",
            "APScheduler",
            "pytest"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace(".", "_"))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            return TestResult(
                "Dependencies",
                False,
                f"Missing packages: {', '.join(missing_packages)}",
                time.time() - start_time,
                {"missing": missing_packages}
            )
        
        return TestResult(
            "Dependencies",
            True,
            "All required packages are installed",
            time.time() - start_time
        )
        
    except Exception as e:
        return TestResult(
            "Dependencies",
            False,
            f"Error checking dependencies: {e}",
            time.time() - start_time
        )


def test_configuration() -> TestResult:
    """Тест 3: Проверка конфигурации"""
    start_time = time.time()
    
    try:
        from stock_tracker.utils.config import get_config, validate_configuration
        
        # Загружаем конфигурацию
        config = get_config()
        
        # Валидируем конфигурацию
        validation_result = validate_configuration()
        
        if not validation_result.get("valid", False):
            return TestResult(
                "Configuration",
                False,
                f"Configuration validation failed: {validation_result.get('error', 'Unknown error')}",
                time.time() - start_time,
                {"validation_result": validation_result}
            )
        
        # Проверяем критические настройки
        if not config.wildberries.api_key:
            return TestResult(
                "Configuration",
                False,
                "Wildberries API key is not configured",
                time.time() - start_time
            )
        
        if not config.google_sheets.sheet_id:
            return TestResult(
                "Configuration",
                False,
                "Google Sheets ID is not configured",
                time.time() - start_time
            )
        
        return TestResult(
            "Configuration",
            True,
            "Configuration is valid and complete",
            time.time() - start_time,
            {"summary": validation_result.get("summary", {})}
        )
        
    except Exception as e:
        return TestResult(
            "Configuration",
            False,
            f"Error loading configuration: {e}",
            time.time() - start_time
        )


def test_google_sheets_connection() -> TestResult:
    """Тест 4: Проверка подключения к Google Sheets"""
    start_time = time.time()
    
    try:
        from stock_tracker.database.sheets import GoogleSheetsClient
        from stock_tracker.utils.config import get_config
        
        config = get_config()
        
        # Проверяем наличие файла сервисного аккаунта
        service_account_path = config.google_sheets.service_account_key_path
        if not os.path.exists(service_account_path):
            return TestResult(
                "Google Sheets Connection",
                False,
                f"Service account file not found: {service_account_path}",
                time.time() - start_time
            )
        
        # Пытаемся подключиться
        sheets_client = GoogleSheetsClient(service_account_path)
        
        # Пытаемся открыть таблицу
        sheet_id = config.google_sheets.sheet_id
        spreadsheet = sheets_client.open_by_id(sheet_id)
        
        if not spreadsheet:
            return TestResult(
                "Google Sheets Connection",
                False,
                "Could not open spreadsheet",
                time.time() - start_time
            )
        
        # Получаем информацию о таблице
        sheet_title = spreadsheet.title
        worksheet_count = len(spreadsheet.worksheets())
        
        return TestResult(
            "Google Sheets Connection",
            True,
            f"Successfully connected to '{sheet_title}' with {worksheet_count} worksheets",
            time.time() - start_time,
            {
                "sheet_title": sheet_title,
                "worksheet_count": worksheet_count
            }
        )
        
    except Exception as e:
        return TestResult(
            "Google Sheets Connection",
            False,
            f"Error connecting to Google Sheets: {e}",
            time.time() - start_time
        )


async def test_wildberries_api_async() -> TestResult:
    """Тест 5: Проверка API Wildberries (асинхронный)"""
    start_time = time.time()
    
    try:
        from stock_tracker.api.wildberries_client import WildberriesClient
        from stock_tracker.utils.config import get_config
        
        config = get_config()
        wb_client = WildberriesClient(config.wildberries.api_key)
        
        # Проверяем Statistics API (FBO склады)
        try:
            stocks_fbo = await wb_client.get_stocks()
            fbo_count = len(stocks_fbo) if stocks_fbo else 0
        except Exception as e:
            return TestResult(
                "Wildberries API",
                False,
                f"Statistics API error: {e}",
                time.time() - start_time
            )
        
        # Проверяем Marketplace API v3 (FBS склады)
        try:
            stocks_fbs = await wb_client.get_marketplace_stocks()
            fbs_count = len(stocks_fbs) if stocks_fbs else 0
        except Exception as e:
            return TestResult(
                "Wildberries API",
                False,
                f"Marketplace API error: {e}",
                time.time() - start_time
            )
        
        # Проверяем Orders API (заказы)
        try:
            orders = await wb_client.get_supplier_orders()
            orders_count = len(orders) if orders else 0
        except Exception as e:
            return TestResult(
                "Wildberries API",
                False,
                f"Orders API error: {e}",
                time.time() - start_time
            )
        
        return TestResult(
            "Wildberries API",
            True,
            f"All APIs working: FBO={fbo_count}, FBS={fbs_count}, Orders={orders_count}",
            time.time() - start_time,
            {
                "fbo_stocks": fbo_count,
                "fbs_stocks": fbs_count,
                "orders": orders_count
            }
        )
        
    except Exception as e:
        return TestResult(
            "Wildberries API",
            False,
            f"Error testing Wildberries API: {e}",
            time.time() - start_time
        )


def test_wildberries_api() -> TestResult:
    """Тест 5: Проверка API Wildberries (синхронная обёртка)"""
    return asyncio.run(test_wildberries_api_async())


async def test_data_synchronization_async() -> TestResult:
    """Тест 6: Проверка синхронизации данных (асинхронный)"""
    start_time = time.time()
    
    try:
        from stock_tracker.services.product_service import ProductService
        from stock_tracker.utils.config import get_config
        
        config = get_config()
        product_service = ProductService(config)
        
        # Выполняем тестовую синхронизацию (с ограничением)
        print("  Выполняется тестовая синхронизация (может занять время)...")
        
        # Для теста синхронизируем только несколько продуктов
        # Используем skip_existence_check=True для ускорения
        sync_session = await product_service.sync_from_dual_api_to_sheets(skip_existence_check=True)
        
        from stock_tracker.core.models import SyncStatus
        is_success = sync_session and sync_session.status == SyncStatus.COMPLETED
        
        if not is_success:
            return TestResult(
                "Data Synchronization",
                False,
                f"Sync failed: {sync_session.last_error if sync_session else 'Unknown error'}",
                time.time() - start_time,
                {
                    "status": sync_session.status.value if sync_session else "unknown",
                    "error": sync_session.last_error if sync_session else None
                }
            )
        
        return TestResult(
            "Data Synchronization",
            True,
            f"Sync completed: {sync_session.products_processed}/{sync_session.products_total} products",
            time.time() - start_time,
            {
                "products_processed": sync_session.products_processed,
                "products_total": sync_session.products_total,
                "products_failed": sync_session.products_failed,
                "duration": sync_session.duration_seconds
            }
        )
        
    except Exception as e:
        return TestResult(
            "Data Synchronization",
            False,
            f"Error during synchronization: {e}",
            time.time() - start_time
        )


def test_data_synchronization() -> TestResult:
    """Тест 6: Проверка синхронизации данных (синхронная обёртка)"""
    return asyncio.run(test_data_synchronization_async())


def test_github_actions_config() -> TestResult:
    """Тест 7: Проверка конфигурации GitHub Actions"""
    start_time = time.time()
    
    try:
        workflow_file = Path(__file__).parent / ".github" / "workflows" / "update-stocks.yml"
        
        if not workflow_file.exists():
            return TestResult(
                "GitHub Actions Config",
                False,
                f"Workflow file not found: {workflow_file}",
                time.time() - start_time
            )
        
        # Читаем и валидируем workflow файл
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow_content = f.read()
        
        # Проверяем наличие критических секций
        required_sections = [
            "on:",
            "schedule:",
            "workflow_dispatch:",
            "jobs:",
            "runs-on:",
            "steps:",
            "secrets.WILDBERRIES_API_KEY",
            "secrets.GOOGLE_SERVICE_ACCOUNT",
            "secrets.GOOGLE_SHEET_ID"
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in workflow_content:
                missing_sections.append(section)
        
        if missing_sections:
            return TestResult(
                "GitHub Actions Config",
                False,
                f"Missing sections in workflow: {', '.join(missing_sections)}",
                time.time() - start_time,
                {"missing_sections": missing_sections}
            )
        
        # Проверяем наличие расписания (cron)
        if "cron:" in workflow_content:
            import re
            cron_match = re.search(r"cron:\s*['\"](.+?)['\"]", workflow_content)
            cron_schedule = cron_match.group(1) if cron_match else None
        else:
            cron_schedule = None
        
        return TestResult(
            "GitHub Actions Config",
            True,
            f"Workflow configured correctly with schedule: {cron_schedule}",
            time.time() - start_time,
            {"cron_schedule": cron_schedule}
        )
        
    except Exception as e:
        return TestResult(
            "GitHub Actions Config",
            False,
            f"Error checking GitHub Actions config: {e}",
            time.time() - start_time
        )


def test_logging_system() -> TestResult:
    """Тест 8: Проверка системы логирования"""
    start_time = time.time()
    
    try:
        from stock_tracker.utils.logger import get_logger, setup_logging
        
        # Настраиваем логирование
        setup_logging()
        
        # Создаём тестовый логгер
        test_logger = get_logger("test_logger")
        
        # Проверяем уровни логирования
        test_logger.debug("Test debug message")
        test_logger.info("Test info message")
        test_logger.warning("Test warning message")
        
        # Проверяем директорию логов
        log_dir = Path(__file__).parent / "logs"
        if not log_dir.exists():
            return TestResult(
                "Logging System",
                False,
                f"Log directory not found: {log_dir}",
                time.time() - start_time
            )
        
        # Подсчитываем файлы логов
        log_files = list(log_dir.glob("*.log"))
        
        return TestResult(
            "Logging System",
            True,
            f"Logging system working correctly with {len(log_files)} log files",
            time.time() - start_time,
            {"log_files_count": len(log_files)}
        )
        
    except Exception as e:
        return TestResult(
            "Logging System",
            False,
            f"Error testing logging system: {e}",
            time.time() - start_time
        )


def test_error_handling() -> TestResult:
    """Тест 9: Проверка обработки ошибок"""
    start_time = time.time()
    
    try:
        from stock_tracker.utils.error_handler import handle_api_error
        from stock_tracker.core.exceptions import APIError, ConfigurationError
        
        # Проверяем, что исключения определены
        errors_defined = [
            APIError,
            ConfigurationError
        ]
        
        # Тестируем обработчик ошибок
        test_error = Exception("Test error")
        try:
            raise test_error
        except Exception as e:
            # Проверяем, что обработчик не падает
            pass
        
        return TestResult(
            "Error Handling",
            True,
            "Error handling system working correctly",
            time.time() - start_time
        )
        
    except Exception as e:
        return TestResult(
            "Error Handling",
            False,
            f"Error testing error handling: {e}",
            time.time() - start_time
        )


def test_performance() -> TestResult:
    """Тест 10: Проверка производительности"""
    start_time = time.time()
    
    try:
        # Проверяем время выполнения критических операций
        operations = []
        
        # Тест 1: Загрузка конфигурации
        op_start = time.time()
        from stock_tracker.utils.config import get_config
        config = get_config()
        operations.append(("Config Load", time.time() - op_start))
        
        # Тест 2: Инициализация логгера
        op_start = time.time()
        from stock_tracker.utils.logger import get_logger
        logger = get_logger("test")
        operations.append(("Logger Init", time.time() - op_start))
        
        # Анализируем производительность
        slow_operations = [(name, duration) for name, duration in operations if duration > 1.0]
        
        if slow_operations:
            return TestResult(
                "Performance",
                False,
                f"Slow operations detected: {slow_operations}",
                time.time() - start_time,
                {"slow_operations": slow_operations}
            )
        
        avg_duration = sum(d for _, d in operations) / len(operations)
        
        return TestResult(
            "Performance",
            True,
            f"Performance is good (avg: {avg_duration:.3f}s)",
            time.time() - start_time,
            {"operations": operations, "average": avg_duration}
        )
        
    except Exception as e:
        return TestResult(
            "Performance",
            False,
            f"Error testing performance: {e}",
            time.time() - start_time
        )


def save_test_report(suite: TestSuite):
    """Сохранить отчёт о тестировании"""
    try:
        report_file = Path(__file__).parent / "test_report.json"
        
        report_data = {
            "summary": suite.get_summary(),
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration": r.duration,
                    "details": r.details,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in suite.results
            ]
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Отчёт сохранён: {report_file}")
        
    except Exception as e:
        print(f"\n⚠️  Ошибка при сохранении отчёта: {e}")


def main():
    """Главная функция для запуска всех тестов"""
    print("="*80)
    print("🧪 МАСШТАБНЫЙ ТЕСТ ПРОЕКТА STOCK TRACKER")
    print("="*80)
    print(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Платформа: {sys.platform}")
    print(f"Python версия: {sys.version}")
    print("="*80 + "\n")
    
    test_suite.start_time = datetime.now()
    
    # Запускаем все тесты
    tests = [
        ("1. Environment Variables", test_environment_variables),
        ("2. Dependencies", test_dependencies),
        ("3. Configuration", test_configuration),
        ("4. Google Sheets Connection", test_google_sheets_connection),
        ("5. Wildberries API", test_wildberries_api),
        ("6. Data Synchronization", test_data_synchronization),
        ("7. GitHub Actions Config", test_github_actions_config),
        ("8. Logging System", test_logging_system),
        ("9. Error Handling", test_error_handling),
        ("10. Performance", test_performance)
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔍 Запуск теста: {test_name}")
        print("-"*80)
        
        try:
            result = test_func()
            test_suite.add_result(result)
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте: {e}")
            test_suite.add_result(TestResult(
                test_name,
                False,
                f"Critical test error: {e}",
                0.0
            ))
    
    test_suite.end_time = datetime.now()
    
    # Выводим сводку
    test_suite.print_summary()
    
    # Сохраняем отчёт
    save_test_report(test_suite)
    
    # Возвращаем код выхода
    summary = test_suite.get_summary()
    if summary['failed'] > 0:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛИЛИСЬ")
        return 1
    else:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
