"""
Performance Monitoring and Metrics Collection Service
Comprehensive metrics collection for chart generation API
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from threading import Lock
import asyncio
from loguru import logger

@dataclass
class ChartMetrics:
    """Chart generation metrics data structure"""
    request_id: str
    user_id: int
    chart_type: str
    data_rows_count: int
    data_columns_count: int
    processing_time: float
    tokens_used: int
    status: str
    error_category: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class PerformanceMetrics:
    """Performance metrics aggregation"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_processing_time: float = 0.0
    median_processing_time: float = 0.0
    p95_processing_time: float = 0.0
    p99_processing_time: float = 0.0
    total_tokens_used: int = 0
    average_tokens_per_request: float = 0.0
    requests_per_minute: float = 0.0
    error_rate: float = 0.0

class MetricsCollector:
    """Collects and aggregates performance metrics"""
    
    def __init__(self, max_metrics_history: int = 10000):
        self.max_metrics_history = max_metrics_history
        self.metrics_history: deque = deque(maxlen=max_metrics_history)
        self.lock = Lock()
        
        # Real-time counters
        self.counters = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_processing_time": 0.0,
            "total_tokens_used": 0,
        }
        
        # Chart type breakdown
        self.chart_type_metrics = defaultdict(lambda: {
            "count": 0,
            "avg_processing_time": 0.0,
            "success_rate": 0.0,
            "avg_tokens": 0.0
        })
        
        # Error tracking
        self.error_metrics = defaultdict(int)
        
        # Time-based metrics
        self.hourly_metrics = defaultdict(lambda: {
            "requests": 0,
            "processing_time": 0.0,
            "tokens": 0,
            "errors": 0
        })
        
    def record_chart_generation(self, metrics: ChartMetrics):
        """Record chart generation metrics"""
        with self.lock:
            # Add to history
            self.metrics_history.append(metrics)
            
            # Update counters
            self.counters["total_requests"] += 1
            self.counters["total_processing_time"] += metrics.processing_time
            self.counters["total_tokens_used"] += metrics.tokens_used
            
            if metrics.status == "completed":
                self.counters["successful_requests"] += 1
            else:
                self.counters["failed_requests"] += 1
                if metrics.error_category:
                    self.error_metrics[metrics.error_category] += 1
            
            # Update chart type metrics
            chart_type = metrics.chart_type
            chart_metrics = self.chart_type_metrics[chart_type]
            chart_metrics["count"] += 1
            
            # Calculate running averages
            total_count = chart_metrics["count"]
            chart_metrics["avg_processing_time"] = (
                (chart_metrics["avg_processing_time"] * (total_count - 1) + metrics.processing_time) / total_count
            )
            chart_metrics["avg_tokens"] = (
                (chart_metrics["avg_tokens"] * (total_count - 1) + metrics.tokens_used) / total_count
            )
            
            # Update success rate
            success_count = sum(1 for m in self.metrics_history if m.chart_type == chart_type and m.status == "completed")
            chart_metrics["success_rate"] = success_count / total_count
            
            # Update hourly metrics
            hour_key = metrics.timestamp.strftime("%Y-%m-%d-%H")
            hourly = self.hourly_metrics[hour_key]
            hourly["requests"] += 1
            hourly["processing_time"] += metrics.processing_time
            hourly["tokens"] += metrics.tokens_used
            if metrics.status != "completed":
                hourly["errors"] += 1
    
    def get_performance_metrics(self, time_range_minutes: int = 60) -> PerformanceMetrics:
        """Get aggregated performance metrics for the specified time range"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)
            recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
            
            if not recent_metrics:
                return PerformanceMetrics()
            
            total_requests = len(recent_metrics)
            successful_requests = sum(1 for m in recent_metrics if m.status == "completed")
            failed_requests = total_requests - successful_requests
            
            processing_times = [m.processing_time for m in recent_metrics]
            processing_times.sort()
            
            avg_processing_time = sum(processing_times) / len(processing_times)
            median_processing_time = processing_times[len(processing_times) // 2]
            p95_processing_time = processing_times[int(len(processing_times) * 0.95)]
            p99_processing_time = processing_times[int(len(processing_times) * 0.99)]
            
            total_tokens = sum(m.tokens_used for m in recent_metrics)
            avg_tokens = total_tokens / total_requests if total_requests > 0 else 0
            
            requests_per_minute = total_requests / time_range_minutes
            error_rate = failed_requests / total_requests if total_requests > 0 else 0
            
            return PerformanceMetrics(
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                average_processing_time=avg_processing_time,
                median_processing_time=median_processing_time,
                p95_processing_time=p95_processing_time,
                p99_processing_time=p99_processing_time,
                total_tokens_used=total_tokens,
                average_tokens_per_request=avg_tokens,
                requests_per_minute=requests_per_minute,
                error_rate=error_rate
            )
    
    def get_chart_type_breakdown(self) -> Dict[str, Any]:
        """Get performance breakdown by chart type"""
        with self.lock:
            return dict(self.chart_type_metrics)
    
    def get_error_breakdown(self) -> Dict[str, int]:
        """Get error breakdown by category"""
        with self.lock:
            return dict(self.error_metrics)
    
    def get_hourly_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get hourly trends for the specified number of hours"""
        with self.lock:
            trends = {}
            current_time = datetime.now()
            
            for i in range(hours):
                hour = current_time - timedelta(hours=i)
                hour_key = hour.strftime("%Y-%m-%d-%H")
                hourly_data = self.hourly_metrics.get(hour_key, {
                    "requests": 0,
                    "processing_time": 0.0,
                    "tokens": 0,
                    "errors": 0
                })
                
                trends[hour.strftime("%H:00")] = {
                    "requests": hourly_data["requests"],
                    "avg_processing_time": (
                        hourly_data["processing_time"] / hourly_data["requests"] 
                        if hourly_data["requests"] > 0 else 0
                    ),
                    "tokens": hourly_data["tokens"],
                    "error_rate": (
                        hourly_data["errors"] / hourly_data["requests"] 
                        if hourly_data["requests"] > 0 else 0
                    )
                }
            
            return trends
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health indicators"""
        with self.lock:
            recent_metrics = self.get_performance_metrics(time_range_minutes=10)
            
            # Determine health status
            health_status = "healthy"
            issues = []
            
            # Check error rate
            if recent_metrics.error_rate > 0.1:  # 10% error rate threshold
                health_status = "warning"
                issues.append(f"High error rate: {recent_metrics.error_rate:.1%}")
            
            # Check processing time
            if recent_metrics.average_processing_time > 30:  # 30 seconds threshold
                health_status = "warning"
                issues.append(f"High processing time: {recent_metrics.average_processing_time:.1f}s")
            
            # Check request rate
            if recent_metrics.requests_per_minute > 50:  # High load threshold
                health_status = "warning"
                issues.append(f"High request rate: {recent_metrics.requests_per_minute:.1f}/min")
            
            if recent_metrics.error_rate > 0.2 or recent_metrics.average_processing_time > 60:
                health_status = "critical"
            
            return {
                "status": health_status,
                "issues": issues,
                "metrics": asdict(recent_metrics),
                "timestamp": datetime.now().isoformat()
            }
    
    def cleanup_old_metrics(self, days_to_keep: int = 7):
        """Clean up old metrics data"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean hourly metrics
            keys_to_remove = []
            for key in self.hourly_metrics:
                try:
                    key_time = datetime.strptime(key, "%Y-%m-%d-%H")
                    if key_time < cutoff_time:
                        keys_to_remove.append(key)
                except ValueError:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.hourly_metrics[key]
            
            logger.info(f"Cleaned up {len(keys_to_remove)} old hourly metric entries")

class PerformanceMonitor:
    """Performance monitoring service for chart generation"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.monitoring_enabled = True
        self.cleanup_task = None
        
    async def start_monitoring(self):
        """Start the performance monitoring service"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop the performance monitoring service"""
        self.monitoring_enabled = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old metrics"""
        while self.monitoring_enabled:
            try:
                await asyncio.sleep(3600)  # Run every hour
                self.metrics_collector.cleanup_old_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    def record_chart_request(
        self,
        request_id: str,
        user_id: int,
        chart_type: str,
        data_rows_count: int,
        data_columns_count: int,
        processing_time: float,
        tokens_used: int,
        status: str,
        error_category: Optional[str] = None
    ):
        """Record a chart generation request"""
        if not self.monitoring_enabled:
            return
            
        metrics = ChartMetrics(
            request_id=request_id,
            user_id=user_id,
            chart_type=chart_type,
            data_rows_count=data_rows_count,
            data_columns_count=data_columns_count,
            processing_time=processing_time,
            tokens_used=tokens_used,
            status=status,
            error_category=error_category
        )
        
        self.metrics_collector.record_chart_generation(metrics)
    
    def get_metrics_summary(self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        performance_metrics = self.metrics_collector.get_performance_metrics(time_range_minutes)
        chart_type_breakdown = self.metrics_collector.get_chart_type_breakdown()
        error_breakdown = self.metrics_collector.get_error_breakdown()
        system_health = self.metrics_collector.get_system_health()
        
        return {
            "performance": asdict(performance_metrics),
            "chart_types": chart_type_breakdown,
            "errors": error_breakdown,
            "health": system_health,
            "time_range_minutes": time_range_minutes
        }
    
    def get_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trends"""
        return self.metrics_collector.get_hourly_trends(hours)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()