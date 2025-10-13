"""
Chart Intelligence Service
AI-driven chart generation with structured response parsing
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.models.api.chart import (
    ChartResultResponse, ChartConfig, ChartData, ChartType
)
from app.services.chart.prompt_builder import chart_prompt_builder
from app.services.chart.formatter import response_formatter_service
from app.services.chart.validation import chart_validation_service


class ChartIntelligenceService:
    """Service for AI-driven chart generation and recommendations"""
    
    def __init__(self):
        """Initialize the chart intelligence service"""
        self.prompt_builder = chart_prompt_builder
        self.formatter = response_formatter_service
        self.validator = chart_validation_service
        self._gigachat_service = None  # Will be injected when available
    
    def set_gigachat_service(self, gigachat_service):
        """
        Set the GigaChat service instance
        
        Args:
            gigachat_service: GigaChat service instance
        """
        self._gigachat_service = gigachat_service
        logger.info("GigaChat service injected into ChartIntelligenceService")
    
    async def generate_chart_response(
        self, 
        chart_data: ChartData,
        query_text: str,
        preferences: Optional[Dict] = None,
        max_retries: int = 3
    ) -> ChartResultResponse:
        """
        Generate structured chart response using AI
        
        Args:
            chart_data: Source data for chart generation
            query_text: Natural language instruction
            preferences: Optional user preferences
            max_retries: Maximum number of retry attempts
            
        Returns:
            ChartResultResponse with generated chart configuration
        """
        start_time = datetime.now()
        
        try:
            # Validate input data
            is_valid, errors = self.validator.validate_chart_data(chart_data)
            if not is_valid:
                logger.error(f"Invalid chart data: {errors}")
                return self.formatter.format_error_response(
                    Exception(f"Invalid chart data: {', '.join(errors)}")
                )
            
            # Analyze data pattern
            data_pattern = self.analyze_data_pattern(chart_data)
            logger.info(f"Detected data pattern: {data_pattern}")
            
            # Recommend chart type if not specified
            if not chart_data.chart_type:
                chart_type = self.recommend_chart_type_from_pattern(data_pattern)
            else:
                chart_type = chart_data.chart_type
            
            # Select best template
            template = self.prompt_builder.select_best_template(
                query_text,
                chart_type=chart_type,
                data_pattern=data_pattern
            )
            
            # Build prompt
            chart_data_dict = {
                "data_range": chart_data.data_range,
                "chart_data": [
                    {
                        "name": series.name,
                        "values": series.values,
                        "format": series.format
                    }
                    for series in chart_data.chart_data
                ],
                "chart_type": chart_data.chart_type,
                "query_text": query_text
            }
            
            prompt = self.prompt_builder.build_prompt(
                query_text,
                chart_data_dict,
                template
            )
            
            # Call AI with retry logic
            ai_response = await self._call_ai_with_retry(prompt, max_retries)
            
            # Parse AI response
            response = self.parse_ai_response(ai_response)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update processing time in response
            if response.processing_time is None or response.processing_time == 0.0:
                response.processing_time = processing_time
            
            # Validate generated response
            is_valid, validation_errors = self.validator.validate_response(response)
            if not is_valid:
                logger.warning(f"Generated response has validation errors: {validation_errors}")
                # Still return the response but log warnings
            
            logger.info(f"Chart response generated successfully in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Error generating chart response: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            error_response = self.formatter.format_error_response(e)
            error_response.processing_time = processing_time
            return error_response
    
    def analyze_data_pattern(self, chart_data: ChartData) -> str:
        """
        Analyze data pattern to recommend appropriate chart type
        
        Args:
            chart_data: Chart data to analyze
            
        Returns:
            Data pattern type: time_series, categorical, multi_series, statistical
        """
        if not chart_data.chart_data:
            return 'unknown'
        
        # Check for time series
        first_series = chart_data.chart_data[0]
        if first_series.format and 'date' in first_series.format.lower():
            return 'time_series'
        
        # Check for multiple y-series (multi-series)
        if len(chart_data.chart_data) > 2:
            return 'multi_series'
        
        # Check for numerical distribution (statistical)
        if len(chart_data.chart_data) == 2:
            # Check if values are numerical
            try:
                second_series = chart_data.chart_data[1]
                numeric_count = sum(1 for v in second_series.values if isinstance(v, (int, float)))
                if numeric_count / len(second_series.values) > 0.8:
                    # Check if it's categorical comparison
                    first_series_values = first_series.values
                    if all(isinstance(v, str) for v in first_series_values):
                        return 'categorical'
                    else:
                        return 'statistical'
            except:
                pass
        
        return 'categorical'
    
    def recommend_chart_type_from_pattern(self, data_pattern: str) -> str:
        """
        Recommend chart type based on data pattern
        
        Args:
            data_pattern: Detected data pattern
            
        Returns:
            Recommended chart type
        """
        pattern_to_chart = {
            'time_series': 'line',
            'categorical': 'column',
            'multi_series': 'column',
            'statistical': 'scatter'
        }
        
        recommended = pattern_to_chart.get(data_pattern, 'column')
        logger.info(f"Recommended chart type '{recommended}' for pattern '{data_pattern}'")
        return recommended
    
    async def _call_ai_with_retry(
        self, 
        prompt: str, 
        max_retries: int = 3
    ) -> str:
        """
        Call AI API with retry logic
        
        Args:
            prompt: Prompt to send to AI
            max_retries: Maximum number of retries
            
        Returns:
            AI response string
        """
        if not self._gigachat_service:
            logger.error("GigaChat service not available")
            raise Exception("GigaChat service not configured")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling AI (attempt {attempt + 1}/{max_retries})")
                
                # Check rate limit
                if not self._gigachat_service._check_rate_limit():
                    if attempt < max_retries - 1:
                        logger.warning("Rate limit exceeded, waiting before retry...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise Exception("Rate limit exceeded")
                
                # Import message classes
                from langchain_core.messages import HumanMessage, SystemMessage
                
                # Prepare messages
                messages = [
                    SystemMessage(content=self.prompt_builder.load_system_prompt()),
                    HumanMessage(content=prompt)
                ]
                
                # Call AI
                response = await asyncio.to_thread(
                    self._gigachat_service.client.invoke,
                    messages
                )
                
                # Add request time for rate limiting
                self._gigachat_service._add_request_time()
                
                return response.content
                
            except Exception as e:
                logger.error(f"AI call attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(f"AI call failed after {max_retries} attempts: {e}")
        
        raise Exception("AI call failed")
    
    def parse_ai_response(self, ai_response: str) -> ChartResultResponse:
        """
        Parse AI response into ChartResultResponse object
        
        Args:
            ai_response: Raw AI response string
            
        Returns:
            Parsed ChartResultResponse
        """
        try:
            # Parse JSON from AI response
            response_dict = self.formatter.parse_ai_response(ai_response)
            
            if not response_dict:
                logger.error("Failed to parse AI response as JSON")
                return self.formatter.format_error_response(
                    Exception("Invalid AI response format")
                )
            
            # Create response from dict
            response = self.formatter.create_response_from_dict(response_dict)
            
            # Estimate tokens used (rough estimate: 1 token ≈ 4 characters)
            if response.tokens_used is None or response.tokens_used == 0:
                estimated_tokens = len(ai_response) // 4
                response.tokens_used = estimated_tokens
            
            return response
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self.formatter.format_error_response(e)
    
    def generate_chart_config(
        self,
        chart_data: ChartData,
        chart_type: ChartType,
        title: str,
        preferences: Optional[Dict] = None
    ) -> ChartConfig:
        """
        Generate basic chart configuration without AI
        (fallback method for when AI is unavailable)
        
        Args:
            chart_data: Source data
            chart_type: Type of chart to generate
            title: Chart title
            preferences: Optional user preferences
            
        Returns:
            ChartConfig object
        """
        from app.models.api.chart import (
            SeriesConfig, ChartPosition, ChartStyling,
            ColorScheme, LegendPosition, BorderStyle
        )
        
        # Create series config
        y_columns = list(range(1, len(chart_data.chart_data)))
        series_names = [series.name for series in chart_data.chart_data[1:]]
        
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=y_columns,
            series_names=series_names,
            show_data_labels=len(chart_data.chart_data[0].values) < 10,
            smooth_lines=chart_type == ChartType.LINE
        )
        
        # Create position
        position = ChartPosition(
            x=400,
            y=50,
            width=600,
            height=400,
            anchor_cell="D2"
        )
        
        # Create styling
        styling = ChartStyling(
            color_scheme=ColorScheme.OFFICE,
            font_family="Arial",
            font_size=12,
            background_color=None,
            border_style=BorderStyle.NONE,
            legend_position=LegendPosition.BOTTOM
        )
        
        # Apply preferences if provided
        if preferences:
            if 'color_scheme' in preferences:
                styling.color_scheme = preferences['color_scheme']
            if 'position' in preferences:
                pos_pref = preferences['position']
                if 'x' in pos_pref:
                    position.x = pos_pref['x']
                if 'y' in pos_pref:
                    position.y = pos_pref['y']
                if 'width' in pos_pref:
                    position.width = pos_pref['width']
                if 'height' in pos_pref:
                    position.height = pos_pref['height']
        
        return ChartConfig(
            chart_type=chart_type,
            title=title,
            subtitle=None,
            series_config=series_config,
            position=position,
            styling=styling
        )


# Global instance
chart_intelligence_service = ChartIntelligenceService()
