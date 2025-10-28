"""
Warehouse Classifier Module.

Классифицирует склады Wildberries на типы FBO и FBS через анализ API заказов.

Использует поле warehouseType из API supplier/orders для построения
точного мапинга складов на типы:
- "Склад WB" → FBO (товары на складах Wildberries)
- "Склад продавца" → FBS/MP (товары на складах продавца/маркетплейс)

Этот подход обеспечивает 100% точность без необходимости вычислений
или угадывания типа склада по названию.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter

from stock_tracker.utils.logger import get_logger
from stock_tracker.api.client import WildberriesAPIClient


logger = get_logger(__name__)


class WarehouseType:
    """Константы для типов складов."""
    FBO = "FBO"  # Fulfillment by Ozon/WB - склады Wildberries
    FBS = "FBS"  # Fulfillment by Seller - склады продавца
    UNKNOWN = "Unknown"  # Неизвестный тип склада


class WarehouseClassifier:
    """
    Классифицирует склады Wildberries на типы FBO и FBS.
    
    Использует API заказов для получения точной информации о типах складов
    через поле warehouseType. Строит и кэширует мапинг складов для
    последующего использования при обработке остатков.
    """
    
    def __init__(self, wb_client: WildberriesAPIClient):
        """
        Инициализация классификатора складов.
        
        Args:
            wb_client: Клиент Wildberries API для получения данных
        """
        self.wb_client = wb_client
        self._warehouse_mapping: Dict[str, str] = {}
        self._mapping_updated_at: Optional[datetime] = None
        self._cache_ttl_hours = 24  # Обновлять мапинг раз в сутки
        
        logger.info("Initialized WarehouseClassifier")
    
    async def build_warehouse_mapping(self, days: int = 90, force_refresh: bool = False) -> Dict[str, str]:
        """
        Строит мапинг складов через анализ заказов.
        
        Запрашивает заказы за указанный период и извлекает информацию
        о типах складов из поля warehouseType. Результат кэшируется.
        
        Args:
            days: Количество дней для анализа заказов (по умолчанию 90)
            force_refresh: Принудительно обновить мапинг (игнорировать кэш)
            
        Returns:
            Словарь {warehouse_name: warehouse_type}
            Где warehouse_type это WarehouseType.FBO или WarehouseType.FBS
            
        Raises:
            WildberriesAPIError: Если запрос к API не удался
        """
        # Проверяем кэш
        if not force_refresh and self._is_cache_valid():
            logger.info(f"Using cached warehouse mapping ({len(self._warehouse_mapping)} warehouses)")
            return self._warehouse_mapping
        
        logger.info(f"Building warehouse mapping from orders (last {days} days)...")
        
        # Получаем заказы за указанный период
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        orders = await self.wb_client.get_supplier_orders(date_from=date_from, flag=0)
        
        logger.info(f"Retrieved {len(orders)} orders for warehouse classification")
        
        # Извлекаем информацию о складах
        warehouse_mapping = {}
        warehouse_stats = Counter()
        
        for order in orders:
            warehouse_name = order.get("warehouseName")
            warehouse_type_raw = order.get("warehouseType", "")
            
            if not warehouse_name:
                continue
            
            # Преобразуем в наши константы
            if warehouse_type_raw == "Склад WB":
                warehouse_type = WarehouseType.FBO
            elif warehouse_type_raw == "Склад продавца":
                warehouse_type = WarehouseType.FBS
            else:
                warehouse_type = WarehouseType.UNKNOWN
            
            # Добавляем в мапинг (если склад уже есть, оставляем существующий тип)
            if warehouse_name not in warehouse_mapping:
                warehouse_mapping[warehouse_name] = warehouse_type
            
            # Статистика для логирования
            warehouse_stats[f"{warehouse_name} ({warehouse_type})"] += 1
        
        # Сохраняем в кэш
        self._warehouse_mapping = warehouse_mapping
        self._mapping_updated_at = datetime.now()
        
        # Логируем результаты
        logger.info(f"Built warehouse mapping: {len(warehouse_mapping)} unique warehouses")
        
        # Подсчет по типам
        type_counts = Counter(warehouse_mapping.values())
        logger.info(f"  FBO warehouses: {type_counts[WarehouseType.FBO]}")
        logger.info(f"  FBS warehouses: {type_counts[WarehouseType.FBS]}")
        
        if type_counts[WarehouseType.UNKNOWN] > 0:
            logger.warning(f"  Unknown warehouses: {type_counts[WarehouseType.UNKNOWN]}")
        
        # Топ-10 складов
        logger.debug("Top 10 warehouses by order count:")
        for warehouse_info, count in warehouse_stats.most_common(10):
            logger.debug(f"  {warehouse_info}: {count} orders")
        
        return warehouse_mapping
    
    def _is_cache_valid(self) -> bool:
        """
        Проверяет валидность кэша мапинга складов.
        
        Returns:
            True если кэш актуален, False если нужно обновить
        """
        if not self._warehouse_mapping or not self._mapping_updated_at:
            return False
        
        age_hours = (datetime.now() - self._mapping_updated_at).total_seconds() / 3600
        return age_hours < self._cache_ttl_hours
    
    def classify_warehouse(self, warehouse_name: str) -> str:
        """
        Возвращает тип склада по его названию.
        
        Args:
            warehouse_name: Название склада из API
            
        Returns:
            Тип склада: WarehouseType.FBO, WarehouseType.FBS или WarehouseType.UNKNOWN
        """
        if not warehouse_name:
            return WarehouseType.UNKNOWN
        
        return self._warehouse_mapping.get(warehouse_name, WarehouseType.UNKNOWN)
    
    def calculate_stock_by_type(self, product: Dict) -> Dict[str, int]:
        """
        Вычисляет остатки FBO и FBS для продукта.
        
        Анализирует поле warehouses в данных продукта из warehouse_remains API
        и суммирует остатки по типам складов.
        
        Args:
            product: Запись продукта из API warehouse_remains с полем warehouses
            
        Returns:
            Словарь с ключами:
            - fbo_stock: остатки на складах FBO
            - fbs_stock: остатки на складах FBS
            - unknown_stock: остатки на складах с неизвестным типом
            - total_stock: общие остатки
            - warehouses_detail: детализация по складам
        """
        fbo_stock = 0
        fbs_stock = 0
        unknown_stock = 0
        warehouses_detail = []
        
        warehouses = product.get("warehouses", [])
        
        for warehouse in warehouses:
            warehouse_name = warehouse.get("warehouseName", "")
            quantity = warehouse.get("quantity", 0)
            
            if not warehouse_name or quantity == 0:
                continue
            
            # Классифицируем склад
            warehouse_type = self.classify_warehouse(warehouse_name)
            
            # Суммируем по типам
            if warehouse_type == WarehouseType.FBO:
                fbo_stock += quantity
            elif warehouse_type == WarehouseType.FBS:
                fbs_stock += quantity
            else:
                unknown_stock += quantity
                logger.debug(f"Unknown warehouse type for: {warehouse_name} (quantity: {quantity})")
            
            # Детализация
            warehouses_detail.append({
                "name": warehouse_name,
                "type": warehouse_type,
                "quantity": quantity
            })
        
        total_stock = fbo_stock + fbs_stock + unknown_stock
        
        return {
            "fbo_stock": fbo_stock,
            "fbs_stock": fbs_stock,
            "unknown_stock": unknown_stock,
            "total_stock": total_stock,
            "warehouses_detail": warehouses_detail
        }
    
    def get_mapping_stats(self) -> Dict:
        """
        Возвращает статистику по текущему мапингу складов.
        
        Returns:
            Словарь со статистикой
        """
        if not self._warehouse_mapping:
            return {
                "is_initialized": False,
                "total_warehouses": 0
            }
        
        type_counts = Counter(self._warehouse_mapping.values())
        
        return {
            "is_initialized": True,
            "total_warehouses": len(self._warehouse_mapping),
            "fbo_warehouses": type_counts[WarehouseType.FBO],
            "fbs_warehouses": type_counts[WarehouseType.FBS],
            "unknown_warehouses": type_counts[WarehouseType.UNKNOWN],
            "updated_at": self._mapping_updated_at.isoformat() if self._mapping_updated_at else None,
            "cache_valid": self._is_cache_valid()
        }
    
    def get_all_warehouses_by_type(self, warehouse_type: str) -> List[str]:
        """
        Возвращает список всех складов указанного типа.
        
        Args:
            warehouse_type: Тип склада (FBO, FBS или Unknown)
            
        Returns:
            Список названий складов
        """
        return [
            name for name, wh_type in self._warehouse_mapping.items()
            if wh_type == warehouse_type
        ]


async def create_warehouse_classifier(wb_client: WildberriesAPIClient,
                                      days: int = 90,
                                      auto_build: bool = True) -> WarehouseClassifier:
    """
    Factory function для создания и инициализации классификатора складов.
    
    Args:
        wb_client: Клиент Wildberries API
        days: Количество дней для анализа заказов
        auto_build: Автоматически построить мапинг при создании
        
    Returns:
        Инициализированный WarehouseClassifier
    """
    classifier = WarehouseClassifier(wb_client)
    
    if auto_build:
        await classifier.build_warehouse_mapping(days=days)
    
    return classifier


if __name__ == "__main__":
    # Тестовый запуск классификатора
    async def test_classifier():
        from stock_tracker.api.client import create_wildberries_client
        
        print("\n" + "="*80)
        print("TEST: Warehouse Classifier")
        print("="*80 + "\n")
        
        # Создаем клиент и классификатор
        client = create_wildberries_client()
        classifier = await create_warehouse_classifier(client, days=90)
        
        # Показываем статистику
        stats = classifier.get_mapping_stats()
        print(f"Warehouse Mapping Stats:")
        print(f"  Total warehouses: {stats['total_warehouses']}")
        print(f"  FBO warehouses: {stats['fbo_warehouses']}")
        print(f"  FBS warehouses: {stats['fbs_warehouses']}")
        print(f"  Unknown warehouses: {stats['unknown_warehouses']}")
        print(f"  Updated at: {stats['updated_at']}")
        print(f"  Cache valid: {stats['cache_valid']}")
        
        # Показываем FBS склады
        fbs_warehouses = classifier.get_all_warehouses_by_type(WarehouseType.FBS)
        print(f"\nFBS Warehouses ({len(fbs_warehouses)}):")
        for wh in sorted(fbs_warehouses):
            print(f"  • {wh}")
        
        # Тестовый продукт
        test_product = {
            "nmId": 163383326,
            "vendorCode": "Its1_2_3/50g",
            "warehouses": [
                {"warehouseName": "Подольск 3", "quantity": 100},
                {"warehouseName": "Обухово МП", "quantity": 200},
                {"warehouseName": "Коледино", "quantity": 50}
            ]
        }
        
        print(f"\nTest Product Classification:")
        print(f"  Article: {test_product['vendorCode']} (nmId: {test_product['nmId']})")
        
        result = classifier.calculate_stock_by_type(test_product)
        print(f"\n  Stock by type:")
        print(f"    FBO stock: {result['fbo_stock']}")
        print(f"    FBS stock: {result['fbs_stock']}")
        print(f"    Unknown stock: {result['unknown_stock']}")
        print(f"    Total stock: {result['total_stock']}")
        
        print(f"\n  Warehouse details:")
        for wh_detail in result['warehouses_detail']:
            print(f"    • {wh_detail['name']} ({wh_detail['type']}): {wh_detail['quantity']}")
        
        client.close()
        print("\n✅ Test completed")
    
    # Запускаем тест
    asyncio.run(test_classifier())
