"""
Test Chart API Models
Unit tests for chart generation data models
"""

import pytest
from pydantic import ValidationError

from app.models.api.chart import (
    ChartType, ColorScheme, LegendPosition, BorderStyle,
    DataSource, ChartPosition, ChartStyling, SeriesConfig, ChartConfig,
    ChartPreferences, R7OfficeConfig, ChartGenerationRequest,
    ChartValidationRequest, ChartGenerationResponse, ChartStatusResponse,
    ChartResultResponse, ChartValidationResponse, DataPattern, ChartRecommendation
)

class TestDataSource:
    """Test DataSource model"""
    
    def test_valid_data_source(self):
        """Test creating valid DataSource"""
        data_source = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B10",
            headers=["Month", "Sales"],
            data_rows=[
                ["Jan", 1000],
                ["Feb", 1200],
                ["Mar", 1100]
            ],
            column_types={0: "string", 1: "number"}
        )
        
        assert data_source.worksheet_name == "Sheet1"
        assert data_source.data_range == "A1:B10"
        assert len(data_source.headers) == 2
        assert len(data_source.data_rows) == 3
    
    def test_invalid_data_range(self):
        """Test invalid data range validation"""
        with pytest.raises(ValidationError):
            DataSource(
                worksheet_name="Sheet1",
                data_range="",  # Empty range
                headers=["Month", "Sales"],
                data_rows=[["Jan", 1000]]
            )
        
        with pytest.raises(ValidationError):
            DataSource(
                worksheet_name="Sheet1", 
                data_range="A1",  # Missing colon
                headers=["Month", "Sales"],
                data_rows=[["Jan", 1000]]
            )

class TestChartPosition:
    """Test ChartPosition model"""
    
    def test_valid_position(self):
        """Test creating valid ChartPosition"""
        position = ChartPosition(
            x=100,
            y=50,
            width=600,
            height=400,
            anchor_cell="D5"
        )
        
        assert position.x == 100
        assert position.y == 50
        assert position.width == 600
        assert position.height == 400
        assert position.anchor_cell == "D5"
    
    def test_negative_coordinates(self):
        """Test negative coordinates validation"""
        with pytest.raises(ValidationError):
            ChartPosition(x=-10, y=50, width=600, height=400)
        
        with pytest.raises(ValidationError):
            ChartPosition(x=100, y=-5, width=600, height=400)
    
    def test_minimum_dimensions(self):
        """Test minimum dimension validation"""
        with pytest.raises(ValidationError):
            ChartPosition(x=100, y=50, width=50, height=400)  # Too narrow
        
        with pytest.raises(ValidationError):
            ChartPosition(x=100, y=50, width=600, height=50)  # Too short

class TestChartStyling:
    """Test ChartStyling model"""
    
    def test_valid_styling(self):
        """Test creating valid ChartStyling"""
        styling = ChartStyling(
            color_scheme=ColorScheme.MODERN,
            font_family="Arial",
            font_size=14,
            background_color="#FFFFFF",
            border_style=BorderStyle.SOLID,
            legend_position=LegendPosition.BOTTOM,
            custom_colors=["#FF0000", "#00FF00", "#0000FF"]
        )
        
        assert styling.color_scheme == ColorScheme.MODERN
        assert styling.font_size == 14
        assert len(styling.custom_colors) == 3
    
    def test_invalid_colors(self):
        """Test invalid color format validation"""
        with pytest.raises(ValidationError):
            ChartStyling(background_color="red")  # Not hex format
        
        with pytest.raises(ValidationError):
            ChartStyling(custom_colors=["red", "blue"])  # Not hex format
    
    def test_font_size_limits(self):
        """Test font size validation"""
        with pytest.raises(ValidationError):
            ChartStyling(font_size=5)  # Too small
        
        with pytest.raises(ValidationError):
            ChartStyling(font_size=80)  # Too large

class TestSeriesConfig:
    """Test SeriesConfig model"""
    
    def test_valid_series_config(self):
        """Test creating valid SeriesConfig"""
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=[1, 2],
            series_names=["Sales", "Profit"],
            show_data_labels=True,
            smooth_lines=False
        )
        
        assert series_config.x_axis_column == 0
        assert len(series_config.y_axis_columns) == 2
        assert len(series_config.series_names) == 2
    
    def test_negative_column_indices(self):
        """Test negative column index validation"""
        with pytest.raises(ValidationError):
            SeriesConfig(x_axis_column=-1, y_axis_columns=[1])
        
        with pytest.raises(ValidationError):
            SeriesConfig(x_axis_column=0, y_axis_columns=[-1])

class TestChartConfig:
    """Test complete ChartConfig model"""
    
    def test_valid_chart_config(self):
        """Test creating valid ChartConfig"""
        chart_config = ChartConfig(
            chart_type=ChartType.COLUMN,
            title="Monthly Sales",
            subtitle="Q1 2024",
            data_range="A1:B4",
            series_config=SeriesConfig(
                x_axis_column=0,
                y_axis_columns=[1],
                series_names=["Sales"]
            ),
            position=ChartPosition(x=100, y=50, width=600, height=400),
            styling=ChartStyling(),
            r7_office_properties={"api_version": "1.0"}
        )
        
        assert chart_config.chart_type == ChartType.COLUMN
        assert chart_config.title == "Monthly Sales"
        assert chart_config.subtitle == "Q1 2024"
        assert chart_config.r7_office_properties["api_version"] == "1.0"

class TestChartGenerationRequest:
    """Test ChartGenerationRequest model"""
    
    def test_valid_generation_request(self):
        """Test creating valid ChartGenerationRequest"""
        data_source = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B4",
            headers=["Month", "Sales"],
            data_rows=[["Jan", 1000], ["Feb", 1200], ["Mar", 1100]]
        )
        
        request = ChartGenerationRequest(
            data_source=data_source,
            chart_instruction="Create a column chart showing monthly sales",
            chart_preferences=ChartPreferences(
                preferred_chart_types=[ChartType.COLUMN, ChartType.LINE],
                color_preference=ColorScheme.MODERN
            ),
            r7_office_config=R7OfficeConfig(
                api_version="1.0",
                compatibility_mode=True
            )
        )
        
        assert request.chart_instruction == "Create a column chart showing monthly sales"
        assert len(request.chart_preferences.preferred_chart_types) == 2
        assert request.r7_office_config.compatibility_mode is True

class TestChartValidationRequest:
    """Test ChartValidationRequest model"""
    
    def test_valid_validation_request(self):
        """Test creating valid ChartValidationRequest"""
        chart_config = ChartConfig(
            chart_type=ChartType.PIE,
            title="Market Share",
            data_range="A1:B5",
            series_config=SeriesConfig(x_axis_column=0, y_axis_columns=[1]),
            position=ChartPosition(x=200, y=100, width=500, height=300),
            styling=ChartStyling()
        )
        
        request = ChartValidationRequest(chart_config=chart_config)
        
        assert request.chart_config.chart_type == ChartType.PIE
        assert request.chart_config.title == "Market Share"

class TestResponseModels:
    """Test response models"""
    
    def test_chart_generation_response(self):
        """Test ChartGenerationResponse model"""
        response = ChartGenerationResponse(
            success=True,
            request_id="test-123",
            status="completed",
            chart_config=None,
            message="Chart generated successfully",
            tokens_used=150,
            processing_time=2.5
        )
        
        assert response.success is True
        assert response.request_id == "test-123"
        assert response.tokens_used == 150
        assert response.processing_time == 2.5
    
    def test_chart_status_response(self):
        """Test ChartStatusResponse model"""
        response = ChartStatusResponse(
            success=True,
            request_id="test-456",
            status="processing",
            message="Chart generation in progress"
        )
        
        assert response.success is True
        assert response.status == "processing"
    
    def test_chart_validation_response(self):
        """Test ChartValidationResponse model"""
        response = ChartValidationResponse(
            success=True,
            is_valid=True,
            is_r7_office_compatible=True,
            validation_errors=[],
            compatibility_warnings=["Font may not be available"],
            message="Validation completed successfully"
        )
        
        assert response.is_valid is True
        assert response.is_r7_office_compatible is True
        assert len(response.compatibility_warnings) == 1

class TestChartRecommendation:
    """Test ChartRecommendation model"""
    
    def test_valid_recommendation(self):
        """Test creating valid ChartRecommendation"""
        primary_pattern = DataPattern(
            pattern_type="time_series",
            confidence=0.95,
            recommended_chart_type=ChartType.LINE,
            reasoning="Data shows clear temporal progression"
        )
        
        alternative_pattern = DataPattern(
            pattern_type="categorical",
            confidence=0.75,
            recommended_chart_type=ChartType.COLUMN,
            reasoning="Could also be visualized as categorical comparison"
        )
        
        recommendation = ChartRecommendation(
            primary_recommendation=primary_pattern,
            alternative_recommendations=[alternative_pattern],
            data_analysis={
                "pattern_type": "time_series",
                "data_quality_score": 0.9
            },
            generation_metadata={
                "tokens_used": 200,
                "processing_time": 1.5
            }
        )
        
        assert recommendation.primary_recommendation.confidence == 0.95
        assert len(recommendation.alternative_recommendations) == 1
        assert recommendation.data_analysis["pattern_type"] == "time_series"
        assert recommendation.generation_metadata["tokens_used"] == 200