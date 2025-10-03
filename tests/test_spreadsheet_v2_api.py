"""
Integration tests for the V2 Spreadsheet API endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


class TestSpreadsheetV2API:
    """Integration tests for V2 Spreadsheet API"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        
        # Sample V2 spreadsheet data
        self.sample_v2_data = {
            "metadata": {"version": "2.0"},
            "worksheet": {"name": "TestSheet", "range": "A1:C3"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "Email"],
                    "style": "header_style"
                },
                "rows": [
                    {"values": ["John", 30, "john@example.com"], "style": "row_style"},
                    {"values": ["Jane", 25, "jane@example.com"], "style": "row_style"}
                ]
            },
            "styles": [
                {
                    "id": "header_style",
                    "background_color": "#4472C4",
                    "font_color": "#FFFFFF",
                    "font_weight": "bold"
                },
                {
                    "id": "row_style",
                    "background_color": "#F2F2F2"
                }
            ],
            "columns": [
                {"index": 0, "format": "General"},
                {"index": 1, "format": "Number"},
                {"index": 2, "format": "General"}
            ]
        }
        
        # Sample legacy data
        self.sample_legacy_data = {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "TestSheet", "range": "A1:C3"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "Email"],
                    "style": {
                        "background_color": "#4472C4",
                        "font_color": "#FFFFFF",
                        "font_weight": "bold"
                    }
                },
                "rows": [
                    {
                        "values": ["John", 30, "john@example.com"],
                        "style": {"background_color": "#F2F2F2"}
                    },
                    {
                        "values": ["Jane", 25, "jane@example.com"],
                        "style": {"background_color": "#F2F2F2"}
                    }
                ]
            }
        }
    
    @patch('app.api.spreadsheets_v2.kafka_service')
    @patch('app.api.spreadsheets_v2.get_db')
    def test_process_spreadsheet_v2_valid_data(self, mock_db, mock_kafka):
        """Test processing valid V2 spreadsheet data"""
        # Mock database and Kafka
        mock_db.return_value = MagicMock()
        mock_kafka.send_request.return_value = True
        
        request_data = {
            "spreadsheet_data": self.sample_v2_data,
            "query_text": "Format the data nicely",
            "category": "spreadsheet-formatting"
        }
        
        response = self.client.post(
            "/api/v2/spreadsheets/process",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "request_id" in data
        assert data["status"] == "queued"
    
    @patch('app.api.spreadsheets_v2.kafka_service')
    @patch('app.api.spreadsheets_v2.get_db')
    def test_process_spreadsheet_v2_invalid_style_reference(self, mock_db, mock_kafka):
        """Test processing V2 data with invalid style references"""
        # Mock database
        mock_db.return_value = MagicMock()
        
        # Create data with invalid style reference
        invalid_data = self.sample_v2_data.copy()
        invalid_data["data"]["header"]["style"] = "non_existent_style"
        
        request_data = {
            "spreadsheet_data": invalid_data,
            "query_text": "Format the data",
            "category": "spreadsheet-formatting"
        }
        
        response = self.client.post(
            "/api/v2/spreadsheets/process",
            json=request_data
        )
        
        assert response.status_code == 400
        assert "Invalid spreadsheet data" in response.json()["detail"]
    
    @patch('app.api.spreadsheets_v2.get_db')
    def test_get_processing_status_v2(self, mock_db):
        """Test getting processing status for V2 requests"""
        # Mock database query
        mock_request = MagicMock()
        mock_request.status = "COMPLETED"
        mock_request.error_message = None
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_request
        mock_db.return_value = mock_session
        
        response = self.client.get("/api/v2/spreadsheets/status/test-request-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "COMPLETED"
    
    @patch('app.api.spreadsheets_v2.get_db')
    def test_get_spreadsheet_result_v2_format_selection(self, mock_db):
        """Test getting results with format version selection"""
        # Mock database query
        mock_request = MagicMock()
        mock_request.status = "COMPLETED"
        mock_request.result_data = json.dumps(self.sample_legacy_data)
        mock_request.tokens_used = 150
        mock_request.processing_time = 2.5
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_request
        mock_db.return_value = mock_session
        
        # Test V2 format response
        response = self.client.get(
            "/api/v2/spreadsheets/result/test-request-id?format_version=2.0"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["metadata"]["version"] == "2.0"
        assert "styles" in data["result"]
        
        # Test V1 format response
        response = self.client.get(
            "/api/v2/spreadsheets/result/test-request-id?format_version=1.0"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["metadata"]["version"] == "1.0"
        assert "styles" not in data["result"]
    
    def test_transform_to_legacy_format(self):
        """Test transformation endpoint from V2 to legacy format"""
        response = self.client.post(
            "/api/v2/spreadsheets/transform/to-legacy",
            json=self.sample_v2_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["metadata"]["version"] == "1.0"
        assert "styles" not in data["data"]
        
        # Check that styles are inlined
        header_style = data["data"]["data"]["header"]["style"]
        assert isinstance(header_style, dict)
        assert header_style["background_color"] == "#4472C4"
    
    def test_transform_from_legacy_format(self):
        """Test transformation endpoint from legacy to V2 format"""
        response = self.client.post(
            "/api/v2/spreadsheets/transform/from-legacy",
            json=self.sample_legacy_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["metadata"]["version"] == "2.0"
        assert "styles" in data["data"]
        
        # Check that styles are referenced
        header_style = data["data"]["data"]["header"]["style"]
        assert isinstance(header_style, str)
    
    def test_validate_spreadsheet_data(self):
        """Test spreadsheet data validation endpoint"""
        response = self.client.post(
            "/api/v2/spreadsheets/validate",
            json=self.sample_v2_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_valid"] is True
        assert data["style_count"] == 2
    
    def test_validate_invalid_spreadsheet_data(self):
        """Test validation of invalid spreadsheet data"""
        # Create invalid data (missing styles array)
        invalid_data = self.sample_v2_data.copy()
        invalid_data["data"]["header"]["style"] = "missing_style"
        
        response = self.client.post(
            "/api/v2/spreadsheets/validate",
            json=invalid_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_valid"] is False
        assert len(data["validation_errors"]) > 0


class TestLegacyAPICompatibility:
    """Test backward compatibility in legacy API endpoints"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        
        # Sample V2 data for testing compatibility
        self.sample_v2_data = {
            "metadata": {"version": "2.0"},
            "worksheet": {"name": "TestSheet", "range": "A1:C3"},
            "data": {
                "header": {
                    "values": ["Name", "Age", "Email"],
                    "style": "header_style"
                },
                "rows": [
                    {"values": ["John", 30, "john@example.com"], "style": "row_style"}
                ]
            },
            "styles": [
                {
                    "id": "header_style",
                    "background_color": "#4472C4",
                    "font_color": "#FFFFFF",
                    "font_weight": "bold"
                },
                {
                    "id": "row_style",
                    "background_color": "#F2F2F2"
                }
            ]
        }
    
    @patch('app.api.spreadsheets.kafka_service')
    @patch('app.api.spreadsheets.get_db')
    def test_legacy_api_processes_v2_data(self, mock_db, mock_kafka):
        """Test that legacy API can process V2 format data"""
        # Mock database and Kafka
        mock_db.return_value = MagicMock()
        mock_kafka.send_request.return_value = True
        
        request_data = {
            "spreadsheet_data": self.sample_v2_data,
            "query_text": "Format the data",
            "category": "spreadsheet-formatting"
        }
        
        response = self.client.post(
            "/api/spreadsheets/process",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_detect_format_endpoint(self):
        """Test format detection endpoint"""
        response = self.client.post(
            "/api/spreadsheets/detect-format",
            json=self.sample_v2_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["format_version"] == "2.0"
    
    def test_auto_transform_endpoint(self):
        """Test auto-transform endpoint"""
        legacy_data = {
            "metadata": {"version": "1.0"},
            "data": {
                "header": {
                    "values": ["Name"],
                    "style": {"background_color": "#FF0000"}
                },
                "rows": []
            }
        }
        
        response = self.client.post(
            "/api/spreadsheets/auto-transform?target_version=2.0",
            json=legacy_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["metadata"]["version"] == "2.0"
        assert data["target_version"] == "2.0"


class TestAPIErrorHandling:
    """Test error handling in API endpoints"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payload"""
        response = self.client.post(
            "/api/v2/spreadsheets/process",
            data="invalid json"
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields"""
        incomplete_data = {
            "query_text": "Test query"
            # Missing spreadsheet_data
        }
        
        response = self.client.post(
            "/api/v2/spreadsheets/process",
            json=incomplete_data
        )
        
        assert response.status_code == 422
    
    def test_nonexistent_request_id(self):
        """Test handling of non-existent request ID"""
        with patch('app.api.spreadsheets_v2.get_db') as mock_db:
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_db.return_value = mock_session
            
            response = self.client.get("/api/v2/spreadsheets/status/nonexistent-id")
            
            assert response.status_code == 404
            assert "Request not found" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__])