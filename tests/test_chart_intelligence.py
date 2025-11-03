"""
Chart Intelligence Service Tests
Comprehensive tests for chart intelligence and data analysis
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json

from app.models.api.chart import (
    ChartType, DataSource, ChartConfig, ChartPosition, 
    ChartStyling, SeriesConfig, DataPattern, ChartRecommendation
)
from app.services.chart.intelligence import ChartIntelligenceService

class TestChartIntelligenceService:
    """Test Chart Intelligence Service"""
    
    def setup_method(self):
        """Setup test method"""
        self.service = ChartIntelligenceService()
        
        self.sample_time_series_data = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B13",
            headers=["Date", "Value"],
            data_rows=[
                ["2023-01", 100],
                ["2023-02", 120],
                ["2023-03", 110],
                ["2023-04", 135],
                ["2023-05", 150],
                ["2023-06", 145],
                ["2023-07", 160],
                ["2023-08", 175],
                ["2023-09", 165],
                ["2023-10", 180],
                ["2023-11", 195],
                ["2023-12", 210]
            ]
        )
        
        self.sample_categorical_data = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B5",
            headers=["Category", "Count"],
            data_rows=[
                ["Product A", 25],
                ["Product B", 30],
                ["Product C", 20],
                ["Product D", 15]
            ]
        )
        
        self.sample_correlation_data = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:C6",
            headers=["Height", "Weight", "Age"],
            data_rows=[
                [170, 65, 25],
                [175, 70, 30],
                [180, 75, 28],
                [165, 60, 22],
                [185, 80, 35]
            ]
        )
        
        self.sample_distribution_data = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B21",
            headers=["Value", "Frequency"],
            data_rows=[[i, i*2] for i in range(1, 21)]
        )

    @pytest.mark.asyncio
    async def test_analyze_data_patterns_time_series(self):
        """Test time series data pattern analysis"""
        analysis = await self.service.analyze_data_patterns(self.sample_time_series_data)
        
        assert analysis["pattern_type"] == "time_series"
        assert "temporal_data" in analysis["data_characteristics"]
        assert analysis["data_quality_score"] > 0.8
        assert "statistical_insights" in analysis
        assert analysis["recommended_x_axis"] == 0
        assert analysis["recommended_y_axes"] == [1]

    @pytest.mark.asyncio
    async def test_analyze_data_patterns_categorical(self):
        """Test categorical data pattern analysis"""
        analysis = await self.service.analyze_data_patterns(self.sample_categorical_data)
        
        assert analysis["pattern_type"] == "categorical"
        assert "categorical_data" in analysis["data_characteristics"]
        assert analysis["complexity_score"] < 0.5  # Simple data
        assert len(analysis["optimization_suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_data_patterns_correlation(self):
        """Test correlation data pattern analysis"""
        analysis = await self.service.analyze_data_patterns(self.sample_correlation_data)
        
        assert analysis["pattern_type"] == "correlation"
        assert "numerical_correlation" in analysis["data_characteristics"]
        
        # Check statistical insights
        insights = analysis["statistical_insights"]
        assert len(insights["numerical_columns"]) >= 2
        assert len(insights["correlations"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_data_patterns_distribution(self):
        """Test distribution data pattern analysis"""
        analysis = await self.service.analyze_data_patterns(self.sample_distribution_data)
        
        assert analysis["pattern_type"] == "distribution"
        assert "statistical_distribution" in analysis["data_characteristics"]
        assert analysis["complexity_score"] > 0.3  # More complex data

    def test_is_time_series_data(self):
        """Test time series detection"""
        headers = ["Date", "Sales"]
        data_rows = [["2023-01-01", 100], ["2023-01-02", 120]]
        
        result = self.service._is_time_series_data(headers, data_rows)
        assert result is True
        
        # Test non-time series
        headers = ["Product", "Sales"]
        data_rows = [["Product A", 100], ["Product B", 120]]
        
        result = self.service._is_time_series_data(headers, data_rows)
        assert result is False

    def test_is_categorical_data(self):
        """Test categorical data detection"""
        data_rows = [["Product A", 100], ["Product B", 120], ["Product C", 90]]
        
        result = self.service._is_categorical_data(data_rows)
        assert result is True
        
        # Test non-categorical (all numeric)
        data_rows = [[1, 100], [2, 120], [3, 90]]
        
        result = self.service._is_categorical_data(data_rows)
        assert result is False

    def test_is_correlation_data(self):
        """Test correlation data detection"""
        data_rows = [[170, 65, 25], [175, 70, 30], [180, 75, 28]]
        
        result = self.service._is_correlation_data(data_rows)
        assert result is True
        
        # Test non-correlation (mixed types)
        data_rows = [["A", 65], ["B", 70], ["C", 75]]
        
        result = self.service._is_correlation_data(data_rows)
        assert result is False

    def test_is_part_to_whole_data(self):
        """Test part-to-whole data detection"""
        data_rows = [["A", 25], ["B", 30], ["C", 20], ["D", 25]]
        
        result = self.service._is_part_to_whole_data(data_rows)
        assert result is True
        
        # Test too many categories
        data_rows = [[f"Cat{i}", 10] for i in range(15)]
        
        result = self.service._is_part_to_whole_data(data_rows)
        assert result is False

    def test_is_distribution_data(self):
        """Test distribution data detection"""
        data_rows = [[i, i*2] for i in range(1, 20)]
        
        result = self.service._is_distribution_data(data_rows)
        assert result is True
        
        # Test insufficient data
        data_rows = [[1, 2], [2, 4]]
        
        result = self.service._is_distribution_data(data_rows)
        assert result is False

    def test_is_multi_dimensional_data(self):
        """Test multi-dimensional data detection"""
        headers = ["Category", "Metric1", "Metric2", "Metric3", "Metric4"]
        data_rows = [["A", 10, 20, 30, 40], ["B", 15, 25, 35, 45]]
        
        result = self.service._is_multi_dimensional_data(headers, data_rows)
        assert result is True
        
        # Test insufficient dimensions
        headers = ["Category", "Metric1"]
        data_rows = [["A", 10], ["B", 15]]
        
        result = self.service._is_multi_dimensional_data(headers, data_rows)
        assert result is False

    def test_calculate_simple_correlation(self):
        """Test correlation calculation"""
        data_rows = [[1, 2], [2, 4], [3, 6], [4, 8], [5, 10]]
        
        correlation = self.service._calculate_simple_correlation(data_rows, 0, 1)
        assert correlation is not None
        assert abs(correlation - 1.0) < 0.01  # Perfect positive correlation

    def test_interpret_correlation(self):
        """Test correlation interpretation"""
        assert self.service._interpret_correlation(0.9) == "very strong"
        assert self.service._interpret_correlation(0.7) == "strong"
        assert self.service._interpret_correlation(0.5) == "moderate"
        assert self.service._interpret_correlation(0.3) == "weak"
        assert self.service._interpret_correlation(0.1) == "very weak"

    def test_assess_data_quality(self):
        """Test data quality assessment"""
        # High quality data (no missing values)
        data_rows = [[1, 2], [3, 4], [5, 6]]
        quality = self.service._assess_data_quality(data_rows)
        assert quality > 0.8
        
        # Poor quality data (many missing values)
        data_rows = [[1, None], [None, 4], [5, None]]
        quality = self.service._assess_data_quality(data_rows)
        assert quality < 0.5

    @pytest.mark.asyncio
    async def test_fallback_chart_recommendation(self):
        """Test fallback chart recommendation"""
        from app.services.error_handling import ErrorContext
        
        context = ErrorContext(
            request_id="test123",
            operation="chart_recommendation",
            additional_data={
                "data_source": self.sample_categorical_data.dict()
            }
        )
        
        recommendation = await self.service._fallback_chart_recommendation(context)
        
        assert isinstance(recommendation, ChartRecommendation)
        assert recommendation.primary_recommendation.recommended_chart_type in [
            ChartType.COLUMN, ChartType.BAR, ChartType.PIE
        ]
        assert recommendation.generation_metadata["fallback"] is True

    @pytest.mark.asyncio
    async def test_fallback_chart_config(self):
        """Test fallback chart configuration"""
        from app.services.error_handling import ErrorContext
        
        context = ErrorContext(
            request_id="test123",
            operation="chart_config_generation",
            additional_data={
                "data_source": self.sample_categorical_data.dict(),
                "chart_instruction": "Test chart",
                "recommended_chart_type": "column"
            }
        )
        
        config = await self.service._fallback_chart_config(context)
        
        assert isinstance(config, ChartConfig)
        assert config.chart_type == ChartType.COLUMN
        assert config.title == "Test chart"

    @pytest.mark.asyncio
    async def test_optimize_chart_config(self):
        """Test chart configuration optimization"""
        base_config = ChartConfig(
            chart_type=ChartType.COLUMN,
            title="Test Chart",
            data_range="A1:B4",
            series_config=SeriesConfig(
                x_axis_column=0,
                y_axis_columns=[1],
                series_names=["Data"]
            ),
            position=ChartPosition(x=100, y=100, width=400, height=300),
            styling=ChartStyling()
        )
        
        # Test rule-based optimization (fallback)
        optimized = self.service._apply_rule_based_optimization(
            base_config, 
            self.sample_categorical_data,
            ["visual_clarity", "data_presentation"]
        )
        
        assert isinstance(optimized, ChartConfig)
        # Should have optimizations applied
        assert optimized.position.x >= 50  # Minimum positioning
        assert optimized.position.y >= 50

    def test_optimize_for_visual_clarity(self):
        """Test visual clarity optimization"""
        config = ChartConfig(
            chart_type=ChartType.COLUMN,
            title="Test",
            data_range="A1:B4",
            series_config=SeriesConfig(x_axis_column=0, y_axis_columns=[1]),
            position=ChartPosition(x=100, y=100, width=300, height=200),
            styling=ChartStyling(font_size=12)
        )
        
        optimized = self.service._optimize_for_visual_clarity(config, self.sample_categorical_data)
        
        # Small chart should have smaller font
        assert optimized.styling.font_size <= 12

    def test_optimize_for_data_presentation(self):
        """Test data presentation optimization"""
        config = ChartConfig(
            chart_type=ChartType.COLUMN,
            title="Test",
            data_range="A1:B4",
            series_config=SeriesConfig(
                x_axis_column=0, 
                y_axis_columns=[1],
                show_data_labels=False
            ),
            position=ChartPosition(x=100, y=100, width=600, height=400),
            styling=ChartStyling()
        )
        
        optimized = self.service._optimize_for_data_presentation(config, self.sample_categorical_data)
        
        # Small dataset should show data labels
        assert optimized.series_config.show_data_labels is True

    def test_generate_smart_title(self):
        """Test smart title generation"""
        # Test line chart
        title = self.service._generate_smart_title(self.sample_time_series_data, ChartType.LINE)
        assert "Value Over Date" in title
        
        # Test pie chart
        title = self.service._generate_smart_title(self.sample_categorical_data, ChartType.PIE)
        assert "Distribution" in title
        
        # Test scatter plot
        title = self.service._generate_smart_title(self.sample_correlation_data, ChartType.SCATTER)
        assert "vs" in title