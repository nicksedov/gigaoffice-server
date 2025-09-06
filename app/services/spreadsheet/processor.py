"""
Spreadsheet Processor Service
Service for processing enhanced spreadsheet data with GigaChat
"""

import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from loguru import logger
from app.services.gigachat.base import BaseGigaChatService
from app.services.gigachat.response_parser import response_parser

class SpreadsheetProcessorService:
    """
    Service for processing enhanced spreadsheet data with GigaChat AI.
    
    This service handles the processing of spreadsheet data using the GigaChat AI service.
    It takes spreadsheet data in a specific JSON format, sends it to GigaChat for processing,
    and returns enhanced spreadsheet data with features like charts.
    
    The service is used by the FastAPI application through the Kafka message handler
    in fastapi_config.py, which processes messages from the Kafka queue.
    """
    
    def __init__(self, gigachat_service: BaseGigaChatService):
        """
        Initialize the spreadsheet processor service.
        
        Args:
            gigachat_service: An instance of a GigaChat service (cloud, mtls, or dryrun)
        """
        self.gigachat_service = gigachat_service
    
    async def process_spreadsheet(
        self,
        query: str,
        spreadsheet_data: Dict[str, Any],
        temperature: float = 0.1
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Process enhanced spreadsheet data with GigaChat
        
        Args:
            query: Processing instruction for the AI
            spreadsheet_data: Enhanced spreadsheet data in JSON format
            temperature: Temperature for generation (0.0 - 1.0)
            
        Returns:
            Tuple[processed_result, metadata]
            
        The spreadsheet_data should follow this structure:
        {
            "metadata": {
                "version": "1.0",
                "format": "enhanced-spreadsheet-data",
                "created_at": "ISO timestamp",
                "plugin_id": "gigaoffice-ai"
            },
            "worksheet": {
                "name": "Sheet1",
                "range": "A1:D10",
                "options": {
                    "auto_resize_columns": true,
                    "freeze_headers": true,
                    "auto_filter": true
                }
            },
            "data": [
                // Array of row data
            ],
            "columns": [
                // Column definitions with formatting
            ],
            "charts": [
                // Chart definitions
            ]
        }
        """
        try:
            # Check rate limits
            if not self.gigachat_service._check_rate_limit():
                raise Exception("Rate limit exceeded. Please wait before making another request.")
            
            # Prepare the prompt specifically for spreadsheet data
            user_prompt = self.gigachat_service.prompt_builder.prepare_spreadsheet_prompt(
                query, spreadsheet_data
            )
            
            system_prompt = self.gigachat_service.prompt_builder.prepare_system_prompt('spreadsheet')
            
            # Count tokens
            input_tokens = self.gigachat_service._count_tokens(system_prompt + user_prompt)
            if input_tokens > self.gigachat_service.max_tokens_per_request:
                raise Exception(f"Input too long: {input_tokens} tokens (max: {self.gigachat_service.max_tokens_per_request})")
            
            # Prepare messages
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Add request time for rate limiting
            self.gigachat_service._add_request_time()
            
            # Make request to GigaChat
            start_time = time.time()
            logger.info(f"Sending spreadsheet processing request to GigaChat: {query[:100]}...")
            
            response = await asyncio.to_thread(self.gigachat_service.client.invoke, messages)
            
            processing_time = time.time() - start_time
            
            # Parse response
            response_content = response.content
            output_tokens = self.gigachat_service._count_tokens(response_content)
            total_tokens = input_tokens + output_tokens
            
            self.gigachat_service.total_tokens_used += total_tokens
            
            # Try to parse the response as JSON
            try:
                result_data = json.loads(response_content)
                # Validate that this is spreadsheet data
                if not isinstance(result_data, dict) or "worksheet" not in result_data:
                    # If not valid spreadsheet data, wrap in a basic structure
                    result_data = {
                        "metadata": {
                            "version": "1.0",
                            "format": "enhanced-spreadsheet-data",
                            "created_at": datetime.now().isoformat(),
                            "plugin_id": "gigaoffice-ai"
                        },
                        "worksheet": {
                            "name": "Sheet1",
                            "range": "A1",
                            "options": {
                                "auto_resize_columns": True,
                                "freeze_headers": True,
                                "auto_filter": True
                            }
                        },
                        "data": response_content,
                        "columns": [],
                        "charts": []
                    }
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as text response
                result_data = {
                    "metadata": {
                        "version": "1.0",
                        "format": "enhanced-spreadsheet-data",
                        "created_at": datetime.now().isoformat(),
                        "plugin_id": "gigaoffice-ai"
                    },
                    "worksheet": {
                        "name": "Sheet1",
                        "range": "A1",
                        "options": {
                            "auto_resize_columns": True,
                            "freeze_headers": True,
                            "auto_filter": True
                        }
                    },
                    "data": {"response": response_content},
                    "columns": [],
                    "charts": []
                }
            
            # Prepare metadata
            metadata = {
                "processing_time": processing_time,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "model": self.gigachat_service.model,
                "timestamp": datetime.now().isoformat(),
                "request_id": getattr(response, 'id', None),
                "success": True
            }
            
            logger.info(
                f"Spreadsheet processing completed successfully in {processing_time:.2f}s, "
                f"tokens: {total_tokens}"
            )
            
            return result_data, metadata
            
        except Exception as e:
            logger.error(f"Error processing spreadsheet data: {e}")
            raise

# Factory function to create processor
def create_spreadsheet_processor(gigachat_service):
    """
    Create a spreadsheet processor with the given GigaChat service.
    
    This factory function is used in fastapi_config.py to create the spreadsheet processor
    that is used by the Kafka message handler to process spreadsheet requests.
    
    Args:
        gigachat_service: An instance of a GigaChat service (cloud, mtls, or dryrun)
        
    Returns:
        SpreadsheetProcessorService: An instance of the spreadsheet processor service
    """
    return SpreadsheetProcessorService(gigachat_service)