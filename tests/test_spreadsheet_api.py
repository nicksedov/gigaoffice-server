"""
Tests for the spreadsheet API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_process_spreadsheet_request(client, sample_spreadsheet_data):
    """Test the /api/spreadsheets/process endpoint"""
    # Mock the Kafka service to avoid actual Kafka calls
    with patch('app.api.spreadsheets.kafka_service') as mock_kafka:
        mock_kafka.send_request.return_value = True
        
        response = client.post(
            "/api/spreadsheets/process",
            json={
                "spreadsheet_data": sample_spreadsheet_data,
                "query_text": "Add a total column"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "queued"
        assert "request_id" in data
        assert "Spreadsheet processing request added to queue" in data["message"]

def test_process_spreadsheet_request_validation_error(client):
    """Test the /api/spreadsheets/process endpoint with invalid data"""
    response = client.post(
        "/api/spreadsheets/process",
        json={
            "query_text": "Add a total column"
            # Missing required spreadsheet_data field
        }
    )
    
    assert response.status_code == 422

def test_get_spreadsheet_processing_status_not_found(client):
    """Test the /api/spreadsheets/status/{request_id} endpoint with non-existent request"""
    # Mock the database query to return None
    with patch('app.api.spreadsheets.db.query') as mock_query:
        mock_query.return_value.filter.return_value.first.return_value = None
        
        response = client.get("/api/spreadsheets/status/non-existent-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "Request not found" in data["detail"]

@patch('app.api.spreadsheets.db')
def test_get_spreadsheet_processing_status_pending(mock_db, client):
    """Test the /api/spreadsheets/status/{request_id} endpoint with pending request"""
    # Mock the database query to return a pending request
    mock_request = MagicMock()
    mock_request.id = "test-id"
    mock_request.status = "pending"
    mock_request.error_message = None
    mock_request.result_data = None
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_request
    
    response = client.get("/api/spreadsheets/status/test-id")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False  # Not completed yet
    assert data["status"] == "pending"
    assert data["message"] == "Processing in progress"
    assert data["result_data"] is None

@patch('app.api.spreadsheets.db')
def test_get_spreadsheet_processing_status_completed(mock_db, client, sample_spreadsheet_data):
    """Test the /api/spreadsheets/status/{request_id} endpoint with completed request"""
    # Mock the database query to return a completed request
    mock_request = MagicMock()
    mock_request.id = "test-id"
    mock_request.status = "completed"
    mock_request.error_message = None
    mock_request.result_data = sample_spreadsheet_data
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_request
    
    response = client.get("/api/spreadsheets/status/test-id")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "completed"
    assert data["result_data"] is not None
    assert data["result_data"]["worksheet"]["name"] == "TestSheet"