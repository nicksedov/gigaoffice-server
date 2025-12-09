"""
Spreadsheet Processor
Universal processor for all spreadsheet categories
"""

import json
import time
import asyncio
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.orm import Session

from app.services.gigachat.base import BaseGigaChatService
from app.services.gigachat.response_parser import response_parser
from app.services.chart import shared
from app.models.api.spreadsheet import SpreadsheetData
from app.models.api.prompt import RequiredTableInfo
   

class SpreadsheetProcessor:
    """
    Universal spreadsheet processor for all categories.
    
    Handles the complete processing workflow. Data optimization is
    performed by the API layer before processing.
    """
    
    def __init__(self, gigachat_service: BaseGigaChatService, db_session: Session):
        """
        Initialize the spreadsheet processor.
        
        Args:
            gigachat_service: An instance of a GigaChat service (cloud, mtls, or dryrun)
            db_session: SQLAlchemy database session
        """
        self.gigachat_service = gigachat_service
        self.db_session = db_session
    
    def preprocess_data(self, spreadsheet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess spreadsheet data.
        
        Data optimization is handled by the API layer before Kafka messaging.
        This method simply returns the data unchanged while maintaining the
        processing workflow structure.
        
        Args:
            spreadsheet_data: Already optimized spreadsheet data dictionary
            
        Returns:
            The same spreadsheet data unchanged
        """
        logger.debug("Preprocessing spreadsheet data (pass-through)")
        return spreadsheet_data
    
    async def process_spreadsheet(
        self,
        query: str,
        category: str,
        spreadsheet_data: Dict[str, Any],
        temperature: float = 0.1,
        required_table_info: Optional[RequiredTableInfo] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Process spreadsheet data with GigaChat.
        
        This is the main entry point that orchestrates the complete processing workflow:
        1. Preprocess data (pass-through)
        2. Check rate limits
        3. Prepare prompts
        4. Validate token limits
        5. Invoke GigaChat
        6. Parse response
        7. Return result and metadata
        
        Note: Data optimization is performed by the API layer before this method is called.
        
        Args:
            query: Processing instruction for the AI
            category: Processing instruction category
            spreadsheet_data: Already optimized spreadsheet data in JSON format
            temperature: Temperature for generation (0.0 - 1.0)
            required_table_info: Optional specification (informational only, optimization already applied)
            
        Returns:
            Tuple[processed_result, metadata]
        """
        try:
            # Preprocess data (pass-through for universal processor)
            # Data is already optimized by the API layer
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
            # Use category-specific parser
            try:
                if category == "spreadsheet-assistance":
                    # For assistance category, parse text content response
                    result_data = response_parser.parse_text_content(response_content)
                else:
                    # For all other categories, parse spreadsheet data
                    result_data = response_parser.parse_spreadsheet_data(response_content)
                
                if result_data is None:
                    # If parsing returns None, create empty dict
                    result_data = {}
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as empty dict
                result_data = {}
            
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
