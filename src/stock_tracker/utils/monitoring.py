"""
Comprehensive monitoring and metrics collection for Wildberries Stock Tracker.

Provides advanced monitoring capabilities including:
- Performance metrics tracking
- API call monitoring
- Error rate tracking  
- System health monitoring
- Custom business metrics
- Alerting and notification support
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import psutil
import os

from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics that can be tracked."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricData:
    """Individual metric data point."""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None


@dataclass
class Alert:
    """Alert notification data."""
    alert_id: str
    level: AlertLevel
    message: str
    metric_name: str
    current_value: Union[int, float]
    threshold: Union[int, float]
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, monitor: 'MonitoringSystem', metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.monitor = monitor
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time
        
        # Add error tag if exception occurred
        if exc_type is not None:
            self.tags["error"] = str(exc_type.__name__)
            self.tags["success"] = "false"
        else:
            self.tags["success"] = "true"
        
        self.monitor.record_timer(self.metric_name, duration, self.tags)


class MonitoringSystem:
    """
    Comprehensive monitoring system for Stock Tracker application.
    
    Provides metrics collection, alerting, and health monitoring
    capabilities for all application components.
    """
    
    def __init__(self, retention_hours: int = 24):
        """
        Initialize monitoring system.
        
        Args:
            retention_hours: How long to keep metrics in memory
        """
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.alerts: List[Alert] = []
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.api_call_counts = defaultdict(int)
        self.api_call_durations = defaultdict(list)
        self.error_counts = defaultdict(int)
        
        # System metrics
        self.system_metrics = {}
        self.last_system_check = datetime.now()
        
        # Health status
        self.health_status = "healthy"
        self.health_details = {}
        
        # Background thread for metric cleanup
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_thread()
        
        logger.info("MonitoringSystem initialized")
    
    def record_metric(self, name: str, value: Union[int, float], metric_type: MetricType, tags: Optional[Dict[str, str]] = None):
        """
        Record a metric of any type.
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric (counter, gauge, histogram)
            tags: Additional tags for the metric
        """
        metric = MetricData(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
        self._check_alert_rules(metric)
    
    def record_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Record a counter metric.
        
        Args:
            name: Metric name
            value: Counter increment value
            tags: Additional tags for the metric
        """
        metric = MetricData(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
        self._check_alert_rules(metric)
    
    def record_gauge(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
        """
        Record a gauge metric.
        
        Args:
            name: Metric name
            value: Current gauge value
            tags: Additional tags for the metric
        """
        metric = MetricData(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
        self._check_alert_rules(metric)
    
    def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a timer metric.
        
        Args:
            name: Metric name
            duration: Duration in seconds
            tags: Additional tags for the metric
        """
        metric = MetricData(
            name=name,
            value=duration,
            metric_type=MetricType.TIMER,
            timestamp=datetime.now(),
            tags=tags or {},
            unit="seconds"
        )
        self.metrics[name].append(metric)
        self._check_alert_rules(metric)
    
    def timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> PerformanceTimer:
        """
        Create a performance timer context manager.
        
        Args:
            metric_name: Name of the metric to record
            tags: Additional tags for the metric
            
        Returns:
            PerformanceTimer context manager
        """
        return PerformanceTimer(self, metric_name, tags)
    
    def track_api_call(self, endpoint: str, method: str = "GET", success: bool = True, 
                      duration: Optional[float] = None, response_code: Optional[int] = None):
        """
        Track API call metrics.
        
        Args:
            endpoint: API endpoint name
            method: HTTP method
            success: Whether the call was successful
            duration: Call duration in seconds
            response_code: HTTP response code
        """
        tags = {
            "endpoint": endpoint,
            "method": method,
            "success": str(success).lower()
        }
        
        if response_code:
            tags["response_code"] = str(response_code)
        
        # Count API calls
        self.record_counter("api_calls_total", 1, tags)
        
        # Track duration if provided
        if duration is not None:
            self.record_timer("api_call_duration", duration, tags)
        
        # Track errors
        if not success:
            self.record_counter("api_errors_total", 1, tags)
    
    def track_business_metric(self, metric_name: str, value: Union[int, float], 
                            entity_type: Optional[str] = None, entity_id: Optional[str] = None):
        """
        Track business-specific metrics.
        
        Args:
            metric_name: Business metric name
            value: Metric value
            entity_type: Type of entity (product, warehouse, etc.)
            entity_id: Specific entity identifier
        """
        tags = {}
        if entity_type:
            tags["entity_type"] = entity_type
        if entity_id:
            tags["entity_id"] = entity_id
        
        self.record_gauge(f"business.{metric_name}", value, tags)
    
    def collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_gauge("system.cpu_percent", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_gauge("system.memory_percent", memory.percent)
            self.record_gauge("system.memory_available_mb", memory.available / (1024 * 1024))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.record_gauge("system.disk_percent", (disk.used / disk.total) * 100)
            self.record_gauge("system.disk_free_gb", disk.free / (1024 * 1024 * 1024))
            
            # Process info
            process = psutil.Process()
            self.record_gauge("process.memory_mb", process.memory_info().rss / (1024 * 1024))
            self.record_gauge("process.cpu_percent", process.cpu_percent())
            
            # Thread count
            self.record_gauge("process.thread_count", threading.active_count())
            
            self.last_system_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def add_alert_rule(self, metric_name: str, threshold: Union[int, float], 
                      condition: str = "greater_than", level: AlertLevel = AlertLevel.WARNING,
                      message_template: Optional[str] = None):
        """
        Add an alert rule for a metric.
        
        Args:
            metric_name: Metric to monitor
            threshold: Alert threshold value
            condition: Condition type ("greater_than", "less_than", "equals")
            level: Alert severity level
            message_template: Custom alert message template
        """
        self.alert_rules[metric_name] = {
            "threshold": threshold,
            "condition": condition,
            "level": level,
            "message_template": message_template or f"{metric_name} is {condition} {threshold}"
        }
        
        logger.info(f"Added alert rule for {metric_name}: {condition} {threshold}")
    
    def _check_alert_rules(self, metric: MetricData):
        """Check if metric triggers any alert rules."""
        rule = self.alert_rules.get(metric.name)
        if not rule:
            return
        
        threshold = rule["threshold"]
        condition = rule["condition"]
        level = rule["level"]
        
        triggered = False
        
        if condition == "greater_than" and metric.value > threshold:
            triggered = True
        elif condition == "less_than" and metric.value < threshold:
            triggered = True
        elif condition == "equals" and metric.value == threshold:
            triggered = True
        
        if triggered:
            alert = Alert(
                alert_id=f"{metric.name}_{int(time.time())}",
                level=level,
                message=rule["message_template"].format(
                    metric_name=metric.name,
                    value=metric.value,
                    threshold=threshold
                ),
                metric_name=metric.name,
                current_value=metric.value,
                threshold=threshold,
                timestamp=metric.timestamp
            )
            
            self.alerts.append(alert)
            logger.warning(f"Alert triggered: {alert.message}")
    
    def get_metric_summary(self, metric_name: str, 
                          time_window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get summary statistics for a metric.
        
        Args:
            metric_name: Metric to summarize
            time_window_minutes: Time window for analysis
            
        Returns:
            Metric summary statistics
        """
        if metric_name not in self.metrics:
            return {"error": f"Metric {metric_name} not found"}
        
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        recent_metrics = [
            m for m in self.metrics[metric_name]
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": f"No recent data for {metric_name}"}
        
        values = [m.value for m in recent_metrics]
        
        return {
            "metric_name": metric_name,
            "time_window_minutes": time_window_minutes,
            "data_points": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else None,
            "first_timestamp": recent_metrics[0].timestamp.isoformat(),
            "last_timestamp": recent_metrics[-1].timestamp.isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Health status summary
        """
        # Check system metrics age
        metrics_age = (datetime.now() - self.last_system_check).total_seconds()
        
        # Determine health status
        health_status = "healthy"
        health_details = {}
        
        # Check if system metrics are stale
        if metrics_age > 300:  # 5 minutes
            health_status = "degraded"
            health_details["stale_metrics"] = f"System metrics last updated {metrics_age:.0f}s ago"
        
        # Check for recent critical alerts
        recent_critical_alerts = [
            alert for alert in self.alerts
            if alert.level == AlertLevel.CRITICAL 
            and alert.timestamp > datetime.now() - timedelta(minutes=30)
            and not alert.resolved
        ]
        
        if recent_critical_alerts:
            health_status = "unhealthy"
            health_details["critical_alerts"] = len(recent_critical_alerts)
        
        # Check error rates
        error_summary = self.get_metric_summary("api_errors_total", 30)
        if not error_summary.get("error") and error_summary.get("latest", 0) > 5:
            if health_status == "healthy":
                health_status = "degraded"
            health_details["high_error_rate"] = error_summary["latest"]
        
        return {
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "details": health_details,
            "metrics_age_seconds": metrics_age,
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "total_metrics": sum(len(metrics) for metrics in self.metrics.values())
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data.
        
        Returns:
            Dashboard data including metrics, alerts, and health
        """
        # Collect fresh system metrics
        self.collect_system_metrics()
        
        # Key metrics summaries
        key_metrics = [
            "api_calls_total",
            "api_errors_total", 
            "api_call_duration",
            "system.cpu_percent",
            "system.memory_percent"
        ]
        
        metric_summaries = {}
        for metric in key_metrics:
            summary = self.get_metric_summary(metric, 60)
            if "error" not in summary:
                metric_summaries[metric] = summary
        
        # Recent alerts
        recent_alerts = [
            {
                "alert_id": alert.alert_id,
                "level": alert.level.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved
            }
            for alert in sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:10]
        ]
        
        return {
            "health": self.get_health_status(),
            "metrics": metric_summaries,
            "alerts": recent_alerts,
            "system_info": {
                "monitoring_since": (datetime.now() - timedelta(hours=self.retention_hours)).isoformat(),
                "total_metrics_tracked": len(self.metrics),
                "alert_rules": len(self.alert_rules)
            }
        }
    
    def _start_cleanup_thread(self):
        """Start background thread for metric cleanup."""
        def cleanup_worker():
            while not self._stop_cleanup.wait(3600):  # Run every hour
                self._cleanup_old_metrics()
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_old_metrics(self):
        """Remove old metrics beyond retention period."""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        for metric_name, metrics in self.metrics.items():
            # Remove old metrics
            while metrics and metrics[0].timestamp < cutoff_time:
                metrics.popleft()
        
        # Clean up old alerts
        self.alerts = [
            alert for alert in self.alerts
            if alert.timestamp > cutoff_time or not alert.resolved
        ]
        
        logger.debug("Completed metric cleanup")
    
    def shutdown(self):
        """Shutdown monitoring system."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        
        logger.info("MonitoringSystem shutdown completed")


# Global monitoring instance
_monitoring_system: Optional[MonitoringSystem] = None


def get_monitoring_system() -> MonitoringSystem:
    """Get global monitoring system instance."""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = MonitoringSystem()
        
        # Setup default alert rules
        setup_default_alerts(_monitoring_system)
    
    return _monitoring_system


def setup_default_alerts(monitor: MonitoringSystem):
    """Setup default alert rules for common metrics."""
    # System alerts
    monitor.add_alert_rule("system.cpu_percent", 80, "greater_than", AlertLevel.WARNING)
    monitor.add_alert_rule("system.cpu_percent", 95, "greater_than", AlertLevel.CRITICAL)
    monitor.add_alert_rule("system.memory_percent", 85, "greater_than", AlertLevel.WARNING)
    monitor.add_alert_rule("system.memory_percent", 95, "greater_than", AlertLevel.CRITICAL)
    
    # API alerts
    monitor.add_alert_rule("api_errors_total", 5, "greater_than", AlertLevel.WARNING)
    monitor.add_alert_rule("api_errors_total", 10, "greater_than", AlertLevel.ERROR)
    monitor.add_alert_rule("api_call_duration", 30, "greater_than", AlertLevel.WARNING)
    monitor.add_alert_rule("api_call_duration", 60, "greater_than", AlertLevel.CRITICAL)


if __name__ == "__main__":
    # Test monitoring system
    print("Testing MonitoringSystem...")
    
    monitor = get_monitoring_system()
    
    # Test metrics
    monitor.record_counter("test.counter", 5)
    monitor.record_gauge("test.gauge", 42.5)
    
    # Test timer
    with monitor.timer("test.operation"):
        time.sleep(0.1)
    
    # Test API tracking
    monitor.track_api_call("wildberries.orders", "GET", True, 1.5, 200)
    monitor.track_api_call("wildberries.warehouses", "POST", False, 5.0, 500)
    
    # Test business metrics
    monitor.track_business_metric("products_processed", 25, "product", "WB123")
    
    # Get dashboard data
    dashboard = monitor.get_dashboard_data()
    print(f"✅ Dashboard data: {len(dashboard['metrics'])} metrics tracked")
    
    # Test health check
    health = monitor.get_health_status()
    print(f"✅ Health status: {health['status']}")
    
    print("MonitoringSystem tests completed!")