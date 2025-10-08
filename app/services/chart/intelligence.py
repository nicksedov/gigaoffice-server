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
from app.services.error_handling import with_retry_and_fallback, ErrorContext

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
            "data_quality_score": 0.0,
            "statistical_insights": {},
            "optimization_suggestions": [],
            "complexity_score": 0.0
        }
        
        try:
            # Enhanced pattern detection with statistical analysis
            analysis["statistical_insights"] = self._perform_statistical_analysis(data_rows, headers)
            
            # Calculate complexity score
            analysis["complexity_score"] = self._calculate_data_complexity(data_rows, headers)
            
            # Basic pattern detection
            if len(headers) >= 2:
                # Check for time series patterns
                if self._is_time_series_data(headers, data_rows):
                    analysis["pattern_type"] = "time_series"
                    analysis["data_characteristics"].append("temporal_data")
                    analysis["optimization_suggestions"].extend([
                        "Consider using line or area chart for temporal trends",
                        "Ensure date/time data is properly formatted"
                    ])
                
                # Check for categorical data
                elif self._is_categorical_data(data_rows):
                    if len(headers) == 2:
                        analysis["pattern_type"] = "categorical"
                    else:
                        analysis["pattern_type"] = "multi_series"
                    analysis["data_characteristics"].append("categorical_data")
                    
                    # Add specific suggestions for categorical data
                    if len(data_rows) > 12:
                        analysis["optimization_suggestions"].append("Consider grouping categories for better readability")
                    if len(headers) > 8:
                        analysis["optimization_suggestions"].append("Too many series may clutter the chart - consider splitting")
                
                # Check for numerical correlations
                elif self._is_correlation_data(data_rows):
                    analysis["pattern_type"] = "correlation"
                    analysis["data_characteristics"].append("numerical_correlation")
                    analysis["optimization_suggestions"].append("Scatter plot ideal for showing correlation patterns")
                
                # Check for part-to-whole relationships
                elif self._is_part_to_whole_data(data_rows):
                    analysis["pattern_type"] = "part_to_whole"
                    analysis["data_characteristics"].append("proportional_data")
                    analysis["optimization_suggestions"].append("Pie or doughnut chart best for showing proportions")
                
                # Check for distribution analysis
                elif self._is_distribution_data(data_rows):
                    analysis["pattern_type"] = "distribution"
                    analysis["data_characteristics"].append("statistical_distribution")
                    analysis["optimization_suggestions"].append("Histogram or box plot ideal for distribution analysis")
                
                # Check for multi-dimensional analysis
                elif self._is_multi_dimensional_data(headers, data_rows):
                    analysis["pattern_type"] = "multi_dimensional"
                    analysis["data_characteristics"].append("multi_metric_comparison")
                    analysis["optimization_suggestions"].append("Radar chart excellent for multi-dimensional comparison")
                
                else:
                    analysis["pattern_type"] = "categorical"
                    analysis["data_characteristics"].append("general_comparison")
            
            # Data quality assessment
            analysis["data_quality_score"] = self._assess_data_quality(data_rows)
            
            # Recommend axis configuration
            x_axis, y_axes = self._recommend_axis_configuration(headers, data_rows, analysis["pattern_type"])
            analysis["recommended_x_axis"] = x_axis
            analysis["recommended_y_axes"] = y_axes
            
            # Add data quality suggestions
            if analysis["data_quality_score"] < 0.8:
                analysis["optimization_suggestions"].append("Data has missing values - consider cleaning before charting")
            
            if len(data_rows) < 3:
                analysis["optimization_suggestions"].append("Very few data points - consider collecting more data")
            
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
    
    def _is_distribution_data(self, data_rows: List[List[Any]]) -> bool:
        """Check if data is suitable for distribution analysis (histogram, box plot)"""
        if not data_rows or len(data_rows) < 5:
            return False
            
        # Check if we have numerical data suitable for statistical analysis
        for col_idx in range(min(2, len(data_rows[0]) if data_rows[0] else 0)):
            numeric_count = 0
            total_count = 0
            
            for row in data_rows:
                if len(row) > col_idx and row[col_idx] is not None:
                    total_count += 1
                    try:
                        float(row[col_idx])
                        numeric_count += 1
                    except (ValueError, TypeError):
                        continue
            
            # If we have mostly numerical data and enough data points
            if total_count >= 10 and numeric_count / total_count > 0.8:
                return True
        
        return False
    
    def _is_multi_dimensional_data(self, headers: List[str], data_rows: List[List[Any]]) -> bool:
        """Check if data is suitable for multi-dimensional analysis (radar chart)"""
        if not data_rows or len(headers) < 3:
            return False
            
        # Radar charts work well with 3-10 metrics per category
        if len(headers) > 10:
            return False
            
        # Check if we have numerical data in multiple columns
        numeric_columns = 0
        for col_idx in range(1, len(headers)):
            numeric_count = 0
            total_count = 0
            
            for row in data_rows[:10]:
                if len(row) > col_idx and row[col_idx] is not None:
                    total_count += 1
                    try:
                        float(row[col_idx])
                        numeric_count += 1
                    except (ValueError, TypeError):
                        continue
            
            if total_count > 0 and numeric_count / total_count > 0.7:
                numeric_columns += 1
        
        # Need at least 3 numeric columns for radar chart
        return numeric_columns >= 3
    
    def _perform_statistical_analysis(self, data_rows: List[List[Any]], headers: List[str]) -> Dict[str, Any]:
        """Perform statistical analysis on numerical data"""
        insights = {
            "numerical_columns": [],
            "categorical_columns": [],
            "data_ranges": {},
            "missing_value_rates": {},
            "value_distributions": {},
            "correlations": []
        }
        
        try:
            for col_idx, header in enumerate(headers):
                values = []
                missing_count = 0
                
                for row in data_rows:
                    if len(row) > col_idx:
                        value = row[col_idx]
                        if value is None or value == '':
                            missing_count += 1
                        else:
                            values.append(value)
                
                # Calculate missing value rate
                total_rows = len(data_rows)
                missing_rate = missing_count / total_rows if total_rows > 0 else 0
                insights["missing_value_rates"][header] = missing_rate
                
                # Determine if column is numerical
                numerical_values = []
                for value in values:
                    try:
                        num_val = float(value)
                        numerical_values.append(num_val)
                    except (ValueError, TypeError):
                        continue
                
                if len(numerical_values) > len(values) * 0.7:  # 70% numeric threshold
                    insights["numerical_columns"].append({
                        "index": col_idx,
                        "name": header,
                        "count": len(numerical_values),
                        "min": min(numerical_values) if numerical_values else None,
                        "max": max(numerical_values) if numerical_values else None,
                        "mean": sum(numerical_values) / len(numerical_values) if numerical_values else None
                    })
                    
                    # Store data range
                    if numerical_values:
                        insights["data_ranges"][header] = {
                            "min": min(numerical_values),
                            "max": max(numerical_values),
                            "range": max(numerical_values) - min(numerical_values)
                        }
                else:
                    insights["categorical_columns"].append({
                        "index": col_idx,
                        "name": header,
                        "unique_values": len(set(values)),
                        "total_values": len(values)
                    })
                
            # Simple correlation analysis for numerical columns
            num_cols = insights["numerical_columns"]
            if len(num_cols) >= 2:
                for i in range(len(num_cols)):
                    for j in range(i + 1, min(len(num_cols), i + 3)):  # Limit to avoid too many correlations
                        col1_idx = num_cols[i]["index"]
                        col2_idx = num_cols[j]["index"]
                        correlation = self._calculate_simple_correlation(data_rows, col1_idx, col2_idx)
                        if correlation is not None:
                            insights["correlations"].append({
                                "column1": num_cols[i]["name"],
                                "column2": num_cols[j]["name"],
                                "correlation": correlation,
                                "strength": self._interpret_correlation(correlation)
                            })
                        
        except Exception as e:
            logger.warning(f"Error in statistical analysis: {e}")
            
        return insights
    
    def _calculate_data_complexity(self, data_rows: List[List[Any]], headers: List[str]) -> float:
        """Calculate complexity score based on data characteristics"""
        if not data_rows or not headers:
            return 0.0
            
        complexity_score = 0.0
        
        # Row count factor
        row_count = len(data_rows)
        if row_count > 1000:
            complexity_score += 0.4
        elif row_count > 100:
            complexity_score += 0.3
        elif row_count > 10:
            complexity_score += 0.2
        else:
            complexity_score += 0.1
            
        # Column count factor
        col_count = len(headers)
        if col_count > 10:
            complexity_score += 0.3
        elif col_count > 5:
            complexity_score += 0.2
        else:
            complexity_score += 0.1
            
        # Data type diversity
        unique_types = set()
        for row in data_rows[:10]:  # Sample first 10 rows
            for cell in row:
                if cell is not None:
                    unique_types.add(type(cell).__name__)
        
        if len(unique_types) > 3:
            complexity_score += 0.2
        elif len(unique_types) > 1:
            complexity_score += 0.1
            
        # Missing data factor
        total_cells = row_count * col_count
        missing_cells = 0
        for row in data_rows:
            for cell in row:
                if cell is None or cell == '':
                    missing_cells += 1
                    
        missing_rate = missing_cells / total_cells if total_cells > 0 else 0
        complexity_score += missing_rate * 0.1
        
        return min(1.0, complexity_score)
    
    def _calculate_simple_correlation(self, data_rows: List[List[Any]], col1_idx: int, col2_idx: int) -> Optional[float]:
        """Calculate simple correlation between two numerical columns"""
        try:
            values1 = []
            values2 = []
            
            for row in data_rows:
                if len(row) > max(col1_idx, col2_idx):
                    try:
                        val1 = float(row[col1_idx])
                        val2 = float(row[col2_idx])
                        values1.append(val1)
                        values2.append(val2)
                    except (ValueError, TypeError):
                        continue
            
            if len(values1) < 3:  # Need at least 3 points
                return None
                
            # Simple Pearson correlation
            n = len(values1)
            sum1 = sum(values1)
            sum2 = sum(values2)
            sum1_sq = sum(x * x for x in values1)
            sum2_sq = sum(x * x for x in values2)
            sum_products = sum(x * y for x, y in zip(values1, values2))
            
            numerator = (n * sum_products) - (sum1 * sum2)
            denominator = ((n * sum1_sq - sum1 * sum1) * (n * sum2_sq - sum2 * sum2)) ** 0.5
            
            if denominator == 0:
                return None
                
            correlation = numerator / denominator
            return round(correlation, 3)
            
        except Exception:
            return None
    
    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation strength"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.8:
            return "very strong"
        elif abs_corr >= 0.6:
            return "strong"
        elif abs_corr >= 0.4:
            return "moderate"
        elif abs_corr >= 0.2:
            return "weak"
        else:
            return "very weak"
    
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
    
    @with_retry_and_fallback(
        max_attempts=3, 
        operation_name="chart_type_recommendation",
        fallback_function=lambda self, context: self._fallback_chart_recommendation(context)
    )
    async def recommend_chart_type(
        self, 
        data_source: DataSource, 
        chart_instruction: str,
        chart_preferences: Optional[Dict[str, Any]] = None,
        request_id: str = "unknown"
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
            "distribution": ChartType.HISTOGRAM,
            "statistical_analysis": ChartType.BOX_PLOT,
            "multi_dimensional": ChartType.RADAR,
            "ranking": ChartType.BAR,
            "proportional": ChartType.DOUGHNUT
        }
        
        return pattern_mapping.get(pattern_type, ChartType.COLUMN)
    
    @with_retry_and_fallback(
        max_attempts=2, 
        operation_name="chart_config_generation",
        fallback_function=lambda self, context: self._fallback_chart_config(context)
    )
    async def generate_chart_config(
        self,
        data_source: DataSource,
        chart_instruction: str,
        recommended_chart_type: ChartType,
        chart_preferences: Optional[Dict[str, Any]] = None,
        request_id: str = "unknown"
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
    
    async def optimize_chart_config(
        self,
        chart_config: ChartConfig,
        data_source: DataSource,
        optimization_goals: Optional[List[str]] = None
    ) -> ChartConfig:
        """Optimize chart configuration for better visualization"""
        
        await self._initialize()
        
        if not optimization_goals:
            optimization_goals = ["visual_clarity", "data_presentation", "r7_office_performance"]
        
        try:
            # Build optimization prompt
            prompt = chart_prompt_builder.build_chart_optimization_prompt(
                chart_config.dict(),
                data_source.dict(),
                optimization_goals
            )
            
            # Get AI optimization
            response = await self.gigachat_generate_service.generate_response(
                prompt,
                system_role=chart_prompt_builder.system_role,
                max_tokens=1500
            )
            
            # Parse AI response
            ai_result = json.loads(response.content)
            optimized_config_data = ai_result["optimized_config"]
            
            # Create optimized ChartConfig
            optimized_config = ChartConfig(
                chart_type=ChartType(optimized_config_data["chart_type"]),
                title=optimized_config_data["title"],
                subtitle=optimized_config_data.get("subtitle"),
                data_range=optimized_config_data["data_range"],
                series_config=SeriesConfig(**optimized_config_data["series_config"]),
                position=ChartPosition(**optimized_config_data["position"]),
                styling=ChartStyling(**optimized_config_data["styling"]),
                r7_office_properties=optimized_config_data.get("r7_office_properties", {})
            )
            
            return optimized_config
            
        except Exception as e:
            logger.error(f"Error optimizing chart config: {e}")
            
            # Fallback to rule-based optimization
            return self._apply_rule_based_optimization(chart_config, data_source, optimization_goals)
    
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
    
    def _apply_rule_based_optimization(
        self, 
        chart_config: ChartConfig, 
        data_source: DataSource, 
        optimization_goals: List[str]
    ) -> ChartConfig:
        """Apply rule-based optimization when AI optimization fails"""
        
        optimized_config = chart_config.copy(deep=True)
        
        try:
            # Visual clarity optimizations
            if "visual_clarity" in optimization_goals:
                optimized_config = self._optimize_for_visual_clarity(optimized_config, data_source)
            
            # Data presentation optimizations
            if "data_presentation" in optimization_goals:
                optimized_config = self._optimize_for_data_presentation(optimized_config, data_source)
            
            # R7-Office performance optimizations
            if "r7_office_performance" in optimization_goals:
                optimized_config = self._optimize_for_r7_office_performance(optimized_config, data_source)
            
            # User experience optimizations
            if "user_experience" in optimization_goals:
                optimized_config = self._optimize_for_user_experience(optimized_config, data_source)
                
        except Exception as e:
            logger.error(f"Error in rule-based optimization: {e}")
            return chart_config  # Return original if optimization fails
            
        return optimized_config
    
    def _optimize_for_visual_clarity(self, chart_config: ChartConfig, data_source: DataSource) -> ChartConfig:
        """Optimize chart for visual clarity"""
        
        # Adjust font sizes based on chart size
        if chart_config.position.width < 400:
            chart_config.styling.font_size = max(10, chart_config.styling.font_size - 2)
        elif chart_config.position.width > 800:
            chart_config.styling.font_size = min(16, chart_config.styling.font_size + 2)
        
        # Optimize colors for better contrast
        if chart_config.styling.color_scheme == ColorScheme.CUSTOM and chart_config.styling.custom_colors:
            # Ensure sufficient color contrast
            chart_config.styling.custom_colors = self._ensure_color_contrast(chart_config.styling.custom_colors)
        
        # Adjust legend position based on chart type and size
        if chart_config.chart_type in [ChartType.PIE, ChartType.DOUGHNUT]:
            chart_config.styling.legend_position = LegendPosition.RIGHT
        elif chart_config.position.height < 300:
            chart_config.styling.legend_position = LegendPosition.TOP
        
        return chart_config
    
    def _optimize_for_data_presentation(self, chart_config: ChartConfig, data_source: DataSource) -> ChartConfig:
        """Optimize chart for better data presentation"""
        
        # Enable data labels for small datasets
        if len(data_source.data_rows) <= 8:
            chart_config.series_config.show_data_labels = True
        
        # Optimize axis configuration based on data
        if chart_config.chart_type == ChartType.LINE and len(data_source.data_rows) > 20:
            chart_config.series_config.smooth_lines = True
        
        # Adjust chart size based on data complexity
        data_complexity = len(data_source.data_rows) * len(data_source.headers)
        if data_complexity > 100:
            chart_config.position.width = min(1000, chart_config.position.width + 100)
            chart_config.position.height = min(600, chart_config.position.height + 50)
        
        return chart_config
    
    def _optimize_for_r7_office_performance(self, chart_config: ChartConfig, data_source: DataSource) -> ChartConfig:
        """Optimize chart for R7-Office performance"""
        
        # Ensure dimensions are within R7-Office limits
        chart_config.position.width = min(2000, chart_config.position.width)
        chart_config.position.height = min(1500, chart_config.position.height)
        
        # Use standard fonts for better compatibility
        if chart_config.styling.font_family not in ["Arial", "Times New Roman", "Calibri"]:
            chart_config.styling.font_family = "Arial"
        
        # Simplify complex configurations
        if len(data_source.data_rows) > 500:
            chart_config.series_config.show_data_labels = False
            chart_config.styling.custom_colors = None  # Use default colors
        
        # Add R7-Office specific optimizations
        chart_config.r7_office_properties.update({
            "enable_animation": len(data_source.data_rows) < 100,  # Disable for large datasets
            "enable_3d": False,  # Keep 2D for better performance
            "print_object": True
        })
        
        return chart_config
    
    def _optimize_for_user_experience(self, chart_config: ChartConfig, data_source: DataSource) -> ChartConfig:
        """Optimize chart for user experience"""
        
        # Generate meaningful titles if not provided
        if not chart_config.title.strip() or chart_config.title == "Chart":
            chart_config.title = self._generate_smart_title(data_source, chart_config.chart_type)
        
        # Ensure proper positioning to avoid overlap
        chart_config.position.x = max(50, chart_config.position.x)
        chart_config.position.y = max(50, chart_config.position.y)
        
        # Add accessibility features
        if chart_config.chart_type in [ChartType.PIE, ChartType.DOUGHNUT]:
            chart_config.series_config.show_data_labels = True  # Important for accessibility
        
        return chart_config
    
    def _ensure_color_contrast(self, colors: List[str]) -> List[str]:
        """Ensure colors have sufficient contrast"""
        # Simple color contrast improvement
        improved_colors = []
        
        for color in colors:
            # Basic color validation and adjustment
            if color.lower() in ['#ffffff', '#f0f0f0', '#eeeeee']:  # Very light colors
                improved_colors.append('#4472C4')  # Use a standard blue
            elif color.lower() in ['#000000', '#111111', '#222222']:  # Very dark colors
                improved_colors.append('#404040')  # Use a lighter dark
            else:
                improved_colors.append(color)
        
        return improved_colors
    
    def _generate_smart_title(self, data_source: DataSource, chart_type: ChartType) -> str:
        """Generate smart title based on data and chart type"""
        
        headers = data_source.headers
        
        if len(headers) >= 2:
            if chart_type == ChartType.LINE:
                return f"{headers[1]} Over {headers[0]}"
            elif chart_type in [ChartType.PIE, ChartType.DOUGHNUT]:
                return f"{headers[1]} Distribution by {headers[0]}"
            elif chart_type == ChartType.SCATTER:
                return f"{headers[1]} vs {headers[0]}"
            elif chart_type in [ChartType.COLUMN, ChartType.BAR]:
                return f"{headers[1]} by {headers[0]}"
            elif chart_type == ChartType.HISTOGRAM:
                return f"{headers[0]} Distribution"
            elif chart_type == ChartType.RADAR:
                return f"Multi-dimensional Analysis"
            else:
                return f"{headers[1]} Analysis"
        elif len(headers) == 1:
            return f"{headers[0]} Chart"
        else:
            return f"{chart_type.value.title()} Chart"
    
    async def _fallback_chart_recommendation(self, context: ErrorContext) -> ChartRecommendation:
        """Fallback method for chart recommendation when AI service fails"""
        
        try:
            # Extract data source from context if available
            if context.additional_data and "data_source" in context.additional_data:
                data_source = DataSource(**context.additional_data["data_source"])
            else:
                # Create minimal fallback recommendation
                return ChartRecommendation(
                    primary_recommendation=DataPattern(
                        pattern_type="unknown",
                        confidence=0.5,
                        recommended_chart_type=ChartType.COLUMN,
                        reasoning="Fallback recommendation - AI service unavailable"
                    ),
                    alternative_recommendations=[],
                    data_analysis={"pattern_type": "unknown", "fallback": True},
                    generation_metadata={"fallback": True, "error": context.additional_data.get("error", "Unknown")}
                )
            
            # Use rule-based analysis
            data_analysis = await self.analyze_data_patterns(data_source)
            chart_type = self._fallback_chart_type_recommendation(data_analysis["pattern_type"])
            
            primary_rec = DataPattern(
                pattern_type=data_analysis["pattern_type"],
                confidence=0.7,
                recommended_chart_type=chart_type,
                reasoning=f"Fallback recommendation based on data pattern analysis: {data_analysis['pattern_type']}"
            )
            
            # Generate alternative recommendations
            alternatives = []
            pattern_mapping = {
                "time_series": [ChartType.AREA, ChartType.COLUMN],
                "categorical": [ChartType.BAR, ChartType.PIE],
                "correlation": [ChartType.LINE, ChartType.COLUMN],
                "part_to_whole": [ChartType.DOUGHNUT, ChartType.BAR]
            }
            
            alt_types = pattern_mapping.get(data_analysis["pattern_type"], [ChartType.BAR, ChartType.PIE])
            for alt_type in alt_types[:2]:  # Limit to 2 alternatives
                if alt_type != chart_type:
                    alternatives.append(DataPattern(
                        pattern_type=data_analysis["pattern_type"],
                        confidence=0.6,
                        recommended_chart_type=alt_type,
                        reasoning=f"Alternative fallback option for {data_analysis['pattern_type']} data"
                    ))
            
            return ChartRecommendation(
                primary_recommendation=primary_rec,
                alternative_recommendations=alternatives,
                data_analysis=data_analysis,
                generation_metadata={"fallback": True, "method": "rule_based"}
            )
            
        except Exception as e:
            logger.error(f"Fallback chart recommendation failed: {e}")
            # Ultra-safe fallback
            return ChartRecommendation(
                primary_recommendation=DataPattern(
                    pattern_type="unknown",
                    confidence=0.5,
                    recommended_chart_type=ChartType.COLUMN,
                    reasoning="Emergency fallback - column chart selected as safe default"
                ),
                alternative_recommendations=[],
                data_analysis={"pattern_type": "unknown", "emergency_fallback": True},
                generation_metadata={"emergency_fallback": True}
            )
    
    async def _fallback_chart_config(self, context: ErrorContext) -> ChartConfig:
        """Fallback method for chart configuration when AI service fails"""
        
        try:
            # Extract parameters from context
            if not context.additional_data:
                raise ValueError("No additional data provided for fallback")
            
            data_source = DataSource(**context.additional_data["data_source"])
            chart_instruction = context.additional_data.get("chart_instruction", "Chart")
            recommended_chart_type = ChartType(context.additional_data.get("recommended_chart_type", "column"))
            
            # Generate fallback configuration
            return self._generate_fallback_config(data_source, recommended_chart_type, chart_instruction)
            
        except Exception as e:
            logger.error(f"Fallback chart config generation failed: {e}")
            
            # Emergency fallback with minimal configuration
            return ChartConfig(
                chart_type=ChartType.COLUMN,
                title="Chart",
                data_range="A1:B2",
                series_config=SeriesConfig(
                    x_axis_column=0,
                    y_axis_columns=[1],
                    series_names=["Data"]
                ),
                position=ChartPosition(x=400, y=50, width=600, height=400),
                styling=ChartStyling(),
                r7_office_properties={"emergency_fallback": True}
            )

# Global instance
chart_intelligence_service = ChartIntelligenceService()