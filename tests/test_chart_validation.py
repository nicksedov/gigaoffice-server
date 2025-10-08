"""
Chart Validation Service Tests
Comprehensive tests for chart validation and R7-Office compatibility
"""

import pytest
from unittest.mock import Mock

from app.models.api.chart import (
    ChartType, ChartConfig, ChartPosition, ChartStyling, SeriesConfig,
    DataSource, ColorScheme, LegendPosition, BorderStyle
)
from app.services.chart.validation import ChartValidationService

class TestChartValidationService:
    """Test Chart Validation Service"""
    
    def setup_method(self):
        """Setup test method"""
        self.service = ChartValidationService()
        
        self.valid_chart_config = ChartConfig(
            chart_type=ChartType.COLUMN,
            title="Test Chart",
            data_range="A1:B4",
            series_config=SeriesConfig(
                x_axis_column=0,
                y_axis_columns=[1],
                series_names=["Sales"],
                show_data_labels=False
            ),
            position=ChartPosition(
                x=100,
                y=100,
                width=600,
                height=400
            ),
            styling=ChartStyling(
                color_scheme=ColorScheme.OFFICE,
                font_family="Arial",
                font_size=12,
                legend_position=LegendPosition.BOTTOM
            )
        )
        
        self.valid_data_source = DataSource(
            worksheet_name="Sheet1",
            data_range="A1:B4",
            headers=["Month", "Sales"],
            data_rows=[
                ["Jan", 1000],
                ["Feb", 1200],
                ["Mar", 1100]
            ]
        )

    def test_validate_chart_config_valid(self):
        """Test validation of valid chart configuration"""
        is_valid, errors = self.service.validate_chart_config(self.valid_chart_config)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_chart_config_invalid_title(self):
        """Test validation with invalid title"""
        config = self.valid_chart_config.copy(deep=True)
        config.title = ""  # Empty title
        
        is_valid, errors = self.service.validate_chart_config(config)
        
        assert is_valid is False
        assert any("title cannot be empty" in error.lower() for error in errors)

    def test_validate_chart_config_invalid_data_range(self):
        """Test validation with invalid data range"""
        config = self.valid_chart_config.copy(deep=True)
        config.data_range = "INVALID"
        
        is_valid, errors = self.service.validate_chart_config(config)
        
        assert is_valid is False
        assert any("data range" in error.lower() for error in errors)

    def test_validate_chart_config_invalid_position(self):
        """Test validation with invalid position"""
        config = self.valid_chart_config.copy(deep=True)
        config.position.x = -10  # Negative position
        config.position.width = 50  # Too small
        
        is_valid, errors = self.service.validate_chart_config(config)
        
        assert is_valid is False
        assert any("cannot be negative" in error for error in errors)
        assert any("width should be at least" in error for error in errors)

    def test_validate_chart_config_invalid_series(self):
        """Test validation with invalid series configuration"""
        config = self.valid_chart_config.copy(deep=True)
        config.series_config.x_axis_column = -1  # Invalid column
        config.series_config.y_axis_columns = []  # No Y columns
        
        is_valid, errors = self.service.validate_chart_config(config)
        
        assert is_valid is False
        assert any("cannot be negative" in error for error in errors)
        assert any("at least one y-axis column" in error.lower() for error in errors)

    def test_validate_chart_config_invalid_colors(self):
        """Test validation with invalid colors"""
        config = self.valid_chart_config.copy(deep=True)
        config.styling.background_color = "invalid-color"
        config.styling.custom_colors = ["#invalid", "not-a-color"]
        
        is_valid, errors = self.service.validate_chart_config(config)
        
        assert is_valid is False
        assert any("invalid" in error.lower() and "color" in error.lower() for error in errors)

    def test_validate_r7_office_compatibility_valid(self):
        """Test R7-Office compatibility for valid configuration"""
        is_compatible, warnings = self.service.validate_r7_office_compatibility(self.valid_chart_config)
        
        assert is_compatible is True
        assert len(warnings) == 0

    def test_validate_r7_office_compatibility_unsupported_chart_type(self):
        """Test R7-Office compatibility with unsupported chart type"""
        config = self.valid_chart_config.copy(deep=True)
        config.chart_type = ChartType.BOX_PLOT
        
        is_compatible, warnings = self.service.validate_r7_office_compatibility(config)
        
        assert is_compatible is False
        assert any("limited support" in warning.lower() for warning in warnings)

    def test_validate_r7_office_compatibility_large_dimensions(self):
        """Test R7-Office compatibility with large dimensions"""
        config = self.valid_chart_config.copy(deep=True)
        config.position.width = 2500  # Exceeds R7-Office limit
        config.position.height = 1600  # Exceeds R7-Office limit
        
        is_compatible, warnings = self.service.validate_r7_office_compatibility(config)
        
        assert is_compatible is False
        assert any("exceeds r7-office maximum" in warning.lower() for warning in warnings)

    def test_validate_r7_office_compatibility_unsupported_font(self):
        """Test R7-Office compatibility with unsupported font"""
        config = self.valid_chart_config.copy(deep=True)
        config.styling.font_family = "UnsupportedFont"
        
        is_compatible, warnings = self.service.validate_r7_office_compatibility(config)
        
        assert is_compatible is False
        assert any("may not be available" in warning.lower() for warning in warnings)

    def test_validate_r7_office_features(self):
        """Test R7-Office feature validation"""
        config = self.valid_chart_config.copy(deep=True)
        config.chart_type = ChartType.RADAR  # Limited animation support
        config.r7_office_properties = {"enable_animation": True}
        
        warnings = self.service._validate_r7_office_features(config)
        
        assert len(warnings) > 0
        assert any("animation may not be supported" in warning.lower() for warning in warnings)

    def test_validate_r7_office_performance(self):
        """Test R7-Office performance validation"""
        config = self.valid_chart_config.copy(deep=True)
        config.position.width = 2000
        config.position.height = 1000  # Large chart
        config.styling.custom_colors = [f"#{i:06x}" for i in range(15)]  # Too many colors
        
        warnings = self.service._validate_r7_office_performance(config)
        
        assert len(warnings) > 0
        assert any("performance" in warning.lower() for warning in warnings)

    def test_validate_r7_office_api_compatibility(self):
        """Test R7-Office API version compatibility"""
        config = self.valid_chart_config.copy(deep=True)
        config.r7_office_properties = {
            "api_version": "1.0",
            "enable_animation": True  # Requires 1.1+
        }
        
        warnings = self.service._validate_r7_office_api_compatibility(config)
        
        assert len(warnings) > 0
        assert any("requires r7-office api version" in warning.lower() for warning in warnings)

    def test_validate_data_source_valid(self):
        """Test validation of valid data source"""
        is_valid, errors = self.service.validate_data_source(self.valid_data_source)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_data_source_no_headers(self):
        """Test validation with no headers"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.headers = []
        
        is_valid, errors = self.service.validate_data_source(data_source)
        
        assert is_valid is False
        assert any("must have headers" in error.lower() for error in errors)

    def test_validate_data_source_no_data(self):
        """Test validation with no data rows"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.data_rows = []
        
        is_valid, errors = self.service.validate_data_source(data_source)
        
        assert is_valid is False
        assert any("must have data rows" in error.lower() for error in errors)

    def test_validate_data_source_inconsistent_columns(self):
        """Test validation with inconsistent column count"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.data_rows = [
            ["Jan", 1000],
            ["Feb", 1200, "Extra"],  # Too many columns
            ["Mar"]  # Too few columns
        ]
        
        is_valid, errors = self.service.validate_data_source(data_source)
        
        assert is_valid is False
        assert any("has" in error and "columns" in error for error in errors)

    def test_validate_data_source_duplicate_headers(self):
        """Test validation with duplicate headers"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.headers = ["Month", "Month"]  # Duplicate headers
        
        is_valid, errors = self.service.validate_data_source(data_source)
        
        assert is_valid is False
        assert any("must be unique" in error.lower() for error in errors)

    def test_validate_data_source_empty_headers(self):
        """Test validation with empty headers"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.headers = ["Month", ""]  # Empty header
        
        is_valid, errors = self.service.validate_data_source(data_source)
        
        assert is_valid is False
        assert any("cannot be empty" in error.lower() for error in errors)

    def test_validate_data_quality_missing_values(self):
        """Test data quality validation with missing values"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.data_rows = [
            ["Jan", None],
            [None, 1200],
            ["Mar", ""]  # Empty string
        ]
        
        errors = self.service._validate_data_quality(data_source)
        
        assert len(errors) > 0
        assert any("missing values" in error.lower() for error in errors)

    def test_validate_data_quality_inconsistent_types(self):
        """Test data quality validation with inconsistent types"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.data_rows = [
            ["Jan", 1000],
            ["Feb", "Not a number"],  # String instead of number
            ["Mar", [1, 2, 3]]  # List instead of number
        ]
        
        errors = self.service._validate_data_quality(data_source)
        
        assert len(errors) > 0
        assert any("inconsistent data types" in error.lower() for error in errors)

    def test_validate_chart_data_requirements_negative_values(self):
        """Test chart data requirements with negative values"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.data_rows = [
            ["Jan", -1000],  # Negative value
            ["Feb", 1200],
            ["Mar", -500]
        ]
        
        errors = self.service._validate_chart_data_requirements(data_source)
        
        assert len(errors) > 0
        assert any("negative values" in error.lower() for error in errors)

    def test_validate_chart_data_requirements_no_numerical_data(self):
        """Test chart data requirements with no numerical data"""
        data_source = self.valid_data_source.copy(deep=True)
        data_source.data_rows = [
            ["Jan", "High"],
            ["Feb", "Medium"],
            ["Mar", "Low"]
        ]
        
        errors = self.service._validate_chart_data_requirements(data_source)
        
        assert len(errors) > 0
        assert any("numerical column required" in error.lower() for error in errors)

    def test_get_validation_summary(self):
        """Test comprehensive validation summary"""
        summary = self.service.get_validation_summary(self.valid_chart_config)
        
        assert summary["is_valid"] is True
        assert summary["is_r7_office_compatible"] is True
        assert len(summary["validation_errors"]) == 0
        assert len(summary["compatibility_warnings"]) == 0
        assert summary["overall_score"] > 0.8
        assert len(summary["recommendations"]) >= 0

    def test_get_validation_summary_with_issues(self):
        """Test validation summary with issues"""
        config = self.valid_chart_config.copy(deep=True)
        config.title = ""  # Invalid title
        config.position.width = 2500  # R7-Office limit exceeded
        
        summary = self.service.get_validation_summary(config)
        
        assert summary["is_valid"] is False
        assert summary["is_r7_office_compatible"] is False
        assert len(summary["validation_errors"]) > 0
        assert len(summary["compatibility_warnings"]) > 0
        assert summary["overall_score"] < 0.5
        assert len(summary["recommendations"]) > 0

    def test_calculate_quality_score(self):
        """Test quality score calculation"""
        # Perfect score
        score = self.service._calculate_quality_score(True, True, [], [])
        assert score == 1.0
        
        # Score with validation errors
        score = self.service._calculate_quality_score(False, True, ["error1", "error2"], [])
        assert score < 0.5
        
        # Score with compatibility warnings
        score = self.service._calculate_quality_score(True, False, [], ["warning1"])
        assert score < 1.0 and score > 0.8

    def test_generate_recommendations(self):
        """Test recommendation generation"""
        config = self.valid_chart_config.copy(deep=True)
        config.chart_type = ChartType.PIE
        config.series_config.y_axis_columns = [1, 2]  # Multiple series for pie chart
        
        recommendations = self.service._generate_recommendations(
            config, 
            ["validation error"], 
            ["compatibility warning"]
        )
        
        assert len(recommendations) > 0
        assert any("pie charts work best with single data series" in rec.lower() for rec in recommendations)

    def test_is_valid_cell_reference(self):
        """Test cell reference validation"""
        assert self.service._is_valid_cell_reference("A1") is True
        assert self.service._is_valid_cell_reference("Z99") is True
        assert self.service._is_valid_cell_reference("AA10") is True
        
        assert self.service._is_valid_cell_reference("1A") is False
        assert self.service._is_valid_cell_reference("A") is False
        assert self.service._is_valid_cell_reference("") is False
        assert self.service._is_valid_cell_reference("INVALID") is False

    def test_is_valid_hex_color(self):
        """Test hex color validation"""
        assert self.service._is_valid_hex_color("#FF0000") is True
        assert self.service._is_valid_hex_color("#fff") is True
        assert self.service._is_valid_hex_color("#123456") is True
        
        assert self.service._is_valid_hex_color("FF0000") is False  # No #
        assert self.service._is_valid_hex_color("#GG0000") is False  # Invalid hex
        assert self.service._is_valid_hex_color("#FF00") is False  # Wrong length
        assert self.service._is_valid_hex_color("") is False