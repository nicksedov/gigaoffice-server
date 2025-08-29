"""
Test for the fix of "AIMessage can't be used in 'await' expression" error
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.spreadsheet.processor import SpreadsheetProcessorService
from app.services.gigachat.base import BaseGigaChatService
from app.services.gigachat.prompt_builder import GigaChatPromptBuilder

class MockGigaChatClient:
    """Mock GigaChat client that returns a synchronous response"""
    
    class MockAIMessage:
        def __init__(self, content):
            self.content = content
            self.id = "test-id"
    
    def invoke(self, messages):
        # Simulate the synchronous response from GigaChat
        return self.MockAIMessage(content='{"test": "response"}')

class MockGigaChatService(BaseGigaChatService):
    """Mock GigaChat service for testing"""
    
    def __init__(self):
        # Initialize with a mock prompt builder
        prompt_builder = GigaChatPromptBuilder()
        super().__init__(prompt_builder)
        self.client = MockGigaChatClient()
        self.model = "test-model"
        self.max_tokens_per_request = 8192
    
    def _init_client(self):
        pass

@pytest.mark.asyncio
async def test_spreadsheet_processor_uses_asyncio_to_thread():
    """Test that spreadsheet processor correctly uses asyncio.to_thread for GigaChat client invocation"""
    
    # Create mock service and processor
    mock_service = MockGigaChatService()
    processor = SpreadsheetProcessorService(mock_service)
    
    # Test data
    query = "Add a column with totals and create a chart"
    spreadsheet_data = {
        "worksheet": {
            "name": "Sales",
            "range": "A1:C10"
        },
        "data": [
            ["Product", "Q1", "Q2"],
            ["A", 100, 150],
            ["B", 200, 250]
        ]
    }
    
    # This should not raise "AIMessage can't be used in 'await' expression"
    result, metadata = await processor.process_spreadsheet(query, spreadsheet_data)
    
    # Verify the result
    assert result is not None
    assert "data" in result
    assert metadata["success"] is True

@pytest.mark.asyncio
async def test_spreadsheet_processor_rate_limiting():
    """Test that spreadsheet processor respects rate limiting"""
    
    # Create mock service and processor
    mock_service = MockGigaChatService()
    
    # Mock the rate limiting to return False (rate limit exceeded)
    mock_service._check_rate_limit = Mock(return_value=False)
    
    processor = SpreadsheetProcessorService(mock_service)
    
    # Test data
    query = "Add a column with totals and create a chart"
    spreadsheet_data = {
        "worksheet": {
            "name": "Sales",
            "range": "A1:C10"
        },
        "data": [
            ["Product", "Q1", "Q2"],
            ["A", 100, 150],
            ["B", 200, 250]
        ]
    }
    
    # This should raise an exception due to rate limiting
    with pytest.raises(Exception, match="Rate limit exceeded"):
        await processor.process_spreadsheet(query, spreadsheet_data)

if __name__ == "__main__":
    pytest.main([__file__])