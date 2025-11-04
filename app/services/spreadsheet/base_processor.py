"""
Base Spreadsheet Processor
Abstract base class for category-specific spreadsheet processors
"""

import json
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.gigachat.base import BaseGigaChatService
from app.services.gigachat.response_parser import response_parser
from app.services.chart import shared
from app.models.api.spreadsheet import SpreadsheetData


class BaseSpreadsheetProcessor(ABC):
    """
    Abstract base class for spreadsheet processors.
    
    Defines the common processing workflow and requires subclasses
    to implement category-specific data preprocessing logic.
    """
    
    def __init__(self, gigachat_service: BaseGigaChatService):
        """
        Initialize the base spreadsheet processor.
        
        Args:
            gigachat_service: An instance of a GigaChat service (cloud, mtls, or dryrun)
        """
        self.gigachat_service = gigachat_service
    
    @abstractmethod
    def preprocess_data(self, spreadsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess spreadsheet data according to category-specific requirements.
        
        This method must be implemented by subclasses to filter and transform
        the input data, retaining only the fields relevant for the specific
        category type.
        
        Args:
            spreadsheet_data: Full spreadsheet data dictionary
            
        Returns:
            Preprocessed spreadsheet data with only relevant fields
        """
        pass
    
    async def process_spreadsheet(
        self,
        query: str,
        category: str,
        spreadsheet_data: Dict[str, Any],
        temperature: float = 0.1
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Process spreadsheet data with GigaChat.
        
        This is the main entry point that orchestrates the complete processing workflow:
        1. Preprocess data (category-specific)
        2. Check rate limits
        3. Prepare prompts
        4. Validate token limits
        5. Invoke GigaChat
        6. Parse response
        7. Return result and metadata
        
        Args:
            query: Processing instruction for the AI
            category: Processing instruction category
            spreadsheet_data: Enhanced spreadsheet data in JSON format
            temperature: Temperature for generation (0.0 - 1.0)
            
        Returns:
            Tuple[processed_result, metadata]
        """
        try:
            # Preprocess data according to category-specific rules
            preprocessed_data = self.preprocess_data(spreadsheet_data)
            
            # Check rate limits using shared logic
            if not shared.check_rate_limit(self.gigachat_service):
                raise Exception("Rate limit exceeded. Please wait before making another request.")
            
            # Prepare prompts using shared logic
            system_prompt, user_prompt = shared.prepare_prompts(
                query, category, preprocessed_data, self.gigachat_service
            )
            
            # Count tokens using shared logic
            input_tokens = shared.count_tokens(
                system_prompt, user_prompt, self.gigachat_service
            )
            
            # Validate token limit using shared logic
            shared.validate_token_limit(input_tokens, self.gigachat_service)
            
            # Check if client is initialized (for dryrun mode)
            if self.gigachat_service.client is None:
                # Handle dryrun mode
                logger.error("GigaChat service is unavailable")
                raise Exception("GigaChat service is unavailable")
            
            # Prepare messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Add request time for rate limiting using shared logic
            shared.add_request_time(self.gigachat_service)
            
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
                result_data = response_parser.parse_spreadsheet_data(response_content)
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as text response
                result_data = SpreadsheetData()
            
            # Prepare metadata using shared logic
            metadata = shared.create_metadata(
                processing_time=processing_time,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=self.gigachat_service.model,
                request_id=getattr(response, 'id', None)
            )
            
            logger.info(
                f"Spreadsheet processing completed successfully in {processing_time:.2f}s, "
                f"tokens: {total_tokens}"
            )
            
            return result_data, metadata
            
        except Exception as e:
            logger.error(f"Error processing spreadsheet data: {e}")
            raise
"""
Base Spreadsheet Processor
Abstract base class for category-specific spreadsheet processors
"""
