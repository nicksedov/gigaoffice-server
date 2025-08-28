"""
Tests for the spreadsheet processor service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.spreadsheet.processor import SpreadsheetProcessorService

@pytest.fixture
def mock_gigachat_service():
    """Create a mock GigaChat service"""
    mock_service = MagicMock()
    mock_service.prompt_builder = MagicMock()
    mock_service.client = AsyncMock()
    mock_service._add_request_time = MagicMock()
    mock_service._count_tokens = MagicMock(return_value=100)
    mock_service.total_tokens_used = 0
    mock_service.model = "GigaChat"
    return mock_service

@pytest.fixture
def spreadsheet_processor(mock_gigachat_service):
    """Create a SpreadsheetProcessorService instance with a mock GigaChat service"""
    return SpreadsheetProcessorService(mock_gigachat_service)

def test_spreadsheet_processor_initialization(mock_gigachat_service):
    """Test SpreadsheetProcessorService initialization"""
    processor = SpreadsheetProcessorService(mock_gigachat_service)
    assert processor.gigachat_service == mock_gigachat_service

@pytest.mark.asyncio
async def test_process_spreadsheet_success(spreadsheet_processor, mock_gigachat_service, sample_spreadsheet_data):
    """Test successful spreadsheet processing"""
    # Mock the response from GigaChat
    mock_response = MagicMock()
    mock_response.content = '{"worksheet": {"name": "ProcessedSheet"}, "data": {"result": "processed"}}'
    mock_response.id = "test-response-id"
    
    mock_gigachat_service.client.invoke = AsyncMock(return_value=mock_response)
    mock_gigachat_service.prompt_builder.prepare_spreadsheet_prompt.return_value = "Test prompt"
    mock_gigachat_service.prompt_builder.prepare_system_prompt.return_value = "Test system prompt"
    
    result, metadata = await spreadsheet_processor.process_spreadsheet(
        "Test query",
        sample_spreadsheet_data
    )
    
    # Verify the result
    assert isinstance(result, dict)
    assert "worksheet" in result
    assert "data" in result
    
    # Verify the metadata
    assert metadata["success"] is True
    assert "processing_time" in metadata
    assert "input_tokens" in metadata
    assert "output_tokens" in metadata
    assert metadata["model"] == "GigaChat"
    assert metadata["request_id"] == "test-response-id"

@pytest.mark.asyncio
async def test_process_spreadsheet_invalid_json_response(spreadsheet_processor, mock_gigachat_service, sample_spreadsheet_data):
    """Test spreadsheet processing with invalid JSON response"""
    # Mock the response from GigaChat with invalid JSON
    mock_response = MagicMock()
    mock_response.content = 'Invalid JSON response'
    mock_response.id = "test-response-id"
    
    mock_gigachat_service.client.invoke = AsyncMock(return_value=mock_response)
    mock_gigachat_service.prompt_builder.prepare_spreadsheet_prompt.return_value = "Test prompt"
    mock_gigachat_service.prompt_builder.prepare_system_prompt.return_value = "Test system prompt"
    
    result, metadata = await spreadsheet_processor.process_spreadsheet(
        "Test query",
        sample_spreadsheet_data
    )
    
    # Verify the result is wrapped in spreadsheet format
    assert isinstance(result, dict)
    assert "metadata" in result
    assert "worksheet" in result
    assert "data" in result
    assert result["data"] == {"response": "Invalid JSON response"}

@pytest.mark.asyncio
async def test_process_spreadsheet_gigachat_error(spreadsheet_processor, mock_gigachat_service, sample_spreadsheet_data):
    """Test spreadsheet processing when GigaChat returns an error"""
    # Mock GigaChat to raise an exception
    mock_gigachat_service.client.invoke = AsyncMock(side_effect=Exception("GigaChat error"))
    mock_gigachat_service.prompt_builder.prepare_spreadsheet_prompt.return_value = "Test prompt"
    mock_gigachat_service.prompt_builder.prepare_system_prompt.return_value = "Test system prompt"
    
    # Verify that the exception is raised
    with pytest.raises(Exception, match="GigaChat error"):
        await spreadsheet_processor.process_spreadsheet(
            "Test query",
            sample_spreadsheet_data
        )