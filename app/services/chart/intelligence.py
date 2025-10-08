"""
Chart Type Intelligence Service
AI service for analyzing data patterns and recommending optimal chart types
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from app.models.api.chart import (
    ChartType, DataPattern, ChartRecommendation, DataSource,
    ChartConfig, ChartPosition, ChartStyling, SeriesConfig
)
from app.services.chart.prompt_builder import chart_prompt_builder
from app.services.gigachat.factory import create_gigachat_services

class ChartIntelligenceService:
    """Service for intelligent chart type recommendation and generation"""
    
    def __init__(self):
        # Initialize GigaChat services
        self.gigachat_classify_service = None
        self.gigachat_generate_service = None
        self._initialized = False
    
    async def _initialize(self):
        """Initialize GigaChat services if not already done"""
        if not self._initialized:
            from app.services.gigachat.prompt_builder import prompt_builder
            self.gigachat_classify_service, self.gigachat_generate_service = create_gigachat_services(prompt_builder)
            self._initialized = True
    
    async def analyze_data_patterns(self, data_source: DataSource) -> Dict[str, Any]:
        """Analyze data to identify patterns and characteristics"""
        
        headers = data_source.headers
        data_rows = data_source.data_rows
        column_types = data_source.column_types
        
        analysis = {
            "pattern_type": "unknown",
            "data_characteristics": [],
            "recommended_x_axis": 0,
            "recommended_y_axes": [1] if len(headers) > 1 else [0],
            "data_quality_score": 0.0
        }
        
        try:
            # Basic pattern detection
            if len(headers) >= 2:
                # Check for time series patterns
                if self._is_time_series_data(headers, data_rows):
                    analysis["pattern_type"] = "time_series"
                    analysis["data_characteristics"].append("temporal_data")
                
                # Check for categorical data
                elif self._is_categorical_data(data_rows):
                    if len(headers) == 2:
                        analysis["pattern_type"] = "categorical"
                    else:
                        analysis["pattern_type"] = "multi_series"
                    analysis["data_characteristics"].append("categorical_data")
                
                # Check for numerical correlations
                elif self._is_correlation_data(data_rows):
                    analysis["pattern_type"] = "correlation"
                    analysis["data_characteristics"].append("numerical_correlation")
                
                # Check for part-to-whole relationships
                elif self._is_part_to_whole_data(data_rows):
                    analysis["pattern_type"] = "part_to_whole"
                    analysis["data_characteristics"].append("proportional_data")
                
                else:
                    analysis["pattern_type"] = "categorical"
                    analysis["data_characteristics"].append("general_comparison")
            
            # Data quality assessment
            analysis["data_quality_score"] = self._assess_data_quality(data_rows)
            
            # Recommend axis configuration
            x_axis, y_axes = self._recommend_axis_configuration(headers, data_rows, analysis["pattern_type"])
            analysis["recommended_x_axis"] = x_axis
            analysis["recommended_y_axes"] = y_axes
            
        except Exception as e:
            logger.error(f"Error analyzing data patterns: {e}")
            
        return analysis
    
    def _is_time_series_data(self, headers: List[str], data_rows: List[List[Any]]) -> bool:
        """Check if data represents time series"""
        if not data_rows or len(headers) < 2:
            return False
            
        # Check if first column contains date/time-like data
        first_column = [row[0] if row else None for row in data_rows[:5]]
        
        # Simple heuristics for time data detection
        time_indicators = ['date', 'time', 'year', 'month', 'day', 'week']
        header_has_time = any(indicator in headers[0].lower() for indicator in time_indicators)
        
        # Check if values look like dates/times
        data_looks_temporal = False
        for value in first_column:
            if value and isinstance(value, str):
                # Simple check for date-like patterns
                if any(char.isdigit() for char in value) and ('/' in value or '-' in value or ':' in value):
                    data_looks_temporal = True
                    break
        
        return header_has_time or data_looks_temporal
    
    def _is_categorical_data(self, data_rows: List[List[Any]]) -> bool:
        """Check if data is primarily categorical"""
        if not data_rows:
            return False
            
        # Check first column for categorical indicators
        first_column = [row[0] if row else None for row in data_rows[:10]]
        
        # Count string vs numeric values
        string_count = sum(1 for value in first_column if isinstance(value, str))
        total_count = len([v for v in first_column if v is not None])
        
        return total_count > 0 and string_count / total_count > 0.5
    
    def _is_correlation_data(self, data_rows: List[List[Any]]) -> bool:
        """Check if data shows correlation patterns"""
        if not data_rows or len(data_rows[0]) < 2:
            return False
            
        # Check if we have primarily numerical data in multiple columns
        numeric_columns = 0
        for col_idx in range(min(3, len(data_rows[0]))):  # Check up to 3 columns
            numeric_count = 0
            total_count = 0
            
            for row in data_rows[:10]:  # Sample first 10 rows
                if len(row) > col_idx and row[col_idx] is not None:
                    total_count += 1
                    if isinstance(row[col_idx], (int, float)):
                        numeric_count += 1
            
            if total_count > 0 and numeric_count / total_count > 0.7:
                numeric_columns += 1
        
        return numeric_columns >= 2
    
    def _is_part_to_whole_data(self, data_rows: List[List[Any]]) -> bool:
        """Check if data represents part-to-whole relationships"""
        if not data_rows or len(data_rows[0]) < 2:
            return False
            
        # Check if second column contains values that could represent parts of a whole
        if len(data_rows) <= 8:  # Pie charts work best with limited categories
            second_column = [row[1] if len(row) > 1 and row[1] is not None else 0 for row in data_rows]
            
            # Check if values are positive numbers
            numeric_values = []
            for value in second_column:
                try:
                    num_val = float(value)
                    if num_val >= 0:
                        numeric_values.append(num_val)
                except:
                    continue
            
            # Good for pie chart if we have 2-8 positive values
            return len(numeric_values) >= 2 and len(numeric_values) <= 8
        
        return False
    
    def _assess_data_quality(self, data_rows: List[List[Any]]) -> float:
        """Assess data quality for chart generation"""
        if not data_rows:
            return 0.0
            
        # Count non-null values
        total_cells = 0
        non_null_cells = 0
        
        for row in data_rows:
            for cell in row:
                total_cells += 1
                if cell is not None and cell != '':
                    non_null_cells += 1
        
        if total_cells == 0:
            return 0.0
            
        completeness = non_null_cells / total_cells
        
        # Basic quality score based on completeness and row count
        row_count_score = min(1.0, len(data_rows) / 3)  # Optimal around 3+ rows
        
        return (completeness * 0.7) + (row_count_score * 0.3)
    
    def _recommend_axis_configuration(self, headers: List[str], data_rows: List[List[Any]], pattern_type: str) -> Tuple[int, List[int]]:
        """Recommend optimal axis configuration"""
        if len(headers) < 2:
            return 0, [0]
            
        x_axis = 0  # Default to first column for X-axis
        y_axes = list(range(1, len(headers)))  # All other columns for Y-axis
        
        # Pattern-specific recommendations
        if pattern_type == "time_series":
            x_axis = 0  # Time on X-axis
            y_axes = [1] if len(headers) > 1 else [0]
        elif pattern_type == "part_to_whole":
            x_axis = 0  # Categories on X-axis
            y_axes = [1] if len(headers) > 1 else [0]  # Values for pie chart
        elif pattern_type == "correlation":
            x_axis = 0
            y_axes = [1]  # Simple X-Y correlation
        
        return x_axis, y_axes
    
    async def recommend_chart_type(
        self, 
        data_source: DataSource, 
        chart_instruction: str,
        chart_preferences: Optional[Dict[str, Any]] = None
    ) -> ChartRecommendation:
        """Get AI-powered chart type recommendation"""
        
        await self._initialize()
        
        try:
            # Build analysis prompt
            prompt = chart_prompt_builder.build_chart_analysis_prompt(
                data_source.dict(),
                chart_instruction,
                chart_preferences
            )
            
            # Get AI recommendation
            response = await self.gigachat_classify_service.generate_response(
                prompt,
                system_role=chart_prompt_builder.system_role,
                max_tokens=2000
            )
            
            # Parse AI response
            ai_result = json.loads(response.content)
            
            # Create recommendation object
            primary_rec = DataPattern(
                pattern_type=ai_result["data_analysis"]["pattern_type"],
                confidence=ai_result["primary_recommendation"]["confidence"],
                recommended_chart_type=ChartType(ai_result["primary_recommendation"]["chart_type"]),
                reasoning=ai_result["primary_recommendation"]["reasoning"]
            )
            
            alternatives = []
            for alt in ai_result.get("alternative_recommendations", []):
                alternatives.append(DataPattern(
                    pattern_type=ai_result["data_analysis"]["pattern_type"],
                    confidence=alt["confidence"],
                    recommended_chart_type=ChartType(alt["chart_type"]),
                    reasoning=alt["reasoning"]
                ))
            
            recommendation = ChartRecommendation(
                primary_recommendation=primary_rec,
                alternative_recommendations=alternatives,
                data_analysis=ai_result["data_analysis"],
                generation_metadata={
                    "tokens_used": getattr(response, 'tokens_used', 0),
                    "processing_time": getattr(response, 'processing_time', 0.0)
                }
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting chart recommendation: {e}")
            
            # Fallback to rule-based recommendation
            data_analysis = await self.analyze_data_patterns(data_source)
            chart_type = self._fallback_chart_type_recommendation(data_analysis["pattern_type"])
            
            primary_rec = DataPattern(
                pattern_type=data_analysis["pattern_type"],
                confidence=0.7,
                recommended_chart_type=chart_type,
                reasoning="Fallback recommendation based on data pattern analysis"
            )
            
            return ChartRecommendation(
                primary_recommendation=primary_rec,
                alternative_recommendations=[],
                data_analysis=data_analysis,
                generation_metadata={"fallback": True, "error": str(e)}
            )
    
    def _fallback_chart_type_recommendation(self, pattern_type: str) -> ChartType:
        """Fallback chart type recommendation based on pattern"""
        pattern_mapping = {
            "time_series": ChartType.LINE,
            "categorical": ChartType.COLUMN,
            "part_to_whole": ChartType.PIE,
            "correlation": ChartType.SCATTER,
            "multi_series": ChartType.COLUMN,
            "distribution": ChartType.HISTOGRAM
        }
        
        return pattern_mapping.get(pattern_type, ChartType.COLUMN)
    
    async def generate_chart_config(
        self,
        data_source: DataSource,
        chart_instruction: str,
        recommended_chart_type: ChartType,
        chart_preferences: Optional[Dict[str, Any]] = None
    ) -> ChartConfig:
        """Generate complete chart configuration"""
        
        await self._initialize()
        
        try:
            # Build generation prompt
            prompt = chart_prompt_builder.build_chart_generation_prompt(
                data_source.dict(),
                chart_instruction,
                recommended_chart_type.value,
                chart_preferences
            )
            
            # Get AI-generated configuration
            response = await self.gigachat_generate_service.generate_response(
                prompt,
                system_role=chart_prompt_builder.system_role,
                max_tokens=1500
            )
            
            # Parse AI response
            ai_result = json.loads(response.content)
            chart_config_data = ai_result["chart_config"]
            
            # Create ChartConfig object
            chart_config = ChartConfig(
                chart_type=ChartType(chart_config_data["chart_type"]),
                title=chart_config_data["title"],
                subtitle=chart_config_data.get("subtitle"),
                data_range=chart_config_data["data_range"],
                series_config=SeriesConfig(**chart_config_data["series_config"]),
                position=ChartPosition(**chart_config_data["position"]),
                styling=ChartStyling(**chart_config_data["styling"]),
                r7_office_properties=chart_config_data.get("r7_office_properties", {})
            )
            
            return chart_config
            
        except Exception as e:
            logger.error(f"Error generating chart config: {e}")
            
            # Fallback to basic configuration
            return self._generate_fallback_config(data_source, recommended_chart_type, chart_instruction)
    
    def _generate_fallback_config(
        self, 
        data_source: DataSource, 
        chart_type: ChartType,
        chart_instruction: str
    ) -> ChartConfig:
        """Generate fallback chart configuration"""
        
        # Basic series configuration
        series_config = SeriesConfig(
            x_axis_column=0,
            y_axis_columns=[1] if len(data_source.headers) > 1 else [0],
            series_names=data_source.headers[1:] if len(data_source.headers) > 1 else [data_source.headers[0]],
            show_data_labels=chart_type in [ChartType.PIE, ChartType.DOUGHNUT]
        )
        
        # Basic positioning
        position = ChartPosition(x=450, y=50, width=600, height=400)
        
        # Basic styling
        styling = ChartStyling()
        
        # Generate title from instruction
        title = chart_instruction[:50] + "..." if len(chart_instruction) > 50 else chart_instruction
        if not title.strip():
            title = f"{chart_type.value.title()} Chart"
        
        return ChartConfig(
            chart_type=chart_type,
            title=title,
            data_range=data_source.data_range,
            series_config=series_config,
            position=position,
            styling=styling,
            r7_office_properties={"fallback_generated": True}
        )

# Global instance
chart_intelligence_service = ChartIntelligenceService()