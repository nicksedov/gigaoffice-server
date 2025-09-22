"""Tests for the spreadsheet search functionality"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.api.spreadsheet import SpreadsheetSearchRequest, SearchResultItem

client = TestClient(app)

class TestSpreadsheetSearch:
    """Test cases for the spreadsheet search endpoint"""
    
    def test_search_single_string_valid_request(self):
        """Test search with a single search string"""
        # Mock the vector search service
        with patch('app.services.database.vector_search.vector_search_service') as mock_service:
            # Configure mock to return test data
            mock_service.search_headers.return_value = [
                ("Имя", 0.95),
                ("Фамилия", 0.87)
            ]
            
            # Prepare request data
            search_request = SpreadsheetSearchRequest(data="имя")
            
            # Make request
            response = client.post(
                "/api/spreadsheets/data/search?domain=header&limit=5",
                json=search_request.dict()
            )
            
            # Check response
            assert response.status_code == 200
            results = response.json()
            assert len(results) == 2
            assert results[0]["text"] == "Имя"
            assert results[0]["score"] == 0.95
            assert results[0]["language"] == "ru"
    
    def test_search_multiple_strings_valid_request(self):
        """Test search with multiple search strings"""
        # Mock the vector search service
        with patch('app.services.database.vector_search.vector_search_service') as mock_service:
            # Configure mock to return test data
            mock_service.search_headers.side_effect = [
                [("Имя", 0.95)],  # Results for first search string
                [("Email", 0.88)]  # Results for second search string
            ]
            
            # Prepare request data
            search_request = SpreadsheetSearchRequest(data=["имя", "email"])
            
            # Make request
            response = client.post(
                "/api/spreadsheets/data/search?domain=header&limit=5",
                json=search_request.dict()
            )
            
            # Check response
            assert response.status_code == 200
            results = response.json()
            assert len(results) == 2
            assert results[0]["text"] == "Имя"
            assert results[1]["text"] == "Email"
    
    def test_search_invalid_domain(self):
        """Test search with invalid domain parameter"""
        # Prepare request data
        search_request = SpreadsheetSearchRequest(data="test")
        
        # Make request with invalid domain
        response = client.post(
            "/api/spreadsheets/data/search?domain=invalid&limit=5",
            json=search_request.dict()
        )
        
        # Check response
        assert response.status_code == 400
        assert "Invalid domain parameter" in response.json()["detail"]
    
    def test_search_missing_parameters(self):
        """Test search with missing required parameters"""
        # Prepare request data
        search_request = SpreadsheetSearchRequest(data="test")
        
        # Make request without required query parameters
        response = client.post(
            "/api/spreadsheets/data/search",
            json=search_request.dict()
        )
        
        # Check response - should fail due to missing query parameters
        assert response.status_code == 422  # Validation error
    
    def test_search_vector_service_error(self):
        """Test search when vector search service raises an exception"""
        # Mock the vector search service to raise an exception
        with patch('app.services.database.vector_search.vector_search_service') as mock_service:
            mock_service.search_headers.side_effect = Exception("Database connection error")
            
            # Prepare request data
            search_request = SpreadsheetSearchRequest(data="test")
            
            # Make request
            response = client.post(
                "/api/spreadsheets/data/search?domain=header&limit=5",
                json=search_request.dict()
            )
            
            # Check response
            assert response.status_code == 500
            assert "Database connection error" in response.json()["detail"]