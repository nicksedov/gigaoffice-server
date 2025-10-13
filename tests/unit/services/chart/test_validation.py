"""
Unit Tests for ChartValidationService
Tests for validation rules, R7-Office compatibility, and error detection
"""

import pytest
from app.services.chart.validation import ChartValidationService
from app.models.api.chart import (
    ChartResultResponse, ChartConfig, ChartPosition,
    ChartStyling, SeriesConfig, ChartType, ChartData, ChartSeries,
    ColorScheme, LegendPosition, BorderStyle
)


class TestChartValidationService:
    """Test suite for ChartValidationService"""
    
    @pytest.fixture
    def validator(self):
        """Create a ChartValidationService instance"""
        return ChartValidationService()
    
    @pytest.fixture
    def valid_chart_config(self):
        """Create a valid ChartConfig for testing"""
        return ChartConfig(
            chart_type=ChartType.LINE,
            title="Test Chart",
            subtitle="Test Subtitle",
            series_config=SeriesConfig(
                x_axis_column=0,
                y_axis_columns=[1],
                series_names=["Series 1"],
                show_data_labels=False,
                smooth_lines=True
            ),
            position=ChartPosition(
                x=100,
                y=100,
                width=600,
                height=400,
                anchor_cell="D2"
            ),
            styling=ChartStyling(
                color_scheme=ColorScheme.OFFICE,
                font_family="Arial",
                font_size=12,
                background_color=None,
                border_style=BorderStyle.NONE,
                legend_position=LegendPosition.BOTTOM
            )
        )
    
    @pytest.fixture
    def valid_response(self, valid_chart_config):
        """Create a valid ChartResultResponse"""
        return ChartResultResponse(
            success=True,
            status="completed",
            message="Chart generated successfully",
            chart_config=valid_chart_config,
            tokens_used=450,
            processing_time=1.23
        )
    
    # Response Validation Tests
    
    def test_validate_response_valid(self, validator, valid_response):
        """Test validation of valid ChartResultResponse"""
        is_valid, errors = validator.validate_response(valid_response)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_response_missing_chart_config(self, validator):
        """Test validation fails when successful response missing chart_config"""
        response = ChartResultResponse(
            success=True,
            status="completed",
            message="Test",
            chart_config=None,
            tokens_used=100,
            processing_time=1.0
        )
        
        is_valid, errors = validator.validate_response(response)
        
        assert is_valid is False
        assert any('chart_config' in err.lower() for err in errors)
    
    def test_validate_response_invalid_status(self, validator, valid_chart_config):
        """Test validation fails with invalid status"""
        with pytest.raises(ValueError):
            ChartResultResponse(
                success=True,
                status="invalid_status",
                message="Test",
                chart_config=valid_chart_config,
                tokens_used=100,
                processing_time=1.0
            )
    
    def test_validate_response_negative_tokens(self, validator, valid_chart_config):
        """Test validation fails with negative tokens_used"""
        with pytest.raises(ValueError):
            ChartResultResponse(
                success=True,
                status="completed",
                message="Test",
                chart_config=valid_chart_config,
                tokens_used=-100,
                processing_time=1.0
            )
    
    def test_validate_response_negative_processing_time(self, validator, valid_chart_config):
        """Test validation fails with negative processing_time"""
        with pytest.raises(ValueError):
            ChartResultResponse(
                success=True,
                status="completed",
                message="Test",
                chart_config=valid_chart_config,
                tokens_used=100,
                processing_time=-1.0
            )
    
    # Chart Config Validation Tests
    
    def test_validate_chart_config_valid(self, validator, valid_chart_config):
        """Test validation of valid ChartConfig"""
        is_valid, errors = validator.validate_chart_config(valid_chart_config)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_chart_config_empty_title(self, validator, valid_chart_config):
        """Test validation fails with empty title"""
        valid_chart_config.title = ""
        
        is_valid, errors = validator.validate_chart_config(valid_chart_config)
        
        assert is_valid is False
        assert any('title' in err.lower() for err in errors)
    
    def test_validate_chart_config_title_too_long(self, validator, valid_chart_config):
        """Test validation fails with overly long title"""
        valid_chart_config.title = "A" * 201
        
        is_valid, errors = validator.validate_chart_config(valid_chart_config)
        
        assert is_valid is False
        assert any('title' in err.lower() and '200' in err for err in errors)
    
    # Series Config Validation Tests
    
    def test_validate_series_config_valid(self, validator):
        """Test validation of valid SeriesConfig"""
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=[1, 2],
            series_names=["Series 1", "Series 2"],
            show_data_labels=True,
            smooth_lines=False
        )
        
        is_valid, errors = validator.validate_series_config(series_config)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_series_config_negative_x_axis(self, validator):
        """Test validation fails with negative x_axis_column"""
        series_config = SeriesConfig(
            x_axis_column=-1,
            y_axis_columns=[1],
            series_names=["Series 1"],
            show_data_labels=False,
            smooth_lines=False
        )
        
        is_valid, errors = validator.validate_series_config(series_config)
        
        assert is_valid is False
        assert any('x_axis_column' in err.lower() for err in errors)
    
    def test_validate_series_config_empty_y_axis(self, validator):
        """Test validation fails with empty y_axis_columns"""
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=[],
            series_names=[],
            show_data_labels=False,
            smooth_lines=False
        )
        
        is_valid, errors = validator.validate_series_config(series_config)
        
        assert is_valid is False
        assert any('y_axis_columns' in err.lower() for err in errors)
    
    def test_validate_series_config_mismatched_names(self, validator):
        """Test validation fails when series_names length doesn't match y_axis_columns"""
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=[1, 2],
            series_names=["Series 1"],  # Only one name for two columns
            show_data_labels=False,
            smooth_lines=False
        )
        
        is_valid, errors = validator.validate_series_config(series_config)
        
        assert is_valid is False
        assert any('series_names' in err.lower() for err in errors)
    
    def test_validate_series_config_duplicate_columns(self, validator):
        """Test validation fails with duplicate y_axis_columns"""
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=[1, 1],  # Duplicate
            series_names=["Series 1", "Series 2"],
            show_data_labels=False,
            smooth_lines=False
        )
        
        is_valid, errors = validator.validate_series_config(series_config)
        
        assert is_valid is False
        assert any('duplicate' in err.lower() for err in errors)
    
    # Position Validation Tests
    
    def test_validate_position_valid(self, validator):
        """Test validation of valid ChartPosition"""
        position = ChartPosition(
            x=100,
            y=100,
            width=600,
            height=400,
            anchor_cell="A1"
        )
        
        is_valid, errors = validator.validate_position(position)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_position_negative_coordinates(self, validator):
        """Test validation fails with negative coordinates"""
        position = ChartPosition(
            x=-10,
            y=-10,
            width=600,
            height=400
        )
        
        is_valid, errors = validator.validate_position(position)
        
        assert is_valid is False
        assert len(errors) >= 2  # Both x and y are negative
    
    def test_validate_position_too_small(self, validator):
        """Test validation fails with dimensions below minimum"""
        position = ChartPosition(
            x=0,
            y=0,
            width=50,  # Too small
            height=50   # Too small
        )
        
        is_valid, errors = validator.validate_position(position)
        
        assert is_valid is False
        assert any('width' in err.lower() for err in errors)
        assert any('height' in err.lower() for err in errors)
    
    def test_validate_position_too_large(self, validator):
        """Test validation fails with dimensions above maximum"""
        position = ChartPosition(
            x=0,
            y=0,
            width=3000,  # Too large
            height=2000  # Too large
        )
        
        is_valid, errors = validator.validate_position(position)
        
        assert is_valid is False
        assert any('width' in err.lower() for err in errors)
        assert any('height' in err.lower() for err in errors)
    
    def test_validate_position_invalid_anchor_cell(self, validator):
        """Test validation fails with invalid anchor_cell format"""
        position = ChartPosition(
            x=0,
            y=0,
            width=600,
            height=400,
            anchor_cell="invalid123"  # Invalid format
        )
        
        is_valid, errors = validator.validate_position(position)
        
        assert is_valid is False
        assert any('anchor_cell' in err.lower() for err in errors)
    
    # Styling Validation Tests
    
    def test_validate_styling_valid(self, validator):
        """Test validation of valid ChartStyling"""
        styling = ChartStyling(
            color_scheme=ColorScheme.MODERN,
            font_family="Arial",
            font_size=14,
            background_color="#FFFFFF",
            border_style=BorderStyle.SOLID,
            legend_position=LegendPosition.TOP
        )
        
        is_valid, errors = validator.validate_styling(styling)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_styling_font_size_too_small(self, validator):
        """Test validation fails with font size below minimum"""
        styling = ChartStyling(
            color_scheme=ColorScheme.OFFICE,
            font_family="Arial",
            font_size=5,  # Too small
            background_color=None,
            border_style=BorderStyle.NONE,
            legend_position=LegendPosition.BOTTOM
        )
        
        is_valid, errors = validator.validate_styling(styling)
        
        assert is_valid is False
        assert any('font' in err.lower() and '8' in err for err in errors)
    
    def test_validate_styling_font_size_too_large(self, validator):
        """Test validation fails with font size above maximum"""
        styling = ChartStyling(
            color_scheme=ColorScheme.OFFICE,
            font_family="Arial",
            font_size=100,  # Too large
            background_color=None,
            border_style=BorderStyle.NONE,
            legend_position=LegendPosition.BOTTOM
        )
        
        is_valid, errors = validator.validate_styling(styling)
        
        assert is_valid is False
        assert any('font' in err.lower() and '72' in err for err in errors)
    
    def test_validate_styling_invalid_background_color(self, validator):
        """Test validation fails with invalid background color format"""
        styling = ChartStyling(
            color_scheme=ColorScheme.OFFICE,
            font_family="Arial",
            font_size=12,
            background_color="red",  # Invalid format (should be #RRGGBB)
            border_style=BorderStyle.NONE,
            legend_position=LegendPosition.BOTTOM
        )
        
        is_valid, errors = validator.validate_styling(styling)
        
        assert is_valid is False
        assert any('background_color' in err.lower() or 'hex' in err.lower() for err in errors)
    
    # R7-Office Compatibility Tests
    
    def test_validate_r7_office_compatibility_valid(self, validator, valid_chart_config):
        """Test R7-Office compatibility for valid config"""
        is_compatible, warnings = validator.validate_r7_office_compatibility(valid_chart_config)
        
        assert is_compatible is True
        assert len(warnings) == 0
    
    def test_validate_r7_office_compatibility_unsupported_chart_type(self, validator, valid_chart_config):
        """Test R7-Office compatibility warning for unsupported chart type"""
        valid_chart_config.chart_type = ChartType.BOX_PLOT
        
        is_compatible, warnings = validator.validate_r7_office_compatibility(valid_chart_config)
        
        assert is_compatible is False
        assert any('chart type' in warn.lower() for warn in warnings)
    
    def test_validate_r7_office_compatibility_too_many_series(self, validator, valid_chart_config):
        """Test R7-Office compatibility warning for too many series"""
        valid_chart_config.series_config.y_axis_columns = list(range(1, 12))  # 11 series
        
        is_compatible, warnings = validator.validate_r7_office_compatibility(valid_chart_config)
        
        assert is_compatible is False
        assert any('series' in warn.lower() for warn in warnings)
    
    # Validation Summary Tests
    
    def test_get_validation_summary(self, validator, valid_response):
        """Test getting comprehensive validation summary"""
        summary = validator.get_validation_summary(valid_response)
        
        assert summary is not None
        assert 'is_valid' in summary
        assert 'is_r7_office_compatible' in summary
        assert 'validation_errors' in summary
        assert 'compatibility_warnings' in summary
        assert 'response_structure' in summary
        
        assert summary['is_valid'] is True
        assert summary['is_r7_office_compatible'] is True
    
    def test_get_validation_summary_with_errors(self, validator):
        """Test validation summary with errors"""
        # Create response with errors
        response = ChartResultResponse(
            success=False,
            status="failed",
            message="Test error",
            chart_config=None,
            tokens_used=0,
            processing_time=0.0
        )
        
        summary = validator.get_validation_summary(response)
        
        assert summary['is_valid'] is True  # This response is structurally valid
        assert summary['response_structure']['has_chart_config'] is False
    
    # Chart Data Validation Tests
    
    def test_validate_chart_data_valid(self, validator):
        """Test validation of valid ChartData"""
        chart_data = ChartData(
            data_range="A1:B10",
            chart_data=[
                ChartSeries(name="X", values=[1, 2, 3], format="General"),
                ChartSeries(name="Y", values=[10, 20, 30], format="#,##0")
            ],
            chart_type="line",
            query_text="Build a chart"
        )
        
        is_valid, errors = validator.validate_chart_data(chart_data)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_chart_data_empty_series(self, validator):
        """Test validation fails with no chart_data series"""
        chart_data = ChartData(
            data_range="A1:B10",
            chart_data=[],
            chart_type="line",
            query_text="Build a chart"
        )
        
        is_valid, errors = validator.validate_chart_data(chart_data)
        
        assert is_valid is False
        assert any('chart_data' in err.lower() for err in errors)
    
    def test_validate_chart_data_mismatched_lengths(self, validator):
        """Test validation fails when series have different lengths"""
        chart_data = ChartData(
            data_range="A1:B10",
            chart_data=[
                ChartSeries(name="X", values=[1, 2, 3], format="General"),
                ChartSeries(name="Y", values=[10, 20], format="#,##0")  # Different length
            ],
            chart_type="line",
            query_text="Build a chart"
        )
        
        is_valid, errors = validator.validate_chart_data(chart_data)
        
        assert is_valid is False
        assert any('same number of values' in err.lower() for err in errors)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
