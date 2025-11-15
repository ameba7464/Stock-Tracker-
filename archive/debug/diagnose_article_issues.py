#!/usr/bin/env python3
"""
Диагностика проблем с конкретными артикулами.

Использование:
python diagnose_article_issues.py --nm-id 163383326 --expected-total 98 --expected-warehouse "Котовск:18"
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.core.calculator import WildberriesCalculator
from stock_tracker.utils.calculation_verifier import CalculationVerifier
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


async def diagnose_article(nm_id: int, expected_total: int = None, 
                         expected_warehouses: Dict[str, int] = None) -> Dict[str, Any]:
    """
    Проводит полную диагностику артикула для выявления проблем.
    
    Args:
        nm_id: Номер артикула WB
        expected_total: Ожидаемое общее количество заказов
        expected_warehouses: Ожидаемые заказы по складам
        
    Returns:
        Результат диагностики
    """
    try:
        logger.info(f"🔍 Starting diagnosis for nmId: {nm_id}")
        
        # Initialize API client
        config = get_config()
        wb_client = WildberriesAPIClient(config)
        data_fetcher = WildberriesProductDataFetcher(wb_client)
        
        # Fetch raw data
        logger.info("📥 Fetching raw data from APIs...")
        
        # Get orders for last 30 days
        from datetime import datetime, timedelta
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
        
        orders_data = await data_fetcher.fetch_supplier_orders(date_from, flag=0)
        warehouse_data = await data_fetcher.fetch_complete_warehouse_remains()
        
        logger.info(f"📊 Raw data fetched:")
        logger.info(f"   Orders: {len(orders_data)} records")
        logger.info(f"   Warehouse: {len(warehouse_data)} records")
        
        # Filter for specific nmId
        logger.info(f"🎯 Filtering for nmId {nm_id}...")
        
        relevant_orders = [order for order in orders_data if order.get("nmId") == nm_id]
        relevant_warehouse = [item for item in warehouse_data if item.get("nmId") == nm_id]
        
        logger.info(f"📋 Filtered data:")
        logger.info(f"   Orders for nmId: {len(relevant_orders)}")
        logger.info(f"   Warehouse for nmId: {len(relevant_warehouse)}")
        
        # Analyze orders in detail
        logger.info("🔍 Analyzing orders in detail...")
        
        calculator = WildberriesCalculator()
        total_orders, debug_info = calculator.calculate_total_orders_with_debug(
            orders_data, nm_id
        )
        
        # Calculate warehouse orders
        warehouse_orders = {}
        for warehouse_name in debug_info["warehouse_breakdown"]:
            warehouse_orders[warehouse_name] = calculator.calculate_warehouse_orders(
                orders_data, nm_id, warehouse_name
            )
        
        # Validate calculation
        validation = calculator.validate_orders_calculation(nm_id, total_orders, warehouse_orders)
        
        # Perform verification if expected data provided
        verification = None
        if expected_total is not None or expected_warehouses:
            expected_data = {
                "total_orders": expected_total,
                "warehouse_breakdown": expected_warehouses or {}
            }
            
            our_calculation = {
                "total_orders": total_orders,
                "warehouse_breakdown": warehouse_orders
            }
            
            verification = CalculationVerifier.verify_orders_accuracy(
                nm_id, our_calculation, expected_data
            )
        
        # Compile diagnosis result
        diagnosis = {
            "nm_id": nm_id,
            "timestamp": datetime.now().isoformat(),
            "raw_data": {
                "orders_count": len(orders_data),
                "warehouse_count": len(warehouse_data),
                "relevant_orders": len(relevant_orders),
                "relevant_warehouse": len(relevant_warehouse)
            },
            "calculation_results": {
                "total_orders": total_orders,
                "warehouse_orders": warehouse_orders,
                "debug_info": debug_info,
                "validation": validation
            },
            "verification": verification,
            "issues_detected": [],
            "recommendations": []
        }
        
        # Detect issues
        if not validation["is_valid"]:
            diagnosis["issues_detected"].append(
                f"Validation failed: warehouse sum ({validation['warehouse_sum']}) != "
                f"total ({validation['calculated_total']})"
            )
        
        if verification and verification["overall_accuracy"] < 100:
            diagnosis["issues_detected"].append(
                f"Accuracy issue: {verification['overall_accuracy']:.1f}% accuracy vs expected WB data"
            )
        
        # Generate recommendations
        if len(diagnosis["issues_detected"]) > 0:
            diagnosis["recommendations"].append("Review calculation logic for accuracy")
        
        if debug_info["filtered_out"]:
            diagnosis["recommendations"].append(
                f"Review {len(debug_info['filtered_out'])} filtered out records"
            )
        
        logger.info(f"✅ Diagnosis completed for nmId {nm_id}")
        return diagnosis
        
    except Exception as e:
        logger.error(f"❌ Diagnosis failed for nmId {nm_id}: {e}")
        return {
            "nm_id": nm_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def print_diagnosis_report(diagnosis: Dict[str, Any]) -> None:
    """Выводит отчет диагностики в читаемом формате."""
    
    nm_id = diagnosis["nm_id"]
    print(f"\n{'='*60}")
    print(f"🔍 DIAGNOSIS REPORT FOR nmId: {nm_id}")
    print(f"{'='*60}")
    
    if "error" in diagnosis:
        print(f"❌ ERROR: {diagnosis['error']}")
        return
    
    # Raw data info
    raw = diagnosis["raw_data"]
    print(f"\n📊 RAW DATA:")
    print(f"   Total orders in API: {raw['orders_count']}")
    print(f"   Total warehouse records: {raw['warehouse_count']}")
    print(f"   Orders for this nmId: {raw['relevant_orders']}")
    print(f"   Warehouse records for this nmId: {raw['relevant_warehouse']}")
    
    # Calculation results
    calc = diagnosis["calculation_results"]
    print(f"\n🧮 CALCULATION RESULTS:")
    print(f"   Total orders calculated: {calc['total_orders']}")
    print(f"   Warehouses found: {len(calc['warehouse_orders'])}")
    
    print(f"\n🏭 WAREHOUSE BREAKDOWN:")
    for warehouse, orders in calc["warehouse_orders"].items():
        print(f"   📦 {warehouse}: {orders} orders")
    
    # Debug info
    debug = calc["debug_info"]
    print(f"\n🔍 DEBUG INFO:")
    print(f"   Records checked: {debug['total_records_checked']}")
    print(f"   Matching records: {len(debug['matching_records'])}")
    print(f"   Filtered out: {len(debug['filtered_out'])}")
    print(f"   WB warehouses orders: {debug['wb_warehouses']}")
    print(f"   MP warehouses orders: {debug['mp_warehouses']}")
    
    if debug['filtered_out']:
        print(f"\n⚠️ FILTERED OUT RECORDS:")
        for record in debug['filtered_out'][:5]:  # Show first 5
            print(f"   - {record['reason']}: {record['warehouse']} (type: {record['type']})")
        if len(debug['filtered_out']) > 5:
            print(f"   ... and {len(debug['filtered_out']) - 5} more")
    
    # Validation
    validation = calc["validation"]
    print(f"\n✅ VALIDATION:")
    print(f"   Valid: {'✅ YES' if validation['is_valid'] else '❌ NO'}")
    print(f"   Total: {validation['calculated_total']}")
    print(f"   Warehouse sum: {validation['warehouse_sum']}")
    if not validation['is_valid']:
        print(f"   ⚠️ Difference: {validation['difference']}")
    
    # Verification
    if diagnosis["verification"]:
        verif = diagnosis["verification"]
        print(f"\n🎯 VERIFICATION vs EXPECTED:")
        print(f"   Overall accuracy: {verif['overall_accuracy']:.1f}%")
        
        total_check = verif["total_orders"]
        print(f"   Total orders: {total_check['our_result']} vs {total_check['wb_expected']} expected")
        if not total_check['match']:
            print(f"   ❌ Difference: {total_check['difference']}")
        
        if verif["warehouse_orders"]:
            print(f"   Warehouse comparison:")
            for wh, data in verif["warehouse_orders"].items():
                status = "✅" if data['match'] else "❌"
                print(f"     {status} {wh}: {data['our_result']} vs {data['wb_expected']} expected")
    
    # Issues and recommendations
    if diagnosis["issues_detected"]:
        print(f"\n❌ ISSUES DETECTED:")
        for issue in diagnosis["issues_detected"]:
            print(f"   - {issue}")
    
    if diagnosis["recommendations"]:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in diagnosis["recommendations"]:
            print(f"   - {rec}")
    
    print(f"\n{'='*60}")


async def main():
    """Main entry point for diagnosis tool."""
    parser = argparse.ArgumentParser(description="Diagnose article calculation issues")
    parser.add_argument("--nm-id", type=int, required=True, help="WB article ID (nmId)")
    parser.add_argument("--expected-total", type=int, help="Expected total orders")
    parser.add_argument("--expected-warehouse", action="append", 
                       help="Expected warehouse orders (format: 'WarehouseName:count')")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Setup logging
    import os
    os.environ["LOG_LEVEL"] = args.log_level
    setup_logging()
    
    # Parse expected warehouse data
    expected_warehouses = {}
    if args.expected_warehouse:
        for wh_spec in args.expected_warehouse:
            try:
                name, count = wh_spec.split(":")
                expected_warehouses[name.strip()] = int(count.strip())
            except ValueError:
                print(f"⚠️ Invalid warehouse spec: {wh_spec} (use 'WarehouseName:count')")
    
    # Run diagnosis
    try:
        diagnosis = await diagnose_article(
            nm_id=args.nm_id,
            expected_total=args.expected_total,
            expected_warehouses=expected_warehouses if expected_warehouses else None
        )
        
        print_diagnosis_report(diagnosis)
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))