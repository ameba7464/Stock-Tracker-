"""
Analytics Service for calculating business metrics and insights
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session

from stock_tracker.database.models import Product, SyncLog, Tenant

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for calculating product analytics and business metrics"""
    
    def __init__(self, tenant: Tenant, db_session: Session):
        """
        Initialize analytics service
        
        Args:
            tenant: Tenant instance
            db_session: Database session
        """
        self.tenant = tenant
        self.db = db_session
        logger.info(
            f"AnalyticsService initialized for tenant {tenant.id} ({tenant.name})"
        )
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get dashboard summary with key metrics
        
        Returns:
            Dictionary with dashboard metrics
        """
        logger.info(f"Generating dashboard summary for tenant {self.tenant.id}")
        
        # Total products
        total_products = self.db.query(func.count(Product.id)).filter(
            Product.tenant_id == self.tenant.id
        ).scalar() or 0
        
        # Total stock
        total_stock = self.db.query(func.sum(Product.total_stock)).filter(
            Product.tenant_id == self.tenant.id
        ).scalar() or 0
        
        # Total orders
        total_orders = self.db.query(func.sum(Product.total_orders)).filter(
            Product.tenant_id == self.tenant.id
        ).scalar() or 0
        
        # Low stock products (< 10 units)
        low_stock_count = self.db.query(func.count(Product.id)).filter(
            and_(
                Product.tenant_id == self.tenant.id,
                Product.total_stock < 10,
                Product.total_stock > 0
            )
        ).scalar() or 0
        
        # Out of stock products
        out_of_stock_count = self.db.query(func.count(Product.id)).filter(
            and_(
                Product.tenant_id == self.tenant.id,
                Product.total_stock == 0
            )
        ).scalar() or 0
        
        # Last sync info
        last_sync = self.db.query(SyncLog).filter(
            SyncLog.tenant_id == self.tenant.id
        ).order_by(desc(SyncLog.started_at)).first()
        
        last_sync_data = None
        if last_sync:
            last_sync_data = {
                "timestamp": last_sync.started_at.isoformat(),
                "status": last_sync.status,
                "products_synced": last_sync.products_synced,
                "duration_ms": last_sync.duration_ms
            }
        
        # Average stock per product
        avg_stock = float(total_stock / total_products) if total_products > 0 else 0.0
        
        summary = {
            "total_products": total_products,
            "total_stock": int(total_stock),
            "total_orders": int(total_orders),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "average_stock_per_product": round(avg_stock, 2),
            "last_sync": last_sync_data,
            "health_score": self._calculate_health_score(
                total_products, low_stock_count, out_of_stock_count
            )
        }
        
        logger.info(f"Dashboard summary generated: {total_products} products, {total_stock} total stock")
        return summary
    
    def get_low_stock_products(
        self,
        threshold: int = 10,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get products with low stock levels
        
        Args:
            threshold: Stock level threshold (default: 10)
            limit: Maximum number of results
            
        Returns:
            List of low stock products
        """
        logger.info(f"Fetching low stock products (threshold={threshold})")
        
        products = self.db.query(Product).filter(
            and_(
                Product.tenant_id == self.tenant.id,
                Product.total_stock < threshold,
                Product.total_stock >= 0
            )
        ).order_by(Product.total_stock.asc()).limit(limit).all()
        
        result = []
        for product in products:
            result.append({
                "id": str(product.id),
                "marketplace_article": product.marketplace_article,
                "seller_article": product.seller_article,
                "product_name": product.product_name,
                "total_stock": product.total_stock,
                "total_orders": product.total_orders,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            })
        
        logger.info(f"Found {len(result)} low stock products")
        return result
    
    def get_top_products_by_orders(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get top products by order count
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of top products
        """
        logger.info(f"Fetching top {limit} products by orders")
        
        products = self.db.query(Product).filter(
            Product.tenant_id == self.tenant.id
        ).order_by(desc(Product.total_orders)).limit(limit).all()
        
        result = []
        for product in products:
            result.append({
                "id": str(product.id),
                "marketplace_article": product.marketplace_article,
                "seller_article": product.seller_article,
                "product_name": product.product_name,
                "total_stock": product.total_stock,
                "total_orders": product.total_orders,
                "stock_to_orders_ratio": (
                    round(product.total_stock / product.total_orders, 2)
                    if product.total_orders > 0 else None
                )
            })
        
        return result
    
    def get_sync_history(
        self,
        days: int = 7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get sync history for the past N days
        
        Args:
            days: Number of days to look back
            limit: Maximum number of results
            
        Returns:
            List of sync logs
        """
        logger.info(f"Fetching sync history for past {days} days")
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        sync_logs = self.db.query(SyncLog).filter(
            and_(
                SyncLog.tenant_id == self.tenant.id,
                SyncLog.started_at >= since_date
            )
        ).order_by(desc(SyncLog.started_at)).limit(limit).all()
        
        result = []
        for log in sync_logs:
            result.append({
                "id": str(log.id),
                "started_at": log.started_at.isoformat(),
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "status": log.status,
                "products_synced": log.products_synced,
                "duration_ms": log.duration_ms,
                "message": log.message
            })
        
        logger.info(f"Found {len(result)} sync logs")
        return result
    
    def get_stock_distribution(self) -> Dict[str, int]:
        """
        Get stock distribution across different ranges
        
        Returns:
            Dictionary with stock range counts
        """
        logger.info("Calculating stock distribution")
        
        # Query all products
        products = self.db.query(Product.total_stock).filter(
            Product.tenant_id == self.tenant.id
        ).all()
        
        distribution = {
            "out_of_stock": 0,      # 0
            "critical": 0,           # 1-5
            "low": 0,                # 6-20
            "medium": 0,             # 21-50
            "good": 0,               # 51-100
            "excellent": 0           # 100+
        }
        
        for (stock,) in products:
            if stock == 0:
                distribution["out_of_stock"] += 1
            elif stock <= 5:
                distribution["critical"] += 1
            elif stock <= 20:
                distribution["low"] += 1
            elif stock <= 50:
                distribution["medium"] += 1
            elif stock <= 100:
                distribution["good"] += 1
            else:
                distribution["excellent"] += 1
        
        return distribution
    
    def get_warehouse_breakdown(self) -> List[Dict[str, Any]]:
        """
        Get stock breakdown by warehouse
        
        Returns:
            List of warehouse statistics
        """
        logger.info("Calculating warehouse breakdown")
        
        products = self.db.query(Product).filter(
            Product.tenant_id == self.tenant.id
        ).all()
        
        warehouse_stats: Dict[str, Dict[str, int]] = {}
        
        for product in products:
            if product.warehouse_data:
                for warehouse_name, data in product.warehouse_data.items():
                    if warehouse_name not in warehouse_stats:
                        warehouse_stats[warehouse_name] = {
                            "total_stock": 0,
                            "total_orders": 0,
                            "product_count": 0
                        }
                    
                    warehouse_stats[warehouse_name]["total_stock"] += data.get("stock", 0)
                    warehouse_stats[warehouse_name]["total_orders"] += data.get("orders", 0)
                    warehouse_stats[warehouse_name]["product_count"] += 1
        
        # Convert to list
        result = []
        for warehouse_name, stats in warehouse_stats.items():
            result.append({
                "warehouse_name": warehouse_name,
                "total_stock": stats["total_stock"],
                "total_orders": stats["total_orders"],
                "product_count": stats["product_count"]
            })
        
        # Sort by total stock
        result.sort(key=lambda x: x["total_stock"], reverse=True)
        
        return result
    
    def _calculate_health_score(
        self,
        total_products: int,
        low_stock_count: int,
        out_of_stock_count: int
    ) -> float:
        """
        Calculate inventory health score (0-100)
        
        Args:
            total_products: Total number of products
            low_stock_count: Number of low stock products
            out_of_stock_count: Number of out of stock products
            
        Returns:
            Health score as float
        """
        if total_products == 0:
            return 100.0
        
        # Calculate percentage of problematic products
        problematic_pct = (low_stock_count + out_of_stock_count) / total_products
        
        # Score: 100 - (problematic_percentage * 100)
        score = max(0.0, 100.0 - (problematic_pct * 100))
        
        return round(score, 1)
