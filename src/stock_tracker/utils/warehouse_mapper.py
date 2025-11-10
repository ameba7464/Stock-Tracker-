"""
Модуль для нормализации и сопоставления названий складов.

Решает проблему дублирования из-за разных названий одних и тех же складов
в разных источниках данных.
"""

import re
from typing import Dict, List, Optional, Tuple
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

# Справочник известных соответствий названий складов
# РАСШИРЕНО 26.10.2025: Добавлены все варианты Маркетплейс/FBS складов
WAREHOUSE_NAME_MAPPINGS = {
    # Формат: "каноническое_название": ["возможные_варианты"]
    # ИСПРАВЛЕНО 09.11.2025: Удалены неправильные маппинги "Подольск 3" → "Подольск" и "Чехов 1" → "Чехов"
    # Эти склады должны оставаться с номерами, так как являются отдельными складами
    
    "Новосемейкино": ["Самара (Новосемейкино)", "Самара Новосемейкино", "Новосемейкино"],
    "Чехов 1": ["Чехов 1", "Чехов-1", "Чехов (Филиал)"],  # Чехов 1 - отдельный склад, не путать с "Чехов"
    "Подольск 3": ["Подольск 3", "Подольск-3", "Подольск (Филиал)"],  # Подольск 3 - отдельный склад
    "Екатеринбург - Перспективный 12": ["Екатеринбург - Перспективный 12", "Екатеринбург Перспективный 12", "Екатеринбург-Перспективный 12"],
    "Домодедово": ["Домодедово", "Домодедово (Московская область)"],
    "Тула": ["Тула", "Тула (Филиал)"],
    "Белые Столбы": ["Белые Столбы", "Белые столбы"],
    "Электросталь": ["Электросталь", "Электросталь (МО)"],
    
    # КРИТИЧЕСКИ ВАЖНО: Все варианты складов Маркетплейс/FBS
    # РАСШИРЕНО 26.10.2025: Добавлены варианты с номерами, символами, латиницей
    # ДОПОЛНЕНО 30.10.2025: Добавлены "Обухово МП", "Обухово Маркетплейс" и другие региональные варианты
    "Маркетплейс": [
        # Основные варианты
        "Маркетплейс", "маркетплейс", "МАРКЕТПЛЕЙС",
        "Marketplace", "marketplace", "MARKETPLACE",
        
        # С номерами и символами
        "Маркетплейс-1", "Маркетплейс 1", "Маркетплейс1",
        "Marketplace-1", "Marketplace 1", "Marketplace1",
        
        # Сокращения
        "МП", "МП-1", "МП 1", "МП1",
        "MP", "MP-1", "MP 1", "MP1",
        "СП", "СП-1", "СП 1",  # Склад Продавца
        
        # НОВОЕ: Региональные варианты с "МП" в названии
        "Обухово МП", "Обухово Маркетплейс", "Обухово Marketplace",
        "Коледино МП", "Коледино Маркетплейс", "Коледино Marketplace",
        "Электросталь МП", "Электросталь Маркетплейс",
        "Подольск МП", "Подольск Маркетплейс",
        "Чехов МП", "Чехов Маркетплейс",
        
        # Полные названия
        "Склад продавца", "Склад Продавца", "СКЛАД ПРОДАВЦА",
        "Склад селлера", "Склад Селлера", "СКЛАД СЕЛЛЕРА",
        "Seller Warehouse", "Seller Storage",
        
        # FBS варианты
        "FBS", "FBS-1", "FBS 1", "FBS1",
        "FBS Warehouse", "FBS-Warehouse", "FBS Storage",
        "Fulllog FBS", "Fulllog", "FullLog FBS",  # НОВОЕ: API Marketplace v3 возвращает "Fulllog FBS"
        "Fulfillment by Seller", "Fulfillment By Seller",
        
        # С уточнениями в скобках
        "Маркетплейс (FBS)", "Marketplace (FBS)",
        "Склад продавца (FBS)", "Seller Warehouse (FBS)",
        
        # Вариации написания
        "Маркет плейс", "Маркет-плейс",
        "Market place", "Market-place"
    ]
}


class WarehouseNameMapper:
    """Класс для нормализации и сопоставления названий складов."""
    
    def __init__(self):
        self.mapping_cache = {}
        self.reverse_mapping = self._build_reverse_mapping()
    
    def _build_reverse_mapping(self) -> Dict[str, str]:
        """Построить обратный справочник: вариант -> канонический."""
        reverse = {}
        for canonical, variants in WAREHOUSE_NAME_MAPPINGS.items():
            for variant in variants:
                reverse[variant.lower()] = canonical
        return reverse
    
    def normalize_warehouse_name(self, warehouse_name: str) -> str:
        """
        Нормализовать название склада к каноническому виду.
        
        Args:
            warehouse_name: Исходное название склада
            
        Returns:
            Каноническое название склада
        """
        if not warehouse_name:
            return warehouse_name
            
        original = warehouse_name.strip()
        
        # Проверяем кэш
        if original in self.mapping_cache:
            return self.mapping_cache[original]
        
        # Прямое соответствие
        lower_name = original.lower()
        if lower_name in self.reverse_mapping:
            canonical = self.reverse_mapping[lower_name]
            self.mapping_cache[original] = canonical
            logger.debug(f"Direct mapping: '{original}' -> '{canonical}'")
            return canonical
        
        # Поиск частичного соответствия
        partial_match = self._find_partial_match(original)
        if partial_match:
            self.mapping_cache[original] = partial_match
            logger.debug(f"Partial mapping: '{original}' -> '{partial_match}'")
            return partial_match
        
        # Не найдено - возвращаем исходное
        self.mapping_cache[original] = original
        logger.debug(f"No mapping found for: '{original}'")
        return original
    
    def _find_partial_match(self, warehouse_name: str) -> Optional[str]:
        """
        Найти частичное соответствие по ключевым словам.
        
        ИСПРАВЛЕНО 09.11.2025:
        - Приоритет #1: полные названия складов (например "Подольск 3")
        - Приоритет #2: частичные совпадения без маркетплейс-маркеров
        - Приоритет #3: только явный "маркетплейс"
        
        Args:
            warehouse_name: Название склада для поиска
            
        Returns:
            Каноническое название если найдено, иначе None
        """
        lower_name = warehouse_name.lower()
        original = warehouse_name.strip()
        
        # ПРИОРИТЕТ #1: ПОЛНЫЕ СОВПАДЕНИЯ СКЛАДОВ
        # Сначала ищем точные совпадения с вариантами складов
        for canonical, variants in WAREHOUSE_NAME_MAPPINGS.items():
            # Пропускаем Маркетплейс на этом этапе
            if canonical == "Маркетплейс":
                continue
                
            for variant in variants:
                variant_lower = variant.lower()
                # Точное совпадение (без учета регистра)
                if lower_name == variant_lower:
                    logger.info(f"✅ EXACT MATCH: '{original}' -> '{canonical}'")
                    return canonical
                
                # Совпадение с префиксом/суффиксом
                if lower_name.startswith(variant_lower + " ") or lower_name.endswith(" " + variant_lower):
                    logger.info(f"✅ PREFIX/SUFFIX MATCH: '{original}' -> '{canonical}'")
                    return canonical
        
        # ПРИОРИТЕТ #2: МАРКЕТПЛЕЙС только с явными индикаторами
        # Проверяем ТОЛЬКО явные индикаторы Маркетплейс (без коротких "мп" и "сп")
        marketplace_keywords = [
            "маркетплейс", "marketplace", "маркет",
            "склад продавца", "склад селлера", "seller",
            "fbs", "fulfillment"
        ]
        
        # Если найден явный индикатор - возвращаем Маркетплейс
        if any(keyword in lower_name for keyword in marketplace_keywords):
            logger.info(f"✅ MARKETPLACE MATCH: '{original}' -> 'Маркетплейс'")
            return "Маркетплейс"
        
        # ПРИОРИТЕТ #3: ЧАСТИЧНОЕ СОВПАДЕНИЕ для обычных складов
        
        # Убираем распространенные префиксы и суффиксы
        cleaned_name = re.sub(r'\b(сц|склад|центр|филиал)\b', '', lower_name).strip()
        cleaned_name = re.sub(r'[()]', '', cleaned_name).strip()
        
        # Поиск по ключевым словам для обычных складов
        for canonical, variants in WAREHOUSE_NAME_MAPPINGS.items():
            # Пропускаем Маркетплейс - он уже проверен выше
            if canonical == "Маркетплейс":
                continue
            
            canonical_lower = canonical.lower()
            
            # Проверяем вхождение канонического названия
            if canonical_lower in lower_name or any(word in lower_name for word in canonical_lower.split()):
                return canonical
            
            # Проверяем вхождение вариантов
            for variant in variants:
                variant_lower = variant.lower()
                if variant_lower in lower_name:
                    return canonical
        
        return None
    
    def get_warehouse_group(self, warehouse_names: List[str]) -> Dict[str, List[str]]:
        """
        Сгруппировать названия складов по каноническим именам.
        
        Args:
            warehouse_names: Список названий складов
            
        Returns:
            Словарь группировки: канонический -> [варианты]
        """
        groups = {}
        
        for name in warehouse_names:
            canonical = self.normalize_warehouse_name(name)
            
            if canonical not in groups:
                groups[canonical] = []
            
            if name not in groups[canonical]:
                groups[canonical].append(name)
        
        return groups
    
    def validate_mapping_accuracy(self, wb_names: List[str], 
                                st_names: List[str]) -> Dict[str, any]:
        """
        Проверить точность сопоставления между WB и Stock Tracker названиями.
        
        Args:
            wb_names: Названия складов из WB
            st_names: Названия складов из Stock Tracker
            
        Returns:
            Отчет о точности сопоставления
        """
        # Нормализуем все названия
        wb_normalized = {name: self.normalize_warehouse_name(name) for name in wb_names}
        st_normalized = {name: self.normalize_warehouse_name(name) for name in st_names}
        
        # Находим пересечения
        wb_canonical = set(wb_normalized.values())
        st_canonical = set(st_normalized.values())
        
        matched = wb_canonical & st_canonical
        wb_only = wb_canonical - st_canonical
        st_only = st_canonical - wb_canonical
        
        total_warehouses = len(wb_canonical | st_canonical)
        accuracy_percent = (len(matched) / total_warehouses * 100) if total_warehouses > 0 else 100
        
        return {
            "total_wb_warehouses": len(wb_names),
            "total_st_warehouses": len(st_names),
            "unique_wb_canonical": len(wb_canonical),
            "unique_st_canonical": len(st_canonical),
            "matched_warehouses": list(matched),
            "wb_only_warehouses": list(wb_only),
            "st_only_warehouses": list(st_only),
            "accuracy_percent": round(accuracy_percent, 2),
            "mapping_details": {
                "wb_mappings": wb_normalized,
                "st_mappings": st_normalized
            }
        }


# Глобальный экземпляр для использования
warehouse_mapper = WarehouseNameMapper()


def normalize_warehouse_name(warehouse_name: str) -> str:
    """Удобная функция для нормализации названия склада."""
    return warehouse_mapper.normalize_warehouse_name(warehouse_name)


def validate_warehouse_mapping(wb_names: List[str], st_names: List[str]) -> Dict[str, any]:
    """Удобная функция для валидации сопоставления складов."""
    return warehouse_mapper.validate_mapping_accuracy(wb_names, st_names)


def get_warehouse_canonical_groups(warehouse_names: List[str]) -> Dict[str, List[str]]:
    """Удобная функция для группировки складов по каноническим именам."""
    return warehouse_mapper.get_warehouse_group(warehouse_names)


# Специальные функции для критических случаев
def is_marketplace_warehouse(warehouse_name: str) -> bool:
    """
    Проверить, является ли склад Маркетплейсом/FBS.
    
    УЛУЧШЕНО 26.10.2025:
    - Убраны пробелы из индикаторов для лучшего поиска
    - Добавлены дополнительные варианты детекции
    
    Args:
        warehouse_name: Название склада
        
    Returns:
        True если это склад Маркетплейс/FBS
    """
    if not warehouse_name:
        return False
    
    # Нормализуем название
    canonical = normalize_warehouse_name(warehouse_name)
    
    # Проверяем каноническое название
    if canonical.lower() == "маркетплейс":
        return True
    
    # УЛУЧШЕНО: Проверяем прямые индикаторы (БЕЗ пробелов для лучшего поиска)
    lower_name = warehouse_name.lower()
    marketplace_indicators = [
        "маркетплейс", "marketplace", "маркет",
        "склад продавца", "склад селлера", "seller",
        "fbs", "fulfillment",
        "мп", "mp", "сп"  # ИСПРАВЛЕНО: убрали пробелы (было "мп ")
    ]
    
    return any(indicator in lower_name for indicator in marketplace_indicators)


def normalize_for_comparison(warehouse_name: str) -> str:
    """
    Нормализовать название склада для точного сравнения.
    
    Убирает лишние символы, приводит к нижнему регистру,
    нормализует пробелы.
    
    Args:
        warehouse_name: Исходное название
        
    Returns:
        Нормализованное название для сравнения
    """
    if not warehouse_name:
        return ""
    
    # Убираем лишние символы и нормализуем
    normalized = re.sub(r'[^\w\s]', ' ', warehouse_name.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Убираем стандартные префиксы
    prefixes_to_remove = ['сц', 'склад', 'центр', 'филиал']
    words = normalized.split()
    words = [word for word in words if word not in prefixes_to_remove]
    
    return ' '.join(words)


if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Testing warehouse mapper...")
    
    # Тест нормализации
    test_names = [
        "Самара (Новосемейкино)",
        "Чехов 1", 
        "Маркетплейс",
        "Склад продавца",
        "Подольск 3"
    ]
    
    print("\n📝 Normalization test:")
    for name in test_names:
        normalized = normalize_warehouse_name(name)
        print(f"   '{name}' -> '{normalized}'")
    
    # Тест проверки Маркетплейс
    print("\n🏪 Marketplace detection test:")
    marketplace_test = [
        "Маркетплейс",
        "маркетплейс",
        "Marketplace", 
        "Склад продавца",
        "МП-1",
        "Чехов 1"  # Не должен быть Маркетплейс
    ]
    
    for name in marketplace_test:
        is_mp = is_marketplace_warehouse(name)
        status = "✅ MARKETPLACE" if is_mp else "❌ REGULAR"
        print(f"   {status}: '{name}'")
    
    # Тест валидации сопоставления
    print("\n🔍 Mapping validation test:")
    wb_names = ["Новосемейкино", "Чехов", "Маркетплейс"]
    st_names = ["Самара (Новосемейкино)", "Чехов 1", "Склад продавца"]
    
    validation = validate_warehouse_mapping(wb_names, st_names)
    print(f"   Accuracy: {validation['accuracy_percent']:.1f}%")
    print(f"   Matched: {validation['matched_warehouses']}")
    print(f"   WB only: {validation['wb_only_warehouses']}")
    print(f"   ST only: {validation['st_only_warehouses']}")
    
    print("\n✅ Warehouse mapper tests completed!")