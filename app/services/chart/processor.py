"""
Chart Processor Service
Service for processing chart generation requests with GigaChat AI
"""

import time
import asyncio
from typing import Dict, Any, Tuple
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.gigachat.base import BaseGigaChatService
from app.services.gigachat.response_parser import response_parser
from app.services.chart import shared


class ChartProcessorService:
    """
    Service for processing chart generation requests with GigaChat AI.
    
    This service handles the processing of chart data using the GigaChat AI service.
    It takes chart data in a specific JSON format, sends it to GigaChat for processing,
    and returns chart configurations that can be used to generate visualizations.
    
    The service is used by the FastAPI application through the Kafka message handler
    in fastapi_config.py, which processes messages from the Kafka queue.
    """
    
    def __init__(self, gigachat_service: BaseGigaChatService):
        """
        Initialize the chart processor service.
        
        Args:
            gigachat_service: An instance of a GigaChat service (cloud, mtls, or dryrun)
        """
        self.gigachat_service = gigachat_service
    
    async def process_chart(
        self,
        query: str,
        category: str,
        chart_data: Dict[str, Any],
        temperature: float = 0.1
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Process chart generation request with GigaChat
        
        Args:
            query: User instruction for chart generation
            category: Category type (data-chart or data-histogram)
            chart_data: Input data for chart generation with range-based series
                Expected format: List of dicts with 'name', 'range', and 'format' fields
                Example:
                [
                    {"name": "Время", "range": "A2:A18", "format": "hh:mm"},
                    {"name": "Цена", "range": "B2:B18", "format": "# ##0.00"}
                ]
            temperature: Temperature for generation (0.0 - 1.0)
            
        Returns:
            Tuple[processed_result, metadata]
        """
        try:
            # Check rate limits
            if not shared.check_rate_limit(self.gigachat_service):
                raise Exception("Rate limit exceeded. Please wait before making another request.")
            
            # Prepare prompts using shared logic
            system_prompt, user_prompt = shared.prepare_prompts(
                query, category, chart_data, self.gigachat_service
            )
            
            # Count tokens
            input_tokens = shared.count_tokens(
                system_prompt, user_prompt, self.gigachat_service
            )
            
            # Validate token limit
            shared.validate_token_limit(input_tokens, self.gigachat_service)
            
            # Check if client is initialized (for dryrun mode)
            if self.gigachat_service.client is None:
                logger.error("GigaChat service is unavailable")
                raise Exception("GigaChat service is unavailable")
            
            # Prepare messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Add request time for rate limiting
            shared.add_request_time(self.gigachat_service)
            
            # Make request to GigaChat
            start_time = time.time()
            logger.info(f"Sending chart generation request to GigaChat: {query[:100]}...")
            
            response = await asyncio.to_thread(self.gigachat_service.client.invoke, messages)
            
            processing_time = time.time() - start_time
            
            # Parse response
            response_content = response.content
            output_tokens = self.gigachat_service._count_tokens(response_content)
            total_tokens = input_tokens + output_tokens
            
            self.gigachat_service.total_tokens_used += total_tokens
            
            # Parse the response as ChartConfig
            result_data = response_parser.parse_chart_data(response_content)
            
            if result_data is None:
                logger.warning("Failed to parse chart configuration from response")
                # Return empty result on parsing failure
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
                f"Chart processing completed successfully in {processing_time:.2f}s, "
                f"tokens: {total_tokens}"
            )
            
            return result_data, metadata
            
        except Exception as e:
            logger.error(f"Error processing chart data: {e}")
            raise
