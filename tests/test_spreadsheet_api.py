"""
Integration tests for the Spreadsheet API endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app


class TestSpreadsheetAPI:
    """Integration tests for Spreadsheet API"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        
        # Sample spreadsheet data
        self.sample_data = {
            "metadata": {"version": "1.0"},
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
    
    @patch('app.api.spreadsheets.kafka_service')
    @patch('app.api.spreadsheets.get_db')
    def test_process_spreadsheet_valid_data(self, mock_db, mock_kafka):
        """Test processing valid spreadsheet data"""
        # Mock database and Kafka
        mock_db.return_value = MagicMock()
        mock_kafka.send_request.return_value = True
        
        request_data = {
            "spreadsheet_data": self.sample_data,
            "query_text": "Format the data nicely",
            "category": "spreadsheet-formatting"
        }
        
        response = self.client.post(
            "/api/v1/spreadsheets/process",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "request_id" in data
        assert data["status"] == "queued"
    
    @patch('app.api.spreadsheets.kafka_service')
    @patch('app.api.spreadsheets.get_db')
    def test_process_spreadsheet_invalid_style_reference(self, mock_db, mock_kafka):
        """Test processing data with invalid style references"""
        # Mock database
        mock_db.return_value = MagicMock()
        
        # Create data with invalid style reference
        invalid_data = self.sample_data.copy()
        invalid_data["data"]["header"]["style"] = "non_existent_style"
        
        request_data = {
            "spreadsheet_data": invalid_data,
            "query_text": "Format the data",
            "category": "spreadsheet-formatting"
        }
        
        response = self.client.post(
            "/api/v1/spreadsheets/process",
            json=request_data
        )
        
        assert response.status_code == 400
        assert "Invalid spreadsheet data" in response.json()["detail"]
    
    @patch('app.api.spreadsheets.get_db')
    def test_get_processing_status(self, mock_db):
        """Test getting processing status for requests"""
        # Mock database query
        mock_request = MagicMock()
        mock_request.status = "COMPLETED"
        mock_request.error_message = None
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_request
        mock_db.return_value = mock_session
        
        response = self.client.get("/api/v1/spreadsheets/status/test-request-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "COMPLETED"
    
    @patch('app.api.spreadsheets.get_db')
    def test_get_spreadsheet_result(self, mock_db):
        """Test getting spreadsheet processing results"""
        # Mock database query
        mock_request = MagicMock()
        mock_request.status = "COMPLETED"
        mock_request.result_data = json.dumps(self.sample_data)
        mock_request.tokens_used = 150
        mock_request.processing_time = 2.5
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_request
        mock_db.return_value = mock_session
        
        response = self.client.get("/api/v1/spreadsheets/result/test-request-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["metadata"]["version"] == "1.0"
        assert "styles" in data["result"]
    
    def test_validate_spreadsheet_data(self):
        """Test spreadsheet data validation endpoint"""
        response = self.client.post(
            "/api/v1/spreadsheets/validate",
            json=self.sample_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_valid"] is True
        assert data["style_count"] == 2
    
    def test_validate_invalid_spreadsheet_data(self):
        """Test validation of invalid spreadsheet data"""
        # Create invalid data (missing styles array)
        invalid_data = self.sample_data.copy()
        invalid_data["data"]["header"]["style"] = "missing_style"
        
        response = self.client.post(
            "/api/v1/spreadsheets/validate",
            json=invalid_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_valid"] is False
        assert len(data["validation_errors"]) > 0
    
    @patch('app.api.spreadsheets.vector_search_service')
    @patch('app.api.spreadsheets.get_db')
    def test_search_spreadsheet_data(self, mock_db, mock_search):
        """Test spreadsheet data search functionality"""
        # Mock database
        mock_db.return_value = MagicMock()
        
        # Mock search service
        mock_search.search.return_value = [
            ("Customer Name", "en", 0.95),
            ("Client Name", "en", 0.87)
        ]
        
        request_data = {"data": ["name"]}
        
        response = self.client.post(
            "/api/v1/spreadsheets/data/search?domain=header&limit=10",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["search_text"] == "name"
        assert len(data[0]["search_results"]) == 2
        assert data[0]["search_results"][0]["text"] == "Customer Name"
        assert data[0]["search_results"][0]["score"] == 0.95
    
    def test_search_invalid_domain(self):
        """Test search with invalid domain parameter"""
        request_data = {"data": ["test"]}
        
        response = self.client.post(
            "/api/v1/spreadsheets/data/search?domain=invalid&limit=10",
            json=request_data
        )
        
        assert response.status_code == 400
        assert "Invalid domain parameter" in response.json()["detail"]
    
    def test_search_invalid_limit(self):
        """Test search with invalid limit parameter"""
        request_data = {"data": ["test"]}
        
        response = self.client.post(
            "/api/v1/spreadsheets/data/search?domain=header&limit=150",
            json=request_data
        )
        
        assert response.status_code == 400
        assert "Limit must be between 1 and 100" in response.json()["detail"]