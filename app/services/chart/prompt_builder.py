"""
Chart Generation Prompt Builder
Specialized prompts for chart generation with GigaChat integration
"""

import json
from typing import Dict, Any, List, Optional
from loguru import logger

class ChartPromptBuilder:
    """Builder for chart generation prompts with GigaChat"""
    
    def __init__(self):
        self.system_role = self._build_system_role()
    
    def _build_system_role(self) -> str:
        """Build the system role prompt for chart generation"""
        return """You are a Chart Generation Assistant for R7-Office, an expert in data visualization and chart creation.

Your responsibilities:
1. Analyze data patterns and structure to recommend optimal chart types
2. Generate R7-Office compatible chart configurations
3. Provide intelligent chart type recommendations based on data characteristics
4. Create properly formatted chart specifications with styling and positioning

You have deep knowledge of:
- R7-Office API chart parameters and compatibility
- Data visualization best practices
- Chart type selection for different data patterns
- Professional chart styling and layout

Always respond with valid JSON containing chart configuration and recommendations."""

    def build_chart_analysis_prompt(
        self, 
        data_source: Dict[str, Any], 
        chart_instruction: str,
        chart_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for chart type analysis and recommendation"""
        
        # Analyze data structure
        headers = data_source.get('headers', [])
        data_rows = data_source.get('data_rows', [])
        column_types = data_source.get('column_types', {})
        
        # Build data analysis section
        data_info = {
            "headers": headers,
            "row_count": len(data_rows),
            "column_count": len(headers),
            "column_types": column_types,
            "sample_data": data_rows[:3] if data_rows else []  # First 3 rows as sample
        }
        
        # Build preferences section
        preferences_text = ""
        if chart_preferences:
            preferences_text = f"\nUser Preferences: {json.dumps(chart_preferences, indent=2)}"
        
        prompt = f"""
Task: Analyze data and generate chart recommendation

Data Analysis:
{json.dumps(data_info, indent=2)}

User Instruction: "{chart_instruction}"{preferences_text}

Please analyze this data and provide:

1. DATA_PATTERN_ANALYSIS:
   - Identify data patterns (time series, categorical comparison, part-to-whole, correlation, distribution)
   - Determine data relationships and characteristics
   - Assess data suitability for different chart types

2. CHART_TYPE_RECOMMENDATION:
   - Primary recommendation with confidence score (0-1)
   - Alternative recommendations with rationale
   - Explanation for each recommendation

3. CHART_CONFIGURATION:
   - Optimal data series configuration (x-axis, y-axis columns)
   - Suggested chart title and styling
   - R7-Office compatible positioning and sizing

Respond with JSON in this exact format:
{{
    "data_analysis": {{
        "pattern_type": "time_series|categorical|part_to_whole|correlation|distribution|multi_series",
        "data_characteristics": ["characteristic1", "characteristic2"],
        "recommended_x_axis": 0,
        "recommended_y_axes": [1],
        "data_quality_score": 0.95
    }},
    "primary_recommendation": {{
        "chart_type": "column|line|pie|area|scatter|histogram|box_plot|bar|doughnut|radar",
        "confidence": 0.95,
        "reasoning": "Explanation for this recommendation"
    }},
    "alternative_recommendations": [
        {{
            "chart_type": "alternative_type",
            "confidence": 0.80,
            "reasoning": "Explanation for alternative"
        }}
    ],
    "chart_config": {{
        "title": "Suggested Chart Title",
        "chart_type": "recommended_type",
        "series_config": {{
            "x_axis_column": 0,
            "y_axis_columns": [1],
            "series_names": ["Series 1"],
            "show_data_labels": false
        }},
        "position": {{
            "x": 400,
            "y": 50,
            "width": 600,
            "height": 400
        }},
        "styling": {{
            "color_scheme": "office",
            "font_family": "Arial",
            "font_size": 12,
            "legend_position": "bottom"
        }}
    }}
}}"""
        
        return prompt

    def build_chart_generation_prompt(
        self,
        data_source: Dict[str, Any],
        chart_instruction: str,
        recommended_chart_type: str,
        chart_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for specific chart generation"""
        
        headers = data_source.get('headers', [])
        data_rows = data_source.get('data_rows', [])
        
        preferences_text = ""
        if chart_preferences:
            preferences_text = f"\nUser Preferences: {json.dumps(chart_preferences, indent=2)}"
            
        prompt = f"""
Task: Generate detailed R7-Office chart configuration

Chart Type: {recommended_chart_type}
Data Headers: {headers}
Data Rows: {len(data_rows)}
User Instruction: "{chart_instruction}"{preferences_text}

Generate a complete R7-Office compatible chart configuration including:

1. CHART_PROPERTIES:
   - Chart type and subtype
   - Title and subtitle
   - Data range specification

2. SERIES_CONFIGURATION:
   - X-axis and Y-axis column mapping
   - Series names and labels
   - Data label settings

3. POSITIONING:
   - Chart position (x, y coordinates)
   - Chart dimensions (width, height)
   - Optimal placement to avoid data overlap

4. STYLING:
   - Color scheme selection
   - Font settings
   - Legend positioning
   - Border and background options

5. R7_OFFICE_PROPERTIES:
   - API-specific parameters
   - Compatibility settings
   - Custom properties

Respond with JSON in this exact format:
{{
    "chart_config": {{
        "chart_type": "{recommended_chart_type}",
        "title": "Generated Chart Title",
        "subtitle": null,
        "data_range": "A1:B{len(data_rows) + 1}",
        "series_config": {{
            "x_axis_column": 0,
            "y_axis_columns": [1],
            "series_names": ["Series Name"],
            "show_data_labels": false,
            "smooth_lines": false
        }},
        "position": {{
            "x": 450,
            "y": 50,
            "width": 600,
            "height": 400,
            "anchor_cell": null
        }},
        "styling": {{
            "color_scheme": "office",
            "font_family": "Arial", 
            "font_size": 12,
            "background_color": null,
            "border_style": "none",
            "legend_position": "bottom",
            "custom_colors": null
        }},
        "r7_office_properties": {{
            "api_version": "1.0",
            "chart_object_name": "Chart1",
            "enable_animation": true,
            "enable_3d": false
        }}
    }},
    "generation_metadata": {{
        "confidence": 0.95,
        "processing_notes": ["Note about generation"],
        "optimization_applied": ["optimization1", "optimization2"]
    }}
}}"""
        
        return prompt

    def build_chart_validation_prompt(self, chart_config: Dict[str, Any]) -> str:
        """Build prompt for chart configuration validation"""
        
        prompt = f"""
Task: Validate R7-Office chart configuration

Chart Configuration:
{json.dumps(chart_config, indent=2)}

Please validate this chart configuration for:

1. R7-OFFICE_COMPATIBILITY:
   - Check all parameters are valid for R7-Office API
   - Verify chart type is supported
   - Validate positioning and sizing parameters

2. DATA_CONSISTENCY:
   - Verify column references are valid
   - Check data range format
   - Validate series configuration

3. STYLING_VALIDATION:
   - Check color values are properly formatted
   - Verify font settings are valid
   - Validate legend and border settings

4. BEST_PRACTICES:
   - Chart sizing appropriateness
   - Color scheme effectiveness
   - Layout optimization

Respond with JSON in this format:
{{
    "validation_result": {{
        "is_valid": true,
        "is_r7_office_compatible": true,
        "validation_errors": [],
        "compatibility_warnings": [],
        "best_practice_suggestions": []
    }},
    "recommendations": {{
        "suggested_improvements": [],
        "alternative_configurations": []
    }}
}}"""
        
        return prompt

    def build_chart_optimization_prompt(
        self,
        chart_config: Dict[str, Any],
        data_source: Dict[str, Any],
        optimization_goals: List[str]
    ) -> str:
        """Build prompt for chart configuration optimization"""
        
        prompt = f"""
Task: Optimize chart configuration for better visualization

Current Chart Configuration:
{json.dumps(chart_config, indent=2)}

Data Context:
- Headers: {data_source.get('headers', [])}
- Rows: {len(data_source.get('data_rows', []))}

Optimization Goals: {optimization_goals}

Please optimize the chart configuration considering:

1. VISUAL_CLARITY:
   - Improve readability and visual appeal
   - Optimize color schemes and contrast
   - Enhance typography and spacing

2. DATA_PRESENTATION:
   - Maximize data comprehension
   - Improve axis labeling and scaling
   - Optimize legend placement

3. R7_OFFICE_PERFORMANCE:
   - Ensure efficient rendering
   - Minimize resource usage
   - Optimize for various screen sizes

4. USER_EXPERIENCE:
   - Improve accessibility
   - Enhance interactive elements
   - Optimize for presentation context

Respond with optimized configuration and explanation:
{{
    "optimized_config": {{
        // Complete optimized chart configuration
    }},
    "optimization_summary": {{
        "changes_made": ["change1", "change2"],
        "improvements": ["improvement1", "improvement2"],
        "performance_impact": "positive|neutral|negative"
    }}
}}"""
        
        return prompt

# Global instance for the chart prompt builder
chart_prompt_builder = ChartPromptBuilder()