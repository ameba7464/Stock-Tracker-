"""
Health check system for Stock Tracker application.

Provides comprehensive health monitoring for all system components including
API connectivity, database operations, configuration validation, and system
resources. Implements both individual checks and overall system health status.
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # Create a mock psutil module to avoid attribute errors
    class MockPsutil:
        @staticmethod
        def cpu_percent(interval=1):
            return 0.0
        
        @staticmethod
        def virtual_memory():
            class MockMemory:
                def __init__(self):
                    self.percent = 0.0
                    self.total = 0
                    self.available = 0
            return MockMemory()
        
        @staticmethod
        def disk_usage(path):
            class MockDisk:
                def __init__(self):
                    self.used = 0
                    self.total = 1
                    self.free = 1
            return MockDisk()
    
    psutil = MockPsutil()

from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config, validate_configuration
from stock_tracker.utils.exceptions import HealthCheckError
from stock_tracker.utils.monitoring import get_monitoring_system


logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms
        }


class HealthCheck:
    """Base class for health checks."""
    
    def __init__(self, name: str, timeout: float = 10.0):
        self.name = name
        self.timeout = timeout
    
    async def check(self) -> HealthCheckResult:
        """
        Perform health check.
        
        Returns:
            HealthCheckResult with check status
        """
        start_time = time.time()
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(self._perform_check(), timeout=self.timeout)
            duration = (time.time() - start_time) * 1000
            
            if result is None:
                result = HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Check completed successfully"
                )
            
            result.duration_ms = duration
            return result
            
        except asyncio.TimeoutError:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Health check timed out after {self.timeout}s",
                duration_ms=duration
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                details={"error": str(e), "type": type(e).__name__},
                duration_ms=duration
            )
    
    async def _perform_check(self) -> Optional[HealthCheckResult]:
        """
        Override this method to implement specific health check logic.
        
        Returns:
            HealthCheckResult or None (will create default success result)
        """
        raise NotImplementedError("Subclasses must implement _perform_check")


class ConfigurationHealthCheck(HealthCheck):
    """Health check for application configuration."""
    
    def __init__(self):
        super().__init__("configuration", timeout=5.0)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check configuration validity."""
        try:
            # Validate configuration
            validation_result = validate_configuration()
            
            if validation_result["valid"]:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Configuration is valid",
                    details=validation_result
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Configuration validation failed: {validation_result['error']}",
                    details=validation_result
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Configuration check failed: {e}",
                details={"error": str(e)}
            )


class WildberriesAPIHealthCheck(HealthCheck):
    """Health check for Wildberries API connectivity."""
    
    def __init__(self):
        super().__init__("wildberries_api", timeout=30.0)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check Wildberries API connectivity."""
        try:
            from stock_tracker.api.client import create_wildberries_client
            
            client = create_wildberries_client()
            
            # Test API connection (synchronous call, but wrapped in async)
            test_result = client.test_connection()
            
            if test_result["success"]:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Wildberries API is accessible",
                    details={
                        "base_url": test_result["base_url"],
                        "statistics_url": test_result["statistics_url"],
                        "has_api_key": test_result["has_api_key"],
                        "test_task_id": test_result.get("task_id")
                    }
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Wildberries API connection failed: {test_result['error']}",
                    details=test_result
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Wildberries API health check failed: {e}",
                details={"error": str(e)}
            )


class GoogleSheetsHealthCheck(HealthCheck):
    """Health check for Google Sheets API connectivity."""
    
    def __init__(self):
        super().__init__("google_sheets", timeout=15.0)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check Google Sheets API connectivity."""
        try:
            from stock_tracker.database.sheets import create_sheets_client
            
            # Test Google Sheets connection
            sheets_client = create_sheets_client()
            
            # Try to test connection (basic API call)
            test_result = await sheets_client.test_connection()
            
            if test_result["success"]:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Google Sheets API is accessible",
                    details={
                        "sheet_id": test_result.get("sheet_id"),
                        "sheet_title": test_result.get("sheet_title"),
                        "accessible": test_result.get("accessible", True)
                    }
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Google Sheets connection failed: {test_result['error']}",
                    details=test_result
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Google Sheets health check failed: {e}",
                details={"error": str(e)}
            )


class SystemResourcesHealthCheck(HealthCheck):
    """Health check for system resources (CPU, memory, disk)."""
    
    def __init__(self, cpu_threshold: float = 80.0, 
                 memory_threshold: float = 80.0,
                 disk_threshold: float = 90.0):
        super().__init__("system_resources", timeout=5.0)
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check system resource usage."""
        if not PSUTIL_AVAILABLE:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.WARNING,
                message="psutil not available - cannot check system resources",
                details={"psutil_available": False}
            )
        
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get disk usage for current directory
            disk = psutil.disk_usage('.')
            disk_percent = (disk.used / disk.total) * 100
            
            # Determine overall status
            status = HealthStatus.HEALTHY
            issues = []
            
            if cpu_percent > self.cpu_threshold:
                status = HealthStatus.WARNING if status == HealthStatus.HEALTHY else HealthStatus.CRITICAL
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > self.memory_threshold:
                status = HealthStatus.WARNING if status == HealthStatus.HEALTHY else HealthStatus.CRITICAL
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent > self.disk_threshold:
                status = HealthStatus.WARNING if status == HealthStatus.HEALTHY else HealthStatus.CRITICAL
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            details = {
                "psutil_available": True,
                "cpu_percent": cpu_percent,
                "cpu_threshold": self.cpu_threshold,
                "memory_percent": memory_percent,
                "memory_threshold": self.memory_threshold,
                "memory_total_gb": memory.total / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk_percent,
                "disk_threshold": self.disk_threshold,
                "disk_total_gb": disk.total / (1024**3),
                "disk_free_gb": disk.free / (1024**3)
            }
            
            if status == HealthStatus.HEALTHY:
                message = "System resources are within normal limits"
            else:
                message = f"System resource issues detected: {', '.join(issues)}"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"System resources check failed: {e}",
                details={"error": str(e), "psutil_available": PSUTIL_AVAILABLE}
            )


class FileSystemHealthCheck(HealthCheck):
    """Health check for required files and directories."""
    
    def __init__(self):
        super().__init__("filesystem", timeout=5.0)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check filesystem requirements."""
        try:
            config = get_config()
            issues = []
            
            # Check log directory
            log_dir = Path(config.app.log_dir)
            if not log_dir.exists():
                issues.append(f"Log directory not found: {log_dir}")
            elif not log_dir.is_dir():
                issues.append(f"Log path is not a directory: {log_dir}")
            elif not os.access(log_dir, os.W_OK):
                issues.append(f"Log directory not writable: {log_dir}")
            
            # Check Google service account key
            service_key_path = Path(config.google_sheets.service_account_key_path)
            if not service_key_path.exists():
                issues.append(f"Google service account key not found: {service_key_path}")
            elif not service_key_path.is_file():
                issues.append(f"Google service account key path is not a file: {service_key_path}")
            
            # Check if current directory is writable (for temp files)
            current_dir = Path('.')
            if not os.access(current_dir, os.W_OK):
                issues.append("Current directory is not writable")
            
            details = {
                "log_dir": str(log_dir),
                "log_dir_exists": log_dir.exists(),
                "service_key_path": str(service_key_path),
                "service_key_exists": service_key_path.exists(),
                "current_dir_writable": os.access(current_dir, os.W_OK)
            }
            
            if issues:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Filesystem issues detected: {', '.join(issues)}",
                    details=details
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="All required files and directories are accessible",
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Filesystem check failed: {e}",
                details={"error": str(e)}
            )


class HealthCheckManager:
    """Manages and orchestrates health checks for the entire system."""
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.monitoring = get_monitoring_system()
        
        # Register default health checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.checks = [
            ConfigurationHealthCheck(),
            WildberriesAPIHealthCheck(),
            GoogleSheetsHealthCheck(),
            SystemResourcesHealthCheck(),
            FileSystemHealthCheck()
        ]
    
    def add_check(self, check: HealthCheck):
        """Add a custom health check."""
        self.checks.append(check)
        logger.debug(f"Added health check: {check.name}")
    
    def remove_check(self, name: str) -> bool:
        """Remove health check by name."""
        for i, check in enumerate(self.checks):
            if check.name == name:
                del self.checks[i]
                logger.debug(f"Removed health check: {name}")
                return True
        return False
    
    async def run_check(self, name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check by name."""
        for check in self.checks:
            if check.name == name:
                logger.debug(f"Running health check: {name}")
                result = await check.check()
                
                # Record metrics
                self.monitoring.record_metric(
                    f"health_check.{name}.duration",
                    result.duration_ms,
                    {"status": result.status.value}
                )
                
                return result
        return None
    
    async def run_all_checks(self, parallel: bool = True) -> Dict[str, HealthCheckResult]:
        """
        Run all registered health checks.
        
        Args:
            parallel: Run checks in parallel if True, sequential if False
            
        Returns:
            Dict mapping check names to their results
        """
        logger.info(f"Running {len(self.checks)} health checks (parallel={parallel})")
        
        if parallel:
            # Run all checks in parallel
            tasks = [check.check() for check in self.checks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            health_results = {}
            for i, result in enumerate(results):
                check_name = self.checks[i].name
                
                if isinstance(result, Exception):
                    # Handle exceptions from parallel execution
                    health_results[check_name] = HealthCheckResult(
                        name=check_name,
                        status=HealthStatus.CRITICAL,
                        message=f"Health check failed with exception: {result}",
                        details={"error": str(result), "type": type(result).__name__}
                    )
                else:
                    health_results[check_name] = result
                
                # Record metrics
                self.monitoring.record_metric(
                    f"health_check.{check_name}.duration",
                    health_results[check_name].duration_ms,
                    {"status": health_results[check_name].status.value}
                )
        else:
            # Run checks sequentially
            health_results = {}
            for check in self.checks:
                result = await check.check()
                health_results[check.name] = result
                
                # Record metrics
                self.monitoring.record_metric(
                    f"health_check.{check.name}.duration",
                    result.duration_ms,
                    {"status": result.status.value}
                )
        
        logger.info(f"Completed {len(health_results)} health checks")
        return health_results
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.
        
        Returns:
            Dict with overall system health and individual check results
        """
        # Run all health checks
        check_results = await self.run_all_checks(parallel=True)
        
        # Calculate overall system health
        overall_status = HealthStatus.HEALTHY
        healthy_count = 0
        warning_count = 0
        critical_count = 0
        
        for result in check_results.values():
            if result.status == HealthStatus.HEALTHY:
                healthy_count += 1
            elif result.status == HealthStatus.WARNING:
                warning_count += 1
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.WARNING
            elif result.status == HealthStatus.CRITICAL:
                critical_count += 1
                overall_status = HealthStatus.CRITICAL
        
        # Determine overall message
        total_checks = len(check_results)
        if overall_status == HealthStatus.HEALTHY:
            overall_message = f"All {total_checks} health checks passed"
        elif overall_status == HealthStatus.WARNING:
            overall_message = f"{warning_count} warning(s), {critical_count} critical issue(s) out of {total_checks} checks"
        else:
            overall_message = f"{critical_count} critical issue(s) out of {total_checks} checks"
        
        return {
            "overall_status": overall_status.value,
            "overall_message": overall_message,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": total_checks,
                "healthy": healthy_count,
                "warning": warning_count,
                "critical": critical_count
            },
            "checks": {
                name: result.to_dict() 
                for name, result in check_results.items()
            }
        }


# Global health check manager instance
_health_manager: Optional[HealthCheckManager] = None


def get_health_manager() -> HealthCheckManager:
    """Get global health check manager instance."""
    global _health_manager
    
    if _health_manager is None:
        _health_manager = HealthCheckManager()
    
    return _health_manager


async def check_system_health() -> Dict[str, Any]:
    """
    Convenience function to get system health status.
    
    Returns:
        Dict with system health information
    """
    manager = get_health_manager()
    return await manager.get_system_health()


# Example usage and testing
if __name__ == "__main__":
    import os
    
    async def test_health_checks():
        """Test health check system."""
        
        print("🔍 Testing health check system...")
        
        # Create health manager
        manager = HealthCheckManager()
        
        # Run individual checks
        print("\n📋 Running individual health checks:")
        for check in manager.checks:
            result = await manager.run_check(check.name)
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.WARNING: "⚠️",
                HealthStatus.CRITICAL: "❌",
                HealthStatus.UNKNOWN: "❓"
            }[result.status]
            
            print(f"{status_emoji} {result.name}: {result.message} ({result.duration_ms:.1f}ms)")
            if result.details:
                print(f"   Details: {result.details}")
        
        # Get overall system health
        print("\n🏥 Overall system health:")
        system_health = await manager.get_system_health()
        
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "❌",
            "unknown": "❓"
        }[system_health["overall_status"]]
        
        print(f"{status_emoji} Status: {system_health['overall_status']}")
        print(f"📊 Message: {system_health['overall_message']}")
        print(f"📈 Summary: {system_health['summary']}")
        
        return system_health
    
    # Run test
    asyncio.run(test_health_checks())