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
from app.models.api.prompt import RequiredTableInfo
   

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
    
    def filter_spreadsheet_data_by_requirements(
        self,
        spreadsheet_data: Dict[str, Any],
        required_table_info: Optional[RequiredTableInfo]
    ) -> Dict[str, Any]:
        """
        Filter spreadsheet data based on RequiredTableInfo specification.
        
        This method optimizes the data sent to GigaChat by including only
        the components specified in required_table_info. If required_table_info
        is None, returns the full data unchanged (backward compatibility).
        
        Args:
            spreadsheet_data: Full spreadsheet data dictionary
            required_table_info: Specification of required table components (optional)
            
        Returns:
            Filtered spreadsheet data with only required components
        """
        # If no requirements specified, return full data (backward compatibility)
        if required_table_info is None:
            return spreadsheet_data
        
        # Start with base structure (always included)
        filtered_data = {
            "metadata": spreadsheet_data.get("metadata", {}),
            "worksheet": spreadsheet_data.get("worksheet", {})
        }
        
        # Get original data section
        original_data = spreadsheet_data.get("data", {})
        filtered_data_section: Dict[str, Any] = {}
        
        # Process header if requested
        if required_table_info.needs_column_headers or required_table_info.needs_header_styles:
            original_header = original_data.get("header")
            if original_header:
                filtered_header: Dict[str, Any] = {}
                
                # Include header values if requested
                if required_table_info.needs_column_headers:
                    filtered_header["values"] = original_header.get("values", [])
                    if "range" in original_header:
                        filtered_header["range"] = original_header["range"]
                
                # Include header style if requested
                if required_table_info.needs_header_styles:
                    if "style" in original_header:
                        filtered_header["style"] = original_header["style"]
                
                if filtered_header:
                    filtered_data_section["header"] = filtered_header
        
        # Process rows if requested
        if required_table_info.needs_cell_values or required_table_info.needs_cell_styles:
            original_rows = original_data.get("rows", [])
            filtered_rows = []
            
            for row in original_rows:
                filtered_row: Dict[str, Any] = {}
                
                # Include row values if requested
                if required_table_info.needs_cell_values and "values" in row:
                    filtered_row["values"] = row["values"]
                
                # Include row style if requested
                if required_table_info.needs_cell_styles and "style" in row:
                    filtered_row["style"] = row["style"]
                
                # Include range if present
                if "range" in row:
                    filtered_row["range"] = row["range"]
                
                # Only add row if it has content
                if filtered_row and ("values" in filtered_row or "style" in filtered_row):
                    filtered_rows.append(filtered_row)
            
            if filtered_rows:
                filtered_data_section["rows"] = filtered_rows
        
        # Add data section if it has content
        if filtered_data_section:
            filtered_data["data"] = filtered_data_section
        
        # Include column metadata if requested
        if required_table_info.needs_column_metadata:
            if "columns" in spreadsheet_data:
                filtered_data["columns"] = spreadsheet_data["columns"]
        
        # Include styles if any style-related data was requested
        if (required_table_info.needs_header_styles or required_table_info.needs_cell_styles):
            if "styles" in spreadsheet_data:
                # Collect referenced style IDs
                referenced_styles = set()
                
                # Check header style
                if "data" in filtered_data and "header" in filtered_data["data"]:
                    header_style = filtered_data["data"]["header"].get("style")
                    if header_style:
                        referenced_styles.add(header_style)
                
                # Check row styles
                if "data" in filtered_data and "rows" in filtered_data["data"]:
                    for row in filtered_data["data"]["rows"]:
                        row_style = row.get("style")
                        if row_style:
                            referenced_styles.add(row_style)
                
                # Filter styles to only include referenced ones
                original_styles = spreadsheet_data["styles"]
                filtered_styles = [
                    style for style in original_styles 
                    if style.get("id") in referenced_styles
                ]
                
                if filtered_styles:
                    filtered_data["styles"] = filtered_styles
        
        return filtered_data
    
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
        1. Filter data by requirements (if specified)
        2. Preprocess data (category-specific)
        3. Check rate limits
        4. Prepare prompts
        5. Validate token limits
        6. Invoke GigaChat
        7. Parse response
        8. Return result and metadata
        
        Args:
            query: Processing instruction for the AI
            category: Processing instruction category
            spreadsheet_data: Enhanced spreadsheet data in JSON format
            temperature: Temperature for generation (0.0 - 1.0)
            required_table_info: Optional specification of required table components for optimization
            
        Returns:
            Tuple[processed_result, metadata]
        """
        try:
            # Filter data by requirements if specified (optimization step)
            filtered_data = self.filter_spreadsheet_data_by_requirements(
                spreadsheet_data, required_table_info
            )
            
            # Preprocess data according to category-specific rules
            preprocessed_data = self.preprocess_data(filtered_data)
            
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
