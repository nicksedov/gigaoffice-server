"""
Test Chart Services
Unit tests for chart generation services
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.models.api.chart import (
    ChartType, DataSource, ChartConfig, ChartPosition, ChartStyling, SeriesConfig
)
from app.services.chart.intelligence import ChartIntelligenceService
from app.services.chart.validation import ChartValidationService
from app.services.chart.prompt_builder import ChartPromptBuilder

class TestChartValidationService:
    """Test ChartValidationService"""
    
    def setup_method(self):
        """Setup test method"""
        self.validation_service = ChartValidationService()
    
    def test_validate_chart_type(self):
        """Test chart type validation"""
        errors = self.validation_service._validate_chart_type(ChartType.COLUMN)
        assert len(errors) == 0
        
        # Test with invalid type (this would normally be caught by Pydantic)
        errors = self.validation_service._validate_chart_type("invalid_type")
        assert len(errors) > 0
    
    def test_validate_data_range(self):
        """Test data range validation"""
        # Valid ranges
        errors = self.validation_service._validate_data_range("A1:B10")
        assert len(errors) == 0
        
        errors = self.validation_service._validate_data_range("A1:Z100")
        assert len(errors) == 0
        
        # Invalid ranges
        errors = self.validation_service._validate_data_range("")
        assert len(errors) > 0
        
        errors = self.validation_service._validate_data_range("A1")
        assert len(errors) > 0
        
        errors = self.validation_service._validate_data_range("invalid")
        assert len(errors) > 0
    
    def test_validate_series_config(self):
        """Test series configuration validation"""
        # Valid config
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=[1, 2],
            series_names=["Sales", "Profit"]
        )
        errors = self.validation_service._validate_series_config(series_config)
        assert len(errors) == 0
        
        # Invalid config - negative column
        series_config = SeriesConfig(
            x_axis_column=-1,
            y_axis_columns=[1]
        )
        errors = self.validation_service._validate_series_config(series_config)
        assert len(errors) > 0
        
        # Invalid config - no Y columns
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=[]
        )
        errors = self.validation_service._validate_series_config(series_config)
        assert len(errors) > 0
    
    def test_validate_position(self):
        """Test position validation"""
        # Valid position
        position = ChartPosition(x=100, y=50, width=600, height=400)
        errors = self.validation_service._validate_position(position)
        assert len(errors) == 0
        
        # Invalid position - negative coordinates
        position = ChartPosition(x=-10, y=50, width=600, height=400)
        errors = self.validation_service._validate_position(position)
        assert len(errors) > 0
        
        # Invalid position - too small
        position = ChartPosition(x=100, y=50, width=50, height=400)
        errors = self.validation_service._validate_position(position)
        assert len(errors) > 0
    
    def test_validate_styling(self):
        """Test styling validation"""
        # Valid styling
        styling = ChartStyling(
            background_color="#FFFFFF",
            custom_colors=["#FF0000", "#00FF00"],
            font_size=12
        )
        errors = self.validation_service._validate_styling(styling)
        assert len(errors) == 0
        
        # Invalid styling - bad color format
        styling = ChartStyling(background_color="red")
        errors = self.validation_service._validate_styling(styling)
        assert len(errors) > 0
        
        # Invalid styling - font size too large
        styling = ChartStyling(font_size=100)
        errors = self.validation_service._validate_styling(styling)
        assert len(errors) > 0
    
    def test_is_valid_hex_color(self):
        """Test hex color validation"""
        assert self.validation_service._is_valid_hex_color("#FFFFFF") is True
        assert self.validation_service._is_valid_hex_color("#000") is True
        assert self.validation_service._is_valid_hex_color("#FF00FF") is True
        
        assert self.validation_service._is_valid_hex_color("red") is False
        assert self.validation_service._is_valid_hex_color("#GGGGGG") is False
        assert self.validation_service._is_valid_hex_color("FFFFFF") is False
    
    def test_validate_data_source(self):
        """Test data source validation"""
        # Valid data source
        data_source = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B3",
            headers=["Month", "Sales"],
            data_rows=[["Jan", 1000], ["Feb", 1200]]
        )
        is_valid, errors = self.validation_service.validate_data_source(data_source)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid data source - no headers
        data_source = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B3",
            headers=[],
            data_rows=[["Jan", 1000]]
        )
        is_valid, errors = self.validation_service.validate_data_source(data_source)
        assert is_valid is False
        assert len(errors) > 0

class TestChartIntelligenceService:
    """Test ChartIntelligenceService"""
    
    def setup_method(self):
        """Setup test method"""
        self.intelligence_service = ChartIntelligenceService()
    
    def test_is_time_series_data(self):
        """Test time series detection"""
        headers = ["Date", "Sales"]
        data_rows = [["2024-01-01", 1000], ["2024-01-02", 1200]]
        
        result = self.intelligence_service._is_time_series_data(headers, data_rows)
        assert result is True
        
        # Non-time series data
        headers = ["Product", "Sales"] 
        data_rows = [["Widget", 1000], ["Gadget", 1200]]
        
        result = self.intelligence_service._is_time_series_data(headers, data_rows)
        assert result is False
    
    def test_is_categorical_data(self):
        """Test categorical data detection"""
        # Categorical data
        data_rows = [["Product A", 100], ["Product B", 200], ["Product C", 150]]
        
        result = self.intelligence_service._is_categorical_data(data_rows)
        assert result is True
        
        # Numerical data
        data_rows = [[1, 100], [2, 200], [3, 150]]
        
        result = self.intelligence_service._is_categorical_data(data_rows)
        assert result is False
    
    def test_is_part_to_whole_data(self):
        """Test part-to-whole detection"""
        # Good for pie chart - small number of positive values
        data_rows = [["A", 25], ["B", 35], ["C", 40]]
        
        result = self.intelligence_service._is_part_to_whole_data(data_rows)
        assert result is True
        
        # Too many categories for pie chart
        data_rows = [["A", 10], ["B", 10], ["C", 10], ["D", 10], 
                    ["E", 10], ["F", 10], ["G", 10], ["H", 10], ["I", 10]]
        
        result = self.intelligence_service._is_part_to_whole_data(data_rows)
        assert result is False
    
    def test_assess_data_quality(self):
        """Test data quality assessment"""
        # High quality data - complete
        data_rows = [["A", 100], ["B", 200], ["C", 300]]
        score = self.intelligence_service._assess_data_quality(data_rows)
        assert score > 0.8
        
        # Lower quality data - has nulls
        data_rows = [["A", 100], ["B", None], ["C", 300]]
        score = self.intelligence_service._assess_data_quality(data_rows)
        assert score < 0.8
        
        # Empty data
        data_rows = []
        score = self.intelligence_service._assess_data_quality(data_rows)
        assert score == 0.0
    
    def test_fallback_chart_type_recommendation(self):
        """Test fallback chart type recommendation"""
        assert self.intelligence_service._fallback_chart_type_recommendation("time_series") == ChartType.LINE
        assert self.intelligence_service._fallback_chart_type_recommendation("categorical") == ChartType.COLUMN
        assert self.intelligence_service._fallback_chart_type_recommendation("part_to_whole") == ChartType.PIE
        assert self.intelligence_service._fallback_chart_type_recommendation("correlation") == ChartType.SCATTER
        assert self.intelligence_service._fallback_chart_type_recommendation("unknown") == ChartType.COLUMN
    
    @pytest.mark.asyncio
    async def test_analyze_data_patterns(self):
        """Test data pattern analysis"""
        data_source = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B4",
            headers=["Month", "Sales"],
            data_rows=[["Jan", 1000], ["Feb", 1200], ["Mar", 1100]]
        )
        
        analysis = await self.intelligence_service.analyze_data_patterns(data_source)
        
        assert "pattern_type" in analysis
        assert "data_characteristics" in analysis
        assert "recommended_x_axis" in analysis
        assert "recommended_y_axes" in analysis
        assert "data_quality_score" in analysis
        
        assert analysis["recommended_x_axis"] == 0
        assert analysis["recommended_y_axes"] == [1]
        assert analysis["data_quality_score"] > 0.0

class TestChartPromptBuilder:
    """Test ChartPromptBuilder"""
    
    def setup_method(self):
        """Setup test method"""
        self.prompt_builder = ChartPromptBuilder()
    
    def test_build_system_role(self):
        """Test system role prompt building"""
        system_role = self.prompt_builder._build_system_role()
        
        assert "Chart Generation Assistant" in system_role
        assert "R7-Office" in system_role
        assert "data visualization" in system_role.lower()
        assert "JSON" in system_role
    
    def test_build_chart_analysis_prompt(self):
        """Test chart analysis prompt building"""
        data_source = {
            "headers": ["Month", "Sales"],
            "data_rows": [["Jan", 1000], ["Feb", 1200]],
            "column_types": {0: "string", 1: "number"}
        }
        
        prompt = self.prompt_builder.build_chart_analysis_prompt(
            data_source,
            "Create a chart showing monthly sales trends"
        )
        
        assert "Task: Analyze data and generate chart recommendation" in prompt
        assert "Month" in prompt
        assert "Sales" in prompt
        assert "DATA_PATTERN_ANALYSIS" in prompt
        assert "CHART_TYPE_RECOMMENDATION" in prompt
        assert "CHART_CONFIGURATION" in prompt
    
    def test_build_chart_generation_prompt(self):
        """Test chart generation prompt building"""
        data_source = {
            "headers": ["Month", "Sales"],
            "data_rows": [["Jan", 1000], ["Feb", 1200]],
        }
        
        prompt = self.prompt_builder.build_chart_generation_prompt(
            data_source,
            "Create a line chart",
            "line"
        )
        
        assert "Task: Generate detailed R7-Office chart configuration" in prompt
        assert "Chart Type: line" in prompt
        assert "CHART_PROPERTIES" in prompt
        assert "SERIES_CONFIGURATION" in prompt
        assert "POSITIONING" in prompt
        assert "STYLING" in prompt
        assert "R7_OFFICE_PROPERTIES" in prompt
    
    def test_build_chart_validation_prompt(self):
        """Test chart validation prompt building"""
        chart_config = {
            "chart_type": "column",
            "title": "Test Chart",
            "data_range": "A1:B10"
        }
        
        prompt = self.prompt_builder.build_chart_validation_prompt(chart_config)
        
        assert "Task: Validate R7-Office chart configuration" in prompt
        assert "R7-OFFICE_COMPATIBILITY" in prompt
        assert "DATA_CONSISTENCY" in prompt
        assert "STYLING_VALIDATION" in prompt
        assert "BEST_PRACTICES" in prompt
    
    def test_build_chart_optimization_prompt(self):
        """Test chart optimization prompt building"""
        chart_config = {
            "chart_type": "pie",
            "title": "Market Share"
        }
        
        data_source = {
            "headers": ["Company", "Share"],
            "data_rows": [["A", 30], ["B", 40], ["C", 30]]
        }
        
        optimization_goals = ["visual_clarity", "performance"]
        
        prompt = self.prompt_builder.build_chart_optimization_prompt(
            chart_config,
            data_source,
            optimization_goals
        )
        
        assert "Task: Optimize chart configuration" in prompt
        assert "VISUAL_CLARITY" in prompt
        assert "DATA_PRESENTATION" in prompt
        assert "R7_OFFICE_PERFORMANCE" in prompt
        assert "USER_EXPERIENCE" in prompt