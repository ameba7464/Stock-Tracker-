"""
Integration patch for ProductService to use Dual API Stock Fetcher

This file contains the new sync_from_dual_api_to_sheets method that should replace
the old sync_from_api_to_sheets method once testing is complete.

Usage:
1. Test this new method thoroughly
2. Once validated, replace old sync_from_api_to_sheets with this implementation
3. Remove old warehouse_remains-based code
"""

import uuid
from datetime import datetime, timedelta
from collections import defaultdict
import logging

# Correct imports for Stock Tracker project
from stock_tracker.core.models import SyncSession, Product
from stock_tracker.utils.exceptions import SyncError
from stock_tracker.api.products import WildberriesProductDataFetcher

logger = logging.getLogger(__name__)
ORDER_LOOKBACK_DAYS = 7

async def sync_from_dual_api_to_sheets(self, skip_existence_check: bool = False) -> SyncSession:
    """
    Fetch fresh data from Wildberries using Dual API (FBO+FBS) and write to Google Sheets.
    
    This method combines:
    - Statistics API for FBO (Fulfillment by Operator) stocks
    - Marketplace API v3 for FBS (Fulfillment by Seller) stocks  
    - Supplier Orders API for active orders count
    
    Args:
        skip_existence_check: Skip existence checks when writing products.
                             Set to True when table was just cleared to avoid unnecessary API calls.
    
    Returns:
        SyncSession with results summary
        
    Raises:
        SyncError: If synchronization fails
    """
    sync_session = SyncSession(
        session_id=str(uuid.uuid4()),
        start_time=datetime.now()
    )
    
    try:
        logger.info("="*80)
        logger.info("🚀 Starting Dual API Synchronization (FBO+FBS)")
        logger.info("="*80)
        sync_session.start()
        
        # Step 1: Get combined FBO+FBS stocks using Dual API
        logger.info("\n📊 Step 1: Fetching stocks from Dual API (Statistics + Marketplace)...")
        
        stocks_by_article = self.dual_api_fetcher.get_combined_stocks_by_article()
        
        logger.info(f"✅ Retrieved stocks for {len(stocks_by_article)} articles")
        
        # Log summary
        summary = self.dual_api_fetcher.get_all_stocks_summary()
        logger.info(f"\n📈 Stocks Summary:")
        logger.info(f"   FBO (WB warehouses):    {summary['total_fbo']:>6} шт")
        logger.info(f"   FBS (Seller warehouses): {summary['total_fbs']:>6} шт")
        logger.info(f"   ─────────────────────────────────")
        logger.info(f"   TOTAL:                   {summary['total']:>6} шт")
        logger.info(f"   Articles:                {summary['articles_count']}")
        logger.info(f"   FBS warehouses:          {summary['fbs_warehouses_count']}")
        
        if not stocks_by_article:
            logger.info("⚠️ No products returned from Dual API")
            sync_session.complete()
            return sync_session
        # Step 2: Fetch orders from supplier/orders endpoint
        logger.info("\n📦 Step 2: Fetching orders from supplier/orders API...")
        
        # Import data fetcher
        from stock_tracker.api.products import WildberriesProductDataFetcher
        data_fetcher = WildberriesProductDataFetcher(self.wb_client)
        
        def get_week_start() -> str:
            """Get date 7 days ago for full week of data"""
            today = datetime.now()
            week_ago = today - timedelta(days=ORDER_LOOKBACK_DAYS)  # 7 days ago
            return week_ago.strftime("%Y-%m-%dT00:00:00")
        
        date_from = get_week_start()
        logger.info(f"   Date range: {date_from} to now (7 days)")
        
        orders_data_raw = await data_fetcher.fetch_supplier_orders(date_from, flag=0)
        logger.info(f"   Raw orders: {len(orders_data_raw)}")
        
        # Filter cancelled orders
        valid_orders = [
            order for order in orders_data_raw 
            if not order.get('isCancel', False)
        ]
        logger.info(f"   Active orders: {len(valid_orders)} (removed {len(orders_data_raw) - len(valid_orders)} cancelled)")
        
        # Deduplicate by srid
        unique_orders = {}
        for order in valid_orders:
            srid = order.get('srid')
            if srid and srid not in unique_orders:
                unique_orders[srid] = order
        
        orders_data = list(unique_orders.values())
        logger.info(f"   Unique orders: {len(orders_data)} (removed {len(valid_orders) - len(orders_data)} duplicates)")
        
        # Count orders by nmId
        orders_by_nm_id = defaultdict(int)
        for order in orders_data:
            nm_id = order.get('nmId')
            if nm_id:
                orders_by_nm_id[nm_id] += 1
        
        logger.info(f"   Products with orders: {len(orders_by_nm_id)}")
        
        # Step 3: Convert to Product models and write to Sheets
        logger.info("\n💾 Step 3: Writing products to Google Sheets...")
        
        sync_session.products_total = len(stocks_by_article)
        updated_count = 0
        error_count = 0
        
        for article, stock_data in stocks_by_article.items():
            try:
                nm_id = stock_data['nm_id']
                
                # Get orders count for this product
                orders_count = orders_by_nm_id.get(nm_id, 0)
                
                # Create Product model (use correct field names)
                product = Product(
                    seller_article=article,
                    wildberries_article=nm_id,
                    total_stock=stock_data['total_stock'],
                    total_orders=orders_count,
                    fbo_stock=stock_data['fbo_stock'],
                    fbs_stock=stock_data['fbs_stock'],
                    last_updated=datetime.now()
                )
                
                # Calculate turnover if we have stock and orders
                if product.total_stock > 0 and product.total_orders > 0:
                    product.turnover = round(product.total_orders / product.total_stock, 2)
                else:
                    product.turnover = 0.0
                
                # Write/update in Google Sheets
                success = self.operations.create_or_update_product(
                    self.config.google_sheets.sheet_id,
                    product,
                    skip_existence_check=skip_existence_check
                )
                
                if success:
                    updated_count += 1
                    sync_session.products_processed += 1
                    
                    # Log sample product
                    if updated_count <= 3:
                        logger.info(f"   ✅ {article}: FBO={product.fbo_stock}, FBS={product.fbs_stock}, "
                                  f"Total={product.total_stock}, Orders={product.total_orders}")
                else:
                    error_count += 1
                    sync_session.products_failed += 1
                    sync_session.add_error(f"Failed to write product {article}")
                    
            except Exception as e:
                error_count += 1
                sync_session.products_failed += 1
                sync_session.add_error(f"Error processing {article}: {e}")
                logger.warning(f"Failed to process {article}: {e}")
        
        # Complete session
        if error_count == 0:
            sync_session.complete()
        else:
            sync_session.fail(f"Some products failed: {error_count} errors")
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ Dual API Sync Completed:")
        logger.info(f"   Updated: {updated_count}")
        logger.info(f"   Errors:  {error_count}")
        logger.info(f"   Duration: {(datetime.now() - sync_session.start_time).total_seconds():.1f}s")
        logger.info("="*80)
        
        return sync_session
        
    except Exception as e:
        sync_session.fail(f"Dual API sync failed: {e}")
        logger.error(f"Dual API sync failed: {e}")
        raise SyncError(f"Dual API sync failed: {e}")
