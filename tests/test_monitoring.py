"""
Performance Monitoring Tests
Tests for metrics collection and performance monitoring
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from app.services.monitoring.metrics import (
    MetricsCollector, PerformanceMonitor, ChartMetrics, PerformanceMetrics
)

class TestMetricsCollector:
    """Test Metrics Collector"""
    
    def setup_method(self):
        """Setup test method"""
        self.collector = MetricsCollector(max_metrics_history=100)
    
    def test_record_chart_generation_success(self):
        """Test recording successful chart generation"""
        metrics = ChartMetrics(
            request_id="test123",
            user_id=1,
            chart_type="column",
            data_rows_count=10,
            data_columns_count=2,
            processing_time=1.5,
            tokens_used=150,
            status="completed"
        )
        
        self.collector.record_chart_generation(metrics)
        
        assert self.collector.counters["total_requests"] == 1
        assert self.collector.counters["successful_requests"] == 1
        assert self.collector.counters["failed_requests"] == 0
        assert self.collector.counters["total_processing_time"] == 1.5
        assert self.collector.counters["total_tokens_used"] == 150
    
    def test_record_chart_generation_failure(self):
        """Test recording failed chart generation"""
        metrics = ChartMetrics(
            request_id="test123",
            user_id=1,
            chart_type="column",
            data_rows_count=10,
            data_columns_count=2,
            processing_time=0.8,
            tokens_used=50,
            status="failed",
            error_category="validation"
        )
        
        self.collector.record_chart_generation(metrics)
        
        assert self.collector.counters["total_requests"] == 1
        assert self.collector.counters["successful_requests"] == 0
        assert self.collector.counters["failed_requests"] == 1
        assert self.collector.error_metrics["validation"] == 1
    
    def test_chart_type_metrics_tracking(self):
        """Test chart type specific metrics"""
        # Record multiple column charts
        for i in range(3):
            metrics = ChartMetrics(
                request_id=f"test{i}",
                user_id=1,
                chart_type="column",
                data_rows_count=10,
                data_columns_count=2,
                processing_time=1.0 + i * 0.5,
                tokens_used=100 + i * 10,
                status="completed"
            )
            self.collector.record_chart_generation(metrics)
        
        # Record one pie chart
        metrics = ChartMetrics(
            request_id="pie1",
            user_id=1,
            chart_type="pie",
            data_rows_count=5,
            data_columns_count=2,
            processing_time=0.8,
            tokens_used=80,
            status="completed"
        )
        self.collector.record_chart_generation(metrics)
        
        chart_metrics = self.collector.get_chart_type_breakdown()
        
        assert chart_metrics["column"]["count"] == 3
        assert chart_metrics["column"]["success_rate"] == 1.0
        assert chart_metrics["pie"]["count"] == 1
        assert chart_metrics["pie"]["avg_processing_time"] == 0.8
    
    def test_get_performance_metrics(self):
        """Test performance metrics calculation"""
        # Record some test data
        processing_times = [1.0, 1.5, 2.0, 1.2, 1.8]
        for i, time in enumerate(processing_times):
            metrics = ChartMetrics(
                request_id=f"test{i}",
                user_id=1,
                chart_type="column",
                data_rows_count=10,
                data_columns_count=2,
                processing_time=time,
                tokens_used=100,
                status="completed" if i < 4 else "failed"
            )
            self.collector.record_chart_generation(metrics)
        
        perf_metrics = self.collector.get_performance_metrics(time_range_minutes=60)
        
        assert perf_metrics.total_requests == 5
        assert perf_metrics.successful_requests == 4
        assert perf_metrics.failed_requests == 1
        assert perf_metrics.error_rate == 0.2
        assert perf_metrics.average_processing_time == sum(processing_times) / len(processing_times)
        assert perf_metrics.total_tokens_used == 500
    
    def test_get_performance_metrics_empty(self):
        """Test performance metrics with no data"""
        perf_metrics = self.collector.get_performance_metrics(time_range_minutes=60)
        
        assert perf_metrics.total_requests == 0
        assert perf_metrics.successful_requests == 0
        assert perf_metrics.error_rate == 0
        assert perf_metrics.average_processing_time == 0
    
    def test_get_hourly_trends(self):
        """Test hourly trends calculation"""
        # Create metrics for different hours
        base_time = datetime.now()
        
        for hour_offset in range(3):
            timestamp = base_time - timedelta(hours=hour_offset)
            metrics = ChartMetrics(
                request_id=f"test{hour_offset}",
                user_id=1,
                chart_type="column",
                data_rows_count=10,
                data_columns_count=2,
                processing_time=1.0,
                tokens_used=100,
                status="completed",
                timestamp=timestamp
            )
            self.collector.record_chart_generation(metrics)
        
        trends = self.collector.get_hourly_trends(hours=24)
        
        assert len(trends) == 24
        # Should have data for current hour
        current_hour_key = base_time.strftime("%H:00")
        assert trends[current_hour_key]["requests"] >= 1
    
    def test_get_system_health_healthy(self):
        """Test system health assessment - healthy status"""
        # Record good performance metrics
        for i in range(10):
            metrics = ChartMetrics(
                request_id=f"test{i}",
                user_id=1,
                chart_type="column",
                data_rows_count=10,
                data_columns_count=2,
                processing_time=1.0,
                tokens_used=100,
                status="completed"
            )
            self.collector.record_chart_generation(metrics)
        
        health = self.collector.get_system_health()
        
        assert health["status"] == "healthy"
        assert len(health["issues"]) == 0
        assert "metrics" in health
        assert "timestamp" in health
    
    def test_get_system_health_warning(self):
        """Test system health assessment - warning status"""
        # Record some failed requests (high error rate)
        for i in range(10):
            status = "failed" if i < 3 else "completed"  # 30% error rate
            metrics = ChartMetrics(
                request_id=f"test{i}",
                user_id=1,
                chart_type="column",
                data_rows_count=10,
                data_columns_count=2,
                processing_time=35.0,  # High processing time
                tokens_used=100,
                status=status
            )
            self.collector.record_chart_generation(metrics)
        
        health = self.collector.get_system_health()
        
        assert health["status"] == "warning"
        assert len(health["issues"]) > 0
        assert any("error rate" in issue.lower() for issue in health["issues"])
        assert any("processing time" in issue.lower() for issue in health["issues"])
    
    def test_get_system_health_critical(self):
        """Test system health assessment - critical status"""
        # Record very poor performance
        for i in range(10):
            metrics = ChartMetrics(
                request_id=f"test{i}",
                user_id=1,
                chart_type="column",
                data_rows_count=10,
                data_columns_count=2,
                processing_time=70.0,  # Very high processing time
                tokens_used=100,
                status="failed"  # All failed
            )
            self.collector.record_chart_generation(metrics)
        
        health = self.collector.get_system_health()
        
        assert health["status"] == "critical"
    
    def test_cleanup_old_metrics(self):
        """Test cleanup of old metrics data"""
        # Add some hourly metrics
        old_key = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d-%H")
        recent_key = datetime.now().strftime("%Y-%m-%d-%H")
        
        self.collector.hourly_metrics[old_key] = {"requests": 5}
        self.collector.hourly_metrics[recent_key] = {"requests": 3}
        
        self.collector.cleanup_old_metrics(days_to_keep=7)
        
        assert old_key not in self.collector.hourly_metrics
        assert recent_key in self.collector.hourly_metrics

class TestPerformanceMonitor:
    """Test Performance Monitor"""
    
    def setup_method(self):
        """Setup test method"""
        self.monitor = PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        await self.monitor.start_monitoring()
        assert self.monitor.monitoring_enabled is True
        assert self.monitor.cleanup_task is not None
        
        await self.monitor.stop_monitoring()
        assert self.monitor.monitoring_enabled is False
    
    def test_record_chart_request(self):
        """Test recording chart request"""
        self.monitor.record_chart_request(
            request_id="test123",
            user_id=1,
            chart_type="column",
            data_rows_count=10,
            data_columns_count=2,
            processing_time=1.5,
            tokens_used=150,
            status="completed"
        )
        
        # Check that metrics were recorded
        metrics = self.monitor.metrics_collector.get_performance_metrics(60)
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
    
    def test_record_chart_request_disabled(self):
        """Test recording when monitoring is disabled"""
        self.monitor.monitoring_enabled = False
        
        self.monitor.record_chart_request(
            request_id="test123",
            user_id=1,
            chart_type="column",
            data_rows_count=10,
            data_columns_count=2,
            processing_time=1.5,
            tokens_used=150,
            status="completed"
        )
        
        # Should not record metrics when disabled
        metrics = self.monitor.metrics_collector.get_performance_metrics(60)
        assert metrics.total_requests == 0
    
    def test_get_metrics_summary(self):
        """Test getting metrics summary"""
        # Record some test data
        self.monitor.record_chart_request(
            request_id="test123",
            user_id=1,
            chart_type="column",
            data_rows_count=10,
            data_columns_count=2,
            processing_time=1.5,
            tokens_used=150,
            status="completed"
        )
        
        summary = self.monitor.get_metrics_summary(time_range_minutes=60)
        
        assert "performance" in summary
        assert "chart_types" in summary
        assert "errors" in summary
        assert "health" in summary
        assert summary["time_range_minutes"] == 60
        assert summary["performance"]["total_requests"] == 1
    
    def test_get_trends(self):
        """Test getting performance trends"""
        # Record some test data
        self.monitor.record_chart_request(
            request_id="test123",
            user_id=1,
            chart_type="column",
            data_rows_count=10,
            data_columns_count=2,
            processing_time=1.5,
            tokens_used=150,
            status="completed"
        )
        
        trends = self.monitor.get_trends(hours=24)
        
        assert len(trends) == 24
        # Should have data for current hour
        current_hour = datetime.now().strftime("%H:00")
        assert current_hour in trends

class TestChartMetrics:
    """Test ChartMetrics data structure"""
    
    def test_chart_metrics_creation(self):
        """Test chart metrics creation"""
        timestamp = datetime.now()
        metrics = ChartMetrics(
            request_id="test123",
            user_id=1,
            chart_type="column",
            data_rows_count=10,
            data_columns_count=2,
            processing_time=1.5,
            tokens_used=150,
            status="completed",
            error_category="validation",
            timestamp=timestamp
        )
        
        assert metrics.request_id == "test123"
        assert metrics.user_id == 1
        assert metrics.chart_type == "column"
        assert metrics.processing_time == 1.5
        assert metrics.timestamp == timestamp
    
    def test_chart_metrics_auto_timestamp(self):
        """Test automatic timestamp generation"""
        before = datetime.now()
        metrics = ChartMetrics(
            request_id="test123",
            user_id=1,
            chart_type="column",
            data_rows_count=10,
            data_columns_count=2,
            processing_time=1.5,
            tokens_used=150,
            status="completed"
        )
        after = datetime.now()
        
        assert before <= metrics.timestamp <= after

class TestPerformanceMetrics:
    """Test PerformanceMetrics data structure"""
    
    def test_performance_metrics_defaults(self):
        """Test performance metrics with default values"""
        metrics = PerformanceMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.error_rate == 0.0
        assert metrics.average_processing_time == 0.0
    
    def test_performance_metrics_custom_values(self):
        """Test performance metrics with custom values"""
        metrics = PerformanceMetrics(
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            average_processing_time=2.5,
            error_rate=0.05
        )
        
        assert metrics.total_requests == 100
        assert metrics.successful_requests == 95
        assert metrics.failed_requests == 5
        assert metrics.average_processing_time == 2.5
        assert metrics.error_rate == 0.05