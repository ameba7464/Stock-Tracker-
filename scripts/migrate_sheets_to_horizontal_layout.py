"""
Миграция существующих Google Sheets на новую горизонтальную структуру.

Скрипт:
1. Находит всех tenant'ов с настроенными Google Sheets
2. Читает текущие продукты из БД
3. Пересоздает листы с новой структурой
4. Сохраняет резервные копии старых листов (опционально)

Использование:
    python migrate_sheets_to_horizontal_layout.py [--dry-run] [--tenant-id TENANT_ID] [--backup]

Опции:
    --dry-run       Режим проверки без изменений
    --tenant-id     Мигрировать только указанного tenant'а
    --backup        Создать резервную копию старого листа перед миграцией
"""

import argparse
import logging
import sys
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

# Добавляем путь к проекту
sys.path.insert(0, ".")

from stock_tracker.database.connection import get_db_context
from stock_tracker.database.models import Tenant, Product
from stock_tracker.services.google_sheets_service import GoogleSheetsService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SheetsMigrationService:
    """Сервис для миграции Google Sheets на новую структуру."""
    
    def __init__(self, db: Session, dry_run: bool = False, backup: bool = False):
        """
        Инициализация.
        
        Args:
            db: Database session
            dry_run: Если True, не выполнять изменения
            backup: Если True, создавать резервные копии
        """
        self.db = db
        self.dry_run = dry_run
        self.backup = backup
        self.stats = {
            "total_tenants": 0,
            "migrated_tenants": 0,
            "failed_tenants": 0,
            "skipped_tenants": 0
        }
    
    def get_tenants_to_migrate(self, tenant_id: str = None) -> List[Tenant]:
        """
        Получить список tenant'ов для миграции.
        
        Args:
            tenant_id: ID конкретного tenant'а (опционально)
            
        Returns:
            Список Tenant объектов
        """
        query = self.db.query(Tenant).filter(
            Tenant.google_sheet_id.isnot(None),
            Tenant.google_service_account_encrypted.isnot(None)
        )
        
        if tenant_id:
            query = query.filter(Tenant.id == tenant_id)
        
        tenants = query.all()
        logger.info(f"Found {len(tenants)} tenant(s) with Google Sheets configured")
        return tenants
    
    def backup_sheet(self, tenant: Tenant, service: GoogleSheetsService) -> Dict[str, Any]:
        """
        Создать резервную копию листа.
        
        Args:
            tenant: Tenant object
            service: GoogleSheetsService instance
            
        Returns:
            Информация о резервной копии
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create backup for tenant {tenant.id}")
            return {"backed_up": False, "dry_run": True}
        
        try:
            # Получаем информацию о текущем листе
            sheet_info = service.get_sheet_info()
            
            # Копируем лист (через Google Sheets API)
            spreadsheet = service._get_spreadsheet()
            worksheet = spreadsheet.worksheet("Products")
            
            # Создаем копию листа с суффиксом _backup_YYYYMMDD
            backup_name = f"Products_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            worksheet.duplicate(new_sheet_name=backup_name)
            
            logger.info(f"✅ Created backup sheet '{backup_name}' for tenant {tenant.id}")
            
            return {
                "backed_up": True,
                "backup_sheet_name": backup_name,
                "sheet_url": sheet_info["sheet_url"]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create backup for tenant {tenant.id}: {e}")
            return {"backed_up": False, "error": str(e)}
    
    def migrate_tenant_sheet(self, tenant: Tenant) -> Dict[str, Any]:
        """
        Мигрировать Google Sheet для одного tenant'а.
        
        Args:
            tenant: Tenant object
            
        Returns:
            Результат миграции
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Migrating tenant: {tenant.name} (ID: {tenant.id})")
        logger.info(f"{'='*80}")
        
        try:
            # Создаем сервис
            service = GoogleSheetsService(tenant)
            
            # Резервная копия (если требуется)
            if self.backup:
                backup_result = self.backup_sheet(tenant, service)
                if not backup_result.get("backed_up") and not self.dry_run:
                    logger.warning(f"⚠️ Backup failed, continuing anyway...")
            
            # Получаем продукты tenant'а
            products = self.db.query(Product).filter(
                Product.tenant_id == tenant.id,
                Product.is_active == True
            ).all()
            
            logger.info(f"Found {len(products)} active products for tenant {tenant.id}")
            
            if len(products) == 0:
                logger.warning(f"⚠️ No products found for tenant {tenant.id}, skipping")
                return {
                    "success": False,
                    "skipped": True,
                    "reason": "No products found"
                }
            
            # Выполняем миграцию (или dry run)
            if self.dry_run:
                logger.info(f"[DRY RUN] Would migrate {len(products)} products to new structure")
                return {
                    "success": True,
                    "dry_run": True,
                    "products_count": len(products)
                }
            else:
                # Синхронизируем с новой структурой
                result = service.sync_products_to_sheet(products, self.db)
                
                logger.info(f"✅ Successfully migrated tenant {tenant.id}")
                logger.info(f"   - Products synced: {result['products_synced']}")
                logger.info(f"   - Warehouses: {result['warehouses_count']}")
                logger.info(f"   - Duration: {result['duration_seconds']}s")
                logger.info(f"   - Sheet URL: {result['sheet_url']}")
                
                return {
                    "success": True,
                    "migrated": True,
                    **result
                }
        
        except Exception as e:
            logger.error(f"❌ Failed to migrate tenant {tenant.id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def migrate_all(self, tenant_id: str = None) -> Dict[str, Any]:
        """
        Мигрировать все Google Sheets (или один по tenant_id).
        
        Args:
            tenant_id: ID конкретного tenant'а (опционально)
            
        Returns:
            Статистика миграции
        """
        logger.info("\n" + "="*80)
        logger.info("STARTING GOOGLE SHEETS MIGRATION TO HORIZONTAL LAYOUT")
        logger.info("="*80)
        
        if self.dry_run:
            logger.info("🔍 Running in DRY RUN mode - no changes will be made")
        
        if self.backup:
            logger.info("💾 Backup mode enabled - will create backup sheets")
        
        # Получаем tenant'ов
        tenants = self.get_tenants_to_migrate(tenant_id)
        self.stats["total_tenants"] = len(tenants)
        
        if len(tenants) == 0:
            logger.warning("⚠️ No tenants found to migrate")
            return self.stats
        
        # Мигрируем каждого tenant'а
        for idx, tenant in enumerate(tenants, 1):
            logger.info(f"\n📊 Progress: {idx}/{len(tenants)}")
            
            result = self.migrate_tenant_sheet(tenant)
            
            if result.get("success"):
                if result.get("skipped"):
                    self.stats["skipped_tenants"] += 1
                else:
                    self.stats["migrated_tenants"] += 1
            else:
                self.stats["failed_tenants"] += 1
        
        # Выводим итоговую статистику
        logger.info("\n" + "="*80)
        logger.info("MIGRATION COMPLETED")
        logger.info("="*80)
        logger.info(f"Total tenants: {self.stats['total_tenants']}")
        logger.info(f"✅ Migrated: {self.stats['migrated_tenants']}")
        logger.info(f"⏭️ Skipped: {self.stats['skipped_tenants']}")
        logger.info(f"❌ Failed: {self.stats['failed_tenants']}")
        
        return self.stats


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Migrate Google Sheets to new horizontal warehouse layout"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no changes will be made)"
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        help="Migrate only specific tenant by ID"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup sheets before migration"
    )
    
    args = parser.parse_args()
    
    # Получаем сессию БД
    with get_db_context() as db:
        # Создаем сервис миграции
        migration_service = SheetsMigrationService(
            db=db,
            dry_run=args.dry_run,
            backup=args.backup
        )
        
        # Запускаем миграцию
        stats = migration_service.migrate_all(tenant_id=args.tenant_id)
        
        # Возвращаем код выхода
        if stats["failed_tenants"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
