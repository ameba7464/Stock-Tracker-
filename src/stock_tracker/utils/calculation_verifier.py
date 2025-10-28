"""
Verification utilities for validating calculation accuracy against WB data.

This module provides tools to verify that our calculations match the expected
results from Wildberries interface, helping to identify and fix discrepancies.
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import asyncio

from stock_tracker.utils.logger import get_logger
from stock_tracker.core.calculator import WildberriesCalculator

logger = get_logger(__name__)


class CalculationVerifier:
    """Verify calculation accuracy against expected WB results."""
    
    @staticmethod
    def verify_orders_accuracy(nm_id: int, 
                             our_calculation: Dict[str, Any],
                             expected_wb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify orders calculation accuracy against WB interface data.
        
        Args:
            nm_id: Product nmId being verified
            our_calculation: Our calculated results
            expected_wb_data: Expected results from WB interface
            
        Returns:
            Detailed verification report
        """
        verification = {
            "nm_id": nm_id,
            "timestamp": datetime.now().isoformat(),
            "total_orders": {
                "our_result": our_calculation.get("total_orders", 0),
                "wb_expected": expected_wb_data.get("total_orders", 0),
                "difference": 0,
                "match": False,
                "accuracy_percent": 0.0
            },
            "warehouse_orders": {},
            "overall_accuracy": 0.0,
            "issues_found": [],
            "recommendations": []
        }
        
        # Verify total orders
        our_total = our_calculation.get("total_orders", 0)
        wb_total = expected_wb_data.get("total_orders", 0)
        verification["total_orders"]["difference"] = abs(our_total - wb_total)
        verification["total_orders"]["match"] = our_total == wb_total
        
        if wb_total > 0:
            verification["total_orders"]["accuracy_percent"] = (
                min(our_total, wb_total) / max(our_total, wb_total) * 100
            )
        
        if not verification["total_orders"]["match"]:
            verification["issues_found"].append(
                f"Total orders mismatch: calculated {our_total}, expected {wb_total} "
                f"(difference: {verification['total_orders']['difference']})"
            )
            
            if our_total > wb_total:
                verification["recommendations"].append(
                    "Our calculation is higher - check for duplicate counting or incorrect filtering"
                )
            else:
                verification["recommendations"].append(
                    "Our calculation is lower - check for missing warehouse types or date filtering"
                )
        
        # Verify warehouse-level orders
        our_warehouses = our_calculation.get("warehouse_breakdown", {})
        wb_warehouses = expected_wb_data.get("warehouse_breakdown", {})
        
        all_warehouses = set(our_warehouses.keys()) | set(wb_warehouses.keys())
        
        for warehouse in all_warehouses:
            our_count = our_warehouses.get(warehouse, 0)
            wb_count = wb_warehouses.get(warehouse, 0)
            
            warehouse_accuracy = 0.0
            if max(our_count, wb_count) > 0:
                warehouse_accuracy = min(our_count, wb_count) / max(our_count, wb_count) * 100
            
            verification["warehouse_orders"][warehouse] = {
                "our_result": our_count,
                "wb_expected": wb_count,
                "difference": abs(our_count - wb_count),
                "match": our_count == wb_count,
                "accuracy_percent": warehouse_accuracy
            }
            
            if our_count != wb_count:
                verification["issues_found"].append(
                    f"Warehouse {warehouse}: calculated {our_count}, expected {wb_count} "
                    f"(difference: {abs(our_count - wb_count)})"
                )
        
        # Calculate overall accuracy
        total_matches = sum(1 for result in verification["warehouse_orders"].values() if result["match"])
        total_matches += 1 if verification["total_orders"]["match"] else 0
        total_checks = len(verification["warehouse_orders"]) + 1
        
        verification["overall_accuracy"] = (total_matches / total_checks) * 100 if total_checks > 0 else 0
        
        logger.info(f"Verification for nmId {nm_id}: {verification['overall_accuracy']:.1f}% accurate")
        
        return verification
    
    @staticmethod
    def create_verification_report(verifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create comprehensive verification report for multiple products.
        
        Args:
            verifications: List of verification results
            
        Returns:
            Comprehensive report with statistics and recommendations
        """
        if not verifications:
            return {"error": "No verifications provided"}
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "products_verified": len(verifications),
            "overall_accuracy": 0.0,
            "accuracy_by_product": {},
            "common_issues": {},
            "accuracy_distribution": {"perfect": 0, "good": 0, "fair": 0, "poor": 0},
            "recommendations": [],
            "summary_statistics": {
                "total_orders_our": 0,
                "total_orders_wb": 0,
                "total_difference": 0
            }
        }
        
        total_accuracy = 0
        issue_counts = {}
        total_our = 0
        total_wb = 0
        
        for verification in verifications:
            nm_id = verification["nm_id"]
            accuracy = verification["overall_accuracy"]
            
            report["accuracy_by_product"][nm_id] = accuracy
            total_accuracy += accuracy
            
            # Accumulate totals
            total_our += verification["total_orders"]["our_result"]
            total_wb += verification["total_orders"]["wb_expected"]
            
            # Categorize accuracy
            if accuracy == 100:
                report["accuracy_distribution"]["perfect"] += 1
            elif accuracy >= 90:
                report["accuracy_distribution"]["good"] += 1
            elif accuracy >= 70:
                report["accuracy_distribution"]["fair"] += 1
            else:
                report["accuracy_distribution"]["poor"] += 1
            
            # Count issue types
            for issue in verification["issues_found"]:
                issue_type = issue.split(":")[0].strip()
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        report["overall_accuracy"] = total_accuracy / len(verifications)
        report["common_issues"] = {
            k: v for k, v in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        }
        
        # Summary statistics
        report["summary_statistics"] = {
            "total_orders_our": total_our,
            "total_orders_wb": total_wb,
            "total_difference": abs(total_our - total_wb),
            "overall_ratio": total_our / total_wb if total_wb > 0 else 0
        }
        
        # Generate recommendations
        if report["overall_accuracy"] < 90:
            report["recommendations"].append("Overall accuracy below 90% - investigate common issues")
        
        if report["accuracy_distribution"]["poor"] > 0:
            report["recommendations"].append(
                f"{report['accuracy_distribution']['poor']} products have poor accuracy (<70%) - priority fix needed"
            )
        
        most_common_issue = max(issue_counts.items(), key=lambda x: x[1]) if issue_counts else None
        if most_common_issue:
            report["recommendations"].append(
                f"Most common issue: {most_common_issue[0]} ({most_common_issue[1]} occurrences)"
            )
        
        return report
    
    @staticmethod
    def generate_test_cases(problematic_nm_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Generate test cases for known problematic products.
        
        Args:
            problematic_nm_ids: List of nmIds with known issues
            
        Returns:
            List of test case definitions
        """
        test_cases = []
        
        # Known problematic case from user report
        if 163383326 in problematic_nm_ids:
            test_cases.append({
                "nm_id": 163383326,
                "expected_wb_data": {
                    "total_orders": 98,  # According to user report
                    "warehouse_breakdown": {
                        "Котовск": 18  # According to user report
                    }
                },
                "test_description": "User reported discrepancy case",
                "priority": "high"
            })
        
        # Add generic test structure for other cases
        for nm_id in problematic_nm_ids:
            if nm_id != 163383326:  # Skip already added
                test_cases.append({
                    "nm_id": nm_id,
                    "expected_wb_data": {
                        "total_orders": None,  # To be filled manually
                        "warehouse_breakdown": {}
                    },
                    "test_description": f"Test case for nmId {nm_id}",
                    "priority": "medium"
                })
        
        return test_cases


class AccuracyMonitor:
    """Monitor calculation accuracy over time."""
    
    def __init__(self):
        self.verification_history = []
    
    def add_verification(self, verification: Dict[str, Any]) -> None:
        """Add verification result to history."""
        verification["recorded_at"] = datetime.now().isoformat()
        self.verification_history.append(verification)
    
    def get_accuracy_trend(self, days: int = 7) -> Dict[str, Any]:
        """Get accuracy trend over specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        recent_verifications = [
            v for v in self.verification_history 
            if datetime.fromisoformat(v["recorded_at"]) >= cutoff
        ]
        
        if not recent_verifications:
            return {"error": f"No verifications in last {days} days"}
        
        accuracies = [v["overall_accuracy"] for v in recent_verifications]
        
        return {
            "period_days": days,
            "verification_count": len(recent_verifications),
            "average_accuracy": sum(accuracies) / len(accuracies),
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
            "trend": "improving" if accuracies[-1] > accuracies[0] else "declining"
        }