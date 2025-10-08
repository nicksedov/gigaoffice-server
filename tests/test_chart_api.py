"""
Test Chart API Endpoints
Integration tests for chart generation API endpoints
"""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.api.chart import ChartType, DataSource, ChartConfig, ChartPosition, ChartStyling, SeriesConfig

client = TestClient(app)

class TestChartAPIEndpoints:
    """Test Chart API endpoints"""
    
    def setup_method(self):
        """Setup test method"""
        self.sample_data_source = {
            "worksheet_name": "Sheet1",
            "data_range": "A1:B4",
            "headers": ["Month", "Sales"],
            "data_rows": [
                ["Jan", 1000],
                ["Feb", 1200],
                ["Mar", 1100]
            ],
            "column_types": {"0": "string", "1": "number"}
        }
        
        self.sample_chart_request = {
            "data_source": self.sample_data_source,
            "chart_instruction": "Create a column chart showing monthly sales",
            "chart_preferences": {
                "preferred_chart_types": ["column"],
                "color_preference": "modern"
            }
        }
        
        self.sample_chart_config = {
            "chart_type": "column",
            "title": "Monthly Sales",
            "data_range": "A1:B4",
            "series_config": {
                "x_axis_column": 0,
                "y_axis_columns": [1],
                "series_names": ["Sales"],
                "show_data_labels": False,
                "smooth_lines": False
            },
            "position": {
                "x": 100,
                "y": 50,
                "width": 600,
                "height": 400
            },
            "styling": {
                "color_scheme": "office",
                "font_family": "Arial",
                "font_size": 12,
                "legend_position": "bottom"
            },
            "r7_office_properties": {}
        }
    
    def test_get_supported_chart_types(self):
        """Test getting supported chart types"""
        response = client.get("/api/v1/charts/types")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "supported_types" in data
        assert "column" in data["supported_types"]
        assert "line" in data["supported_types"]
        assert "pie" in data["supported_types"]
        assert data["total_count"] > 0
    
    def test_get_chart_examples(self):
        """Test getting chart examples"""
        response = client.get("/api/v1/charts/examples")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "examples" in data
        assert "usage_tips" in data
        assert "sales_by_month" in data["examples"]
        assert "market_share" in data["examples"]
    
    @patch('app.api.charts.chart_validation_service')
    @patch('app.api.charts.get_db')
    def test_validate_chart_config(self, mock_get_db, mock_validation_service):
        """Test chart configuration validation"""
        # Mock validation service
        mock_validation_service.get_validation_summary.return_value = {
            "is_valid": True,
            "is_r7_office_compatible": True,
            "validation_errors": [],
            "compatibility_warnings": [],
            "overall_score": 0.95
        }
        
        validation_request = {
            "chart_config": self.sample_chart_config
        }
        
        response = client.post(
            "/api/v1/charts/validate",
            json=validation_request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["is_valid"] is True
        assert data["is_r7_office_compatible"] is True
        assert len(data["validation_errors"]) == 0
        assert "Quality score: 0.95" in data["message"]
    
    @patch('app.api.charts.chart_validation_service')
    def test_validate_chart_config_with_errors(self, mock_validation_service):
        """Test chart validation with errors"""
        # Mock validation service with errors
        mock_validation_service.get_validation_summary.return_value = {
            "is_valid": False,
            "is_r7_office_compatible": False,
            "validation_errors": ["Invalid data range format"],
            "compatibility_warnings": ["Unsupported font family"],
            "overall_score": 0.3
        }
        
        validation_request = {
            "chart_config": self.sample_chart_config
        }
        
        response = client.post(
            "/api/v1/charts/validate",
            json=validation_request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["is_valid"] is False
        assert data["is_r7_office_compatible"] is False
        assert len(data["validation_errors"]) == 1
        assert len(data["compatibility_warnings"]) == 1
    
    @patch('app.api.charts.chart_validation_service')
    @patch('app.api.charts.chart_intelligence_service')
    @patch('app.api.charts.get_db')
    @patch('app.api.charts.kafka_service')
    def test_generate_chart_simple(self, mock_kafka, mock_get_db, mock_intelligence, mock_validation):
        """Test simple chart generation (immediate response)"""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock validation service
        mock_validation.validate_data_source.return_value = (True, [])
        mock_validation.validate_chart_config.return_value = (True, [])
        mock_validation.validate_r7_office_compatibility.return_value = (True, [])
        
        # Mock intelligence service
        mock_recommendation = Mock()
        mock_recommendation.primary_recommendation.recommended_chart_type = ChartType.COLUMN
        mock_recommendation.primary_recommendation.confidence = 0.95
        mock_recommendation.alternative_recommendations = []
        mock_recommendation.data_analysis = {"pattern_type": "categorical"}
        mock_recommendation.generation_metadata = {"tokens_used": 150, "processing_time": 1.5}
        
        mock_intelligence.recommend_chart_type.return_value = mock_recommendation
        
        mock_chart_config = ChartConfig(**self.sample_chart_config)
        mock_intelligence.generate_chart_config.return_value = mock_chart_config
        
        response = client.post(
            "/api/v1/charts/generate",
            json=self.sample_chart_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["chart_config"] is not None
        assert data["chart_config"]["chart_type"] == "column"
        assert data["tokens_used"] == 150
        assert data["processing_time"] == 1.5
    
    @patch('app.api.charts.chart_validation_service')
    @patch('app.api.charts.get_db')
    @patch('app.api.charts.kafka_service')
    def test_generate_chart_complex(self, mock_kafka, mock_get_db, mock_validation):
        """Test complex chart generation (queued response)"""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock validation service
        mock_validation.validate_data_source.return_value = (True, [])
        
        # Mock Kafka service
        mock_kafka.send_request.return_value = True
        
        # Create complex data (over 100 rows)
        complex_data_source = self.sample_data_source.copy()
        complex_data_source["data_rows"] = [["Month" + str(i), 1000 + i] for i in range(150)]
        
        complex_chart_request = self.sample_chart_request.copy()
        complex_chart_request["data_source"] = complex_data_source
        
        response = client.post(
            "/api/v1/charts/generate",
            json=complex_chart_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["status"] == "queued"
        assert data["chart_config"] is None
        assert "queued for processing" in data["message"]
    
    @patch('app.api.charts.chart_validation_service')
    @patch('app.api.charts.get_db')
    @patch('app.api.charts.kafka_service')
    def test_process_chart_request(self, mock_kafka, mock_get_db, mock_validation):
        """Test chart processing endpoint"""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock validation service
        mock_validation.validate_data_source.return_value = (True, [])
        
        # Mock Kafka service
        mock_kafka.send_request.return_value = True
        
        response = client.post(
            "/api/v1/charts/process",
            json=self.sample_chart_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["status"] == "queued"
        assert data["chart_config"] is None
    
    @patch('app.api.charts.get_db')
    def test_get_chart_status(self, mock_get_db):
        """Test getting chart generation status"""
        # Mock database session and request
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_request = Mock()
        mock_request.status = "completed"
        mock_request.error_message = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_request
        
        response = client.get("/api/v1/charts/status/test-request-id")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["request_id"] == "test-request-id"
        assert data["status"] == "completed"
    
    @patch('app.api.charts.get_db')
    def test_get_chart_status_not_found(self, mock_get_db):
        """Test getting status for non-existent request"""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        response = client.get("/api/v1/charts/status/non-existent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    @patch('app.api.charts.get_db')
    def test_get_chart_result(self, mock_get_db):
        """Test getting chart generation result"""
        # Mock database session and request
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_request = Mock()
        mock_request.status = "completed"
        mock_request.chart_config = self.sample_chart_config
        mock_request.tokens_used = 200
        mock_request.processing_time = 2.5
        mock_db.query.return_value.filter.return_value.first.return_value = mock_request
        
        response = client.get("/api/v1/charts/result/test-request-id")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["chart_config"] is not None
        assert data["tokens_used"] == 200
        assert data["processing_time"] == 2.5
    
    @patch('app.api.charts.get_db')
    def test_get_chart_result_pending(self, mock_get_db):
        """Test getting result for pending request"""
        # Mock database session and request
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_request = Mock()
        mock_request.status = "pending"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_request
        
        response = client.get("/api/v1/charts/result/test-request-id")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is False
        assert data["status"] == "pending"
        assert data["chart_config"] is None
        assert "still in progress" in data["message"]
    
    def test_generate_chart_invalid_data(self):
        """Test chart generation with invalid data"""
        invalid_request = {
            "data_source": {
                "worksheet_name": "",  # Invalid empty name
                "data_range": "invalid",  # Invalid range format
                "headers": [],  # Empty headers
                "data_rows": []  # Empty data
            },
            "chart_instruction": "Create a chart"
        }
        
        response = client.post(
            "/api/v1/charts/generate",
            json=invalid_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_validate_chart_config_invalid_format(self):
        """Test validation with invalid chart config format"""
        invalid_request = {
            "chart_config": {
                "chart_type": "invalid_type",  # Invalid chart type
                "title": "",  # Empty title
                "data_range": "invalid"  # Invalid range
            }
        }
        
        response = client.post(
            "/api/v1/charts/validate",
            json=invalid_request
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.charts.chart_validation_service')
    def test_data_source_validation_errors(self, mock_validation_service):
        """Test chart generation with data source validation errors"""
        # Mock validation service to return errors
        mock_validation_service.validate_data_source.return_value = (False, ["Invalid data range format"])
        
        response = client.post(
            "/api/v1/charts/generate",
            json=self.sample_chart_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid data source" in data["detail"]