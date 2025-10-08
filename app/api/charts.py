"""
Chart Generation API Router
Router for chart generation with AI assistance and R7-Office compatibility
"""

import os
import uuid
import json
from typing import Dict, Any, Optional, Union, List, cast
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from app.models.types.enums import RequestStatus
from app.models.api.chart import (
    ChartGenerationRequest, ChartValidationRequest,
    ChartGenerationResponse, ChartStatusResponse, ChartResultResponse, ChartValidationResponse,
    ChartConfig, DataSource
)
from app.models.orm.chart_request import ChartRequest
from app.services.database.session import get_db
from app.services.chart import chart_intelligence_service, chart_validation_service
from app.services.kafka.service import kafka_service
from app.fastapi_config import security
from app.services.monitoring import performance_monitor

# Import custom JSON encoder
from app.utils.json_encoder import DateTimeEncoder

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}

chart_router = APIRouter(prefix="/api/v1/charts", tags=["Chart Generation"])

@chart_router.post("/generate", response_model=ChartGenerationResponse)
@limiter.limit("10/minute")
async def generate_chart(
    request: Request,
    chart_request: ChartGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate chart with AI assistance - immediate response for simple charts"""
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        # Validate data source
        is_valid_data, data_errors = chart_validation_service.validate_data_source(chart_request.data_source)
        if not is_valid_data:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data source: {', '.join(data_errors)}"
            )
        
        # Determine processing mode based on data complexity
        data_rows_count = len(chart_request.data_source.data_rows)
        data_cols_count = len(chart_request.data_source.headers)
        is_complex = data_rows_count > 100 or data_cols_count > 10
        
        # Create database record
        chart_preferences_json = chart_request.chart_preferences.dict() if chart_request.chart_preferences else None
        r7_config_json = chart_request.r7_office_config.dict() if chart_request.r7_office_config else None
        
        db_request = ChartRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING.value,
            chart_instruction=chart_request.chart_instruction,
            data_source=chart_request.data_source.dict(),
            chart_preferences=chart_preferences_json,
            r7_office_config=r7_config_json,
            data_rows_count=data_rows_count,
            data_columns_count=data_cols_count,
            chart_complexity="complex" if is_complex else "simple"
        )
        
        db.add(db_request)
        db.commit()
        
        if is_complex:
            # Queue for asynchronous processing
            success = await kafka_service.send_request(
                request_id=request_id,
                user_id=user_id,
                query=chart_request.chart_instruction,
                input_range=chart_request.data_source.data_range,
                category="chart_generation",
                input_data=[{
                    "chart_request": chart_request.dict(),
                    "processing_type": "chart_generation"
                }],
                priority=1 if current_user and current_user.get("role") == "premium" else 0
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to queue chart generation request")
            
            # Update status to queued
            db_request.status = RequestStatus.PROCESSING.value
            db.commit()
            
            return ChartGenerationResponse(
                success=True,
                request_id=request_id,
                status="queued",
                chart_config=None,
                message="Chart generation request queued for processing",
                error_message=None
            )
        
        else:
            # Process immediately for simple charts
            try:
                # Update status to processing
                db_request.status = RequestStatus.PROCESSING.value
                db.commit()
                
                # Get AI recommendation
                recommendation = await chart_intelligence_service.recommend_chart_type(
                    chart_request.data_source,
                    chart_request.chart_instruction,
                    chart_preferences_json
                )
                
                # Generate chart configuration
                chart_config = await chart_intelligence_service.generate_chart_config(
                    chart_request.data_source,
                    chart_request.chart_instruction,
                    recommendation.primary_recommendation.recommended_chart_type,
                    chart_preferences_json
                )
                
                # Validate generated configuration
                is_valid, validation_errors = chart_validation_service.validate_chart_config(chart_config)
                is_compatible, compatibility_warnings = chart_validation_service.validate_r7_office_compatibility(chart_config)
                
                if not is_valid:
                    logger.warning(f"Generated chart config has validation errors: {validation_errors}")
                
                # Update database with results
                db_request.status = RequestStatus.COMPLETED.value
                db_request.chart_config = chart_config.dict()
                db_request.chart_type = chart_config.chart_type.value
                db_request.recommended_chart_types = [rec.dict() for rec in [recommendation.primary_recommendation] + recommendation.alternative_recommendations]
                db_request.data_analysis = recommendation.data_analysis
                db_request.confidence_score = recommendation.primary_recommendation.confidence
                db_request.tokens_used = recommendation.generation_metadata.get("tokens_used", 0)
                db_request.processing_time = recommendation.generation_metadata.get("processing_time", 0.0)
                
                db.commit()
                
                # Record metrics
                performance_monitor.record_chart_request(
                    request_id=request_id,
                    user_id=user_id,
                    chart_type=chart_config.chart_type.value,
                    data_rows_count=data_rows_count,
                    data_columns_count=data_cols_count,
                    processing_time=recommendation.generation_metadata.get("processing_time", 0.0),
                    tokens_used=db_request.tokens_used,
                    status="completed"
                )
                
                return ChartGenerationResponse(
                    success=True,
                    request_id=request_id,
                    status="completed",
                    chart_config=chart_config,
                    message="Chart generated successfully",
                    error_message=None,
                    tokens_used=db_request.tokens_used,
                    processing_time=db_request.processing_time
                )
                
            except Exception as e:
                logger.error(f"Error processing chart generation: {e}")
                
                # Update status to failed
                db_request.status = RequestStatus.FAILED.value
                db_request.error_message = str(e)
                db.commit()
                
                raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart generation endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.post("/process", response_model=ChartGenerationResponse)
@limiter.limit("10/minute")
async def process_chart_request(
    request: Request,
    chart_request: ChartGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process chart generation request asynchronously"""
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        # Validate data source
        is_valid_data, data_errors = chart_validation_service.validate_data_source(chart_request.data_source)
        if not is_valid_data:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data source: {', '.join(data_errors)}"
            )
        
        # Create database record
        chart_preferences_json = chart_request.chart_preferences.dict() if chart_request.chart_preferences else None
        r7_config_json = chart_request.r7_office_config.dict() if chart_request.r7_office_config else None
        
        db_request = ChartRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING.value,
            chart_instruction=chart_request.chart_instruction,
            data_source=chart_request.data_source.dict(),
            chart_preferences=chart_preferences_json,
            r7_office_config=r7_config_json,
            data_rows_count=len(chart_request.data_source.data_rows),
            data_columns_count=len(chart_request.data_source.headers),
            chart_complexity="async_requested"
        )
        
        db.add(db_request)
        db.commit()
        
        # Send to Kafka for processing
        success = await kafka_service.send_request(
            request_id=request_id,
            user_id=user_id,
            query=chart_request.chart_instruction,
            input_range=chart_request.data_source.data_range,
            category="chart_generation",
            input_data=[{
                "chart_request": chart_request.dict(),
                "processing_type": "chart_generation"
            }],
            priority=1 if current_user and current_user.get("role") == "premium" else 0
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue chart generation request")
        
        return ChartGenerationResponse(
            success=True,
            request_id=request_id,
            status="queued",
            chart_config=None,
            message="Chart generation request queued for processing",
            error_message=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart process endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.get("/status/{request_id}", response_model=ChartStatusResponse)
async def get_chart_status(request_id: str, db: Session = Depends(get_db)):
    """Get the processing status of a chart generation request"""
    try:
        db_request = db.query(ChartRequest).filter(ChartRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Chart request not found")
        
        # Type-safe access to ORM attributes
        status_value = cast(str, db_request.status)
        error_msg = cast(Optional[str], db_request.error_message)
        
        # Determine message based on status
        if status_value == RequestStatus.FAILED.value:
            message = error_msg or "Chart generation failed"
        elif status_value == RequestStatus.COMPLETED.value:
            message = "Chart generated successfully"
        elif status_value == RequestStatus.PROCESSING.value:
            message = "Chart generation in progress"
        else:
            message = "Chart generation request is queued"
        
        return ChartStatusResponse(
            success=status_value in [RequestStatus.COMPLETED.value, RequestStatus.PROCESSING.value],
            request_id=request_id,
            status=status_value,
            message=message,
            error_message=error_msg if status_value == RequestStatus.FAILED.value else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.get("/result/{request_id}", response_model=ChartResultResponse)
async def get_chart_result(request_id: str, db: Session = Depends(get_db)):
    """Get the result of a chart generation request"""
    try:
        db_request = db.query(ChartRequest).filter(ChartRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Chart request not found")
        
        # Type-safe access to ORM attributes
        status_value = cast(str, db_request.status)
        
        if status_value != RequestStatus.COMPLETED.value:
            message = (
                "Chart generation is still in progress"
                if status_value in [RequestStatus.PENDING.value, RequestStatus.PROCESSING.value]
                else "Chart generation failed or was cancelled"
            )
            return ChartResultResponse(
                success=False,
                status=status_value,
                message=message,
                chart_config=None,
                tokens_used=None,
                processing_time=None
            )
        
        # Parse chart configuration if available
        chart_config = None
        raw_chart_config = cast(Any, db_request.chart_config)
        
        if raw_chart_config is not None:
            try:
                if isinstance(raw_chart_config, str):
                    chart_config_data = json.loads(raw_chart_config)
                elif isinstance(raw_chart_config, dict):
                    chart_config_data = raw_chart_config
                else:
                    chart_config_data = None
                
                if chart_config_data:
                    chart_config = ChartConfig(**chart_config_data)
                    
            except Exception as e:
                logger.warning(f"Could not parse chart configuration: {e}")
        
        # Type-safe access to other attributes
        tokens_used_value = cast(Optional[int], db_request.tokens_used)
        processing_time_value = cast(Optional[float], db_request.processing_time)
        
        return ChartResultResponse(
            success=True,
            status=status_value,
            message="Chart generated successfully",
            chart_config=chart_config,
            tokens_used=tokens_used_value,
            processing_time=processing_time_value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.post("/validate", response_model=ChartValidationResponse)
async def validate_chart_config(
    validation_request: ChartValidationRequest,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Validate chart configuration for errors and R7-Office compatibility"""
    try:
        chart_config = validation_request.chart_config
        
        # Perform comprehensive validation
        validation_summary = chart_validation_service.get_validation_summary(chart_config)
        
        return ChartValidationResponse(
            success=True,
            is_valid=validation_summary["is_valid"],
            is_r7_office_compatible=validation_summary["is_r7_office_compatible"],
            validation_errors=validation_summary["validation_errors"],
            compatibility_warnings=validation_summary["compatibility_warnings"],
            message=f"Validation completed. Quality score: {validation_summary['overall_score']:.2f}"
        )
        
    except Exception as e:
        logger.error(f"Error validating chart configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.post("/optimize")
async def optimize_chart_config(
    chart_config: ChartConfig,
    data_source: DataSource,
    optimization_goals: Optional[List[str]] = Query(None, description="Optimization goals: visual_clarity, data_presentation, r7_office_performance, user_experience"),
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Optimize chart configuration for better visualization"""
    try:
        # Set default optimization goals if not provided
        if not optimization_goals:
            optimization_goals = ["visual_clarity", "data_presentation", "r7_office_performance"]
        
        # Validate input data
        is_valid_data, data_errors = chart_validation_service.validate_data_source(data_source)
        if not is_valid_data:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data source: {', '.join(data_errors)}"
            )
        
        # Optimize chart configuration
        optimized_config = await chart_intelligence_service.optimize_chart_config(
            chart_config,
            data_source,
            optimization_goals
        )
        
        # Validate optimized configuration
        is_valid, validation_errors = chart_validation_service.validate_chart_config(optimized_config)
        is_compatible, compatibility_warnings = chart_validation_service.validate_r7_office_compatibility(optimized_config)
        
        return {
            "success": True,
            "optimized_config": optimized_config,
            "optimization_goals": optimization_goals,
            "validation_summary": {
                "is_valid": is_valid,
                "is_r7_office_compatible": is_compatible,
                "validation_errors": validation_errors,
                "compatibility_warnings": compatibility_warnings
            },
            "message": "Chart configuration optimized successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing chart configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.get("/types")
async def get_supported_chart_types():
    """Get list of supported chart types with descriptions"""
    try:
        chart_types_info = {
            "column": {
                "name": "Column Chart",
                "description": "Best for comparing values across categories",
                "use_cases": ["Categorical comparisons", "Sales by region", "Survey responses"],
                "data_requirements": "Categorical X-axis, numerical Y-axis",
                "r7_office_support": "full"
            },
            "line": {
                "name": "Line Chart", 
                "description": "Ideal for showing trends over time",
                "use_cases": ["Time series data", "Stock prices", "Temperature changes"],
                "data_requirements": "Sequential X-axis (often time), numerical Y-axis",
                "r7_office_support": "full"
            },
            "pie": {
                "name": "Pie Chart",
                "description": "Perfect for showing parts of a whole",
                "use_cases": ["Market share", "Budget allocation", "Survey results"],
                "data_requirements": "Categorical labels, positive numerical values",
                "r7_office_support": "full"
            },
            "area": {
                "name": "Area Chart",
                "description": "Shows trends and proportions over time",
                "use_cases": ["Cumulative values", "Resource usage", "Population growth"],
                "data_requirements": "Sequential X-axis, numerical Y-axis",
                "r7_office_support": "full"
            },
            "scatter": {
                "name": "Scatter Plot",
                "description": "Reveals correlations between variables",
                "use_cases": ["Height vs weight", "Price vs quality", "Performance analysis"],
                "data_requirements": "Numerical X and Y axes",
                "r7_office_support": "full"
            },
            "bar": {
                "name": "Bar Chart",
                "description": "Horizontal comparison of categories",
                "use_cases": ["Rankings", "Survey responses", "Performance metrics"],
                "data_requirements": "Categorical Y-axis, numerical X-axis",
                "r7_office_support": "full"
            },
            "histogram": {
                "name": "Histogram",
                "description": "Shows distribution of numerical data",
                "use_cases": ["Age distribution", "Test scores", "Quality measurements"],
                "data_requirements": "Numerical data for binning",
                "r7_office_support": "full"
            },
            "doughnut": {
                "name": "Doughnut Chart",
                "description": "Modern alternative to pie chart",
                "use_cases": ["Resource allocation", "Category proportions", "Progress indicators"],
                "data_requirements": "Categorical labels, positive numerical values",
                "r7_office_support": "full"
            },
            "box_plot": {
                "name": "Box Plot",
                "description": "Displays data distribution with quartiles",
                "use_cases": ["Statistical analysis", "Outlier detection", "Data distribution comparison"],
                "data_requirements": "Numerical data for statistical analysis",
                "r7_office_support": "limited"
            },
            "radar": {
                "name": "Radar Chart",
                "description": "Multi-dimensional data comparison",
                "use_cases": ["Performance comparison", "Skills assessment", "Multi-metric analysis"],
                "data_requirements": "Multiple numerical metrics per category",
                "r7_office_support": "limited"
            }
        }
        
        return {
            "success": True,
            "supported_types": chart_types_info,
            "total_count": len(chart_types_info)
        }
        
    except Exception as e:
        logger.error(f"Error getting chart types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.get("/examples")
async def get_chart_examples():
    """Get example chart configurations for different use cases"""
    try:
        examples = {
            "sales_by_month": {
                "description": "Monthly sales data visualization",
                "chart_type": "line",
                "use_case": "Time series analysis",
                "complexity": "simple",
                "sample_data": {
                    "headers": ["Month", "Sales"],
                    "data_rows": [
                        ["Jan", 15000],
                        ["Feb", 18000], 
                        ["Mar", 22000],
                        ["Apr", 19000],
                        ["May", 25000],
                        ["Jun", 28000]
                    ]
                },
                "recommended_instruction": "Create a line chart showing sales trends over the first half of the year",
                "expected_config": {
                    "chart_type": "line",
                    "show_data_labels": False,
                    "smooth_lines": True,
                    "legend_position": "bottom"
                }
            },
            "market_share": {
                "description": "Market share distribution",
                "chart_type": "pie",
                "use_case": "Part-to-whole analysis",
                "complexity": "simple",
                "sample_data": {
                    "headers": ["Company", "Market Share"],
                    "data_rows": [
                        ["Company A", 35],
                        ["Company B", 28],
                        ["Company C", 20],
                        ["Company D", 17]
                    ]
                },
                "recommended_instruction": "Show market share distribution as a pie chart with percentages",
                "expected_config": {
                    "chart_type": "pie",
                    "show_data_labels": True,
                    "legend_position": "right"
                }
            },
            "performance_comparison": {
                "description": "Performance comparison across categories",
                "chart_type": "column",
                "use_case": "Multi-series comparison",
                "complexity": "medium",
                "sample_data": {
                    "headers": ["Department", "Q1", "Q2", "Q3", "Q4"],
                    "data_rows": [
                        ["Sales", 85, 92, 88, 95],
                        ["Marketing", 78, 85, 90, 87],
                        ["Support", 92, 89, 94, 96]
                    ]
                },
                "recommended_instruction": "Compare quarterly performance across departments using grouped columns",
                "expected_config": {
                    "chart_type": "column",
                    "show_data_labels": True,
                    "legend_position": "top"
                }
            },
            "correlation_analysis": {
                "description": "Correlation between two variables",
                "chart_type": "scatter",
                "use_case": "Relationship analysis",
                "complexity": "medium",
                "sample_data": {
                    "headers": ["Advertising Spend", "Sales Revenue"],
                    "data_rows": [
                        [1000, 15000],
                        [1500, 22000],
                        [2000, 28000],
                        [2500, 35000],
                        [3000, 42000],
                        [3500, 48000]
                    ]
                },
                "recommended_instruction": "Show the correlation between advertising spend and sales revenue",
                "expected_config": {
                    "chart_type": "scatter",
                    "show_data_labels": False,
                    "legend_position": "none"
                }
            },
            "age_distribution": {
                "description": "Age distribution histogram",
                "chart_type": "histogram",
                "use_case": "Statistical distribution",
                "complexity": "medium",
                "sample_data": {
                    "headers": ["Age Group", "Count"],
                    "data_rows": [
                        ["18-25", 120],
                        ["26-35", 180],
                        ["36-45", 150],
                        ["46-55", 100],
                        ["56-65", 80],
                        ["65+", 45]
                    ]
                },
                "recommended_instruction": "Create a histogram showing age distribution of survey respondents",
                "expected_config": {
                    "chart_type": "histogram",
                    "show_data_labels": True,
                    "legend_position": "none"
                }
            },
            "skill_assessment": {
                "description": "Multi-dimensional skill assessment",
                "chart_type": "radar",
                "use_case": "Multi-metric comparison",
                "complexity": "complex",
                "sample_data": {
                    "headers": ["Employee", "Communication", "Technical", "Leadership", "Creativity", "Teamwork"],
                    "data_rows": [
                        ["John", 8, 9, 6, 7, 8],
                        ["Jane", 9, 7, 8, 9, 9],
                        ["Bob", 7, 10, 5, 6, 7]
                    ]
                },
                "recommended_instruction": "Create a radar chart comparing employee skills across multiple dimensions",
                "expected_config": {
                    "chart_type": "radar",
                    "show_data_labels": False,
                    "legend_position": "bottom"
                }
            },
            "regional_sales": {
                "description": "Regional sales comparison",
                "chart_type": "bar",
                "use_case": "Categorical ranking",
                "complexity": "simple",
                "sample_data": {
                    "headers": ["Region", "Sales"],
                    "data_rows": [
                        ["North America", 45000],
                        ["Europe", 38000],
                        ["Asia Pacific", 52000],
                        ["Latin America", 28000],
                        ["Middle East", 22000]
                    ]
                },
                "recommended_instruction": "Create a horizontal bar chart showing sales by region",
                "expected_config": {
                    "chart_type": "bar",
                    "show_data_labels": True,
                    "legend_position": "none"
                }
            },
            "budget_allocation": {
                "description": "Budget allocation doughnut chart",
                "chart_type": "doughnut",
                "use_case": "Modern proportional display",
                "complexity": "simple",
                "sample_data": {
                    "headers": ["Category", "Budget"],
                    "data_rows": [
                        ["Operations", 40],
                        ["Marketing", 25],
                        ["R&D", 20],
                        ["Administration", 15]
                    ]
                },
                "recommended_instruction": "Show budget allocation as a modern doughnut chart",
                "expected_config": {
                    "chart_type": "doughnut",
                    "show_data_labels": True,
                    "legend_position": "right"
                }
            },
            "performance_metrics": {
                "description": "Performance metrics box plot",
                "chart_type": "box_plot",
                "use_case": "Statistical analysis with outliers",
                "complexity": "complex",
                "sample_data": {
                    "headers": ["Metric", "Q1", "Median", "Q3", "Min", "Max"],
                    "data_rows": [
                        ["Response Time", 120, 150, 180, 80, 250],
                        ["Accuracy", 85, 92, 96, 70, 100],
                        ["Efficiency", 75, 85, 92, 60, 98]
                    ]
                },
                "recommended_instruction": "Create a box plot showing distribution of performance metrics",
                "expected_config": {
                    "chart_type": "box_plot",
                    "show_data_labels": False,
                    "legend_position": "bottom"
                }
            },
            "cumulative_growth": {
                "description": "Cumulative growth area chart",
                "chart_type": "area",
                "use_case": "Cumulative trends",
                "complexity": "medium",
                "sample_data": {
                    "headers": ["Month", "New Users", "Returning Users"],
                    "data_rows": [
                        ["Jan", 1000, 500],
                        ["Feb", 1200, 800],
                        ["Mar", 1500, 1100],
                        ["Apr", 1800, 1400],
                        ["May", 2000, 1600],
                        ["Jun", 2200, 1800]
                    ]
                },
                "recommended_instruction": "Show cumulative user growth with stacked area chart",
                "expected_config": {
                    "chart_type": "area",
                    "show_data_labels": False,
                    "legend_position": "top"
                }
            }
        }
        
        return {
            "success": True,
            "examples": examples,
            "usage_tips": [
                "Use clear, descriptive instructions for better AI recommendations",
                "Ensure data has proper headers and consistent formatting",
                "Consider your audience when choosing chart types",
                "Pie and doughnut charts work best with 2-8 categories",
                "Line and area charts are ideal for time-based data",
                "Scatter plots are perfect for showing correlations",
                "Bar charts work well for ranking and comparisons",
                "Histograms are best for showing data distributions",
                "Radar charts excel at multi-dimensional comparisons",
                "Box plots are ideal for statistical analysis"
            ],
            "chart_selection_guide": {
                "time_series": ["line", "area"],
                "categorical_comparison": ["column", "bar"],
                "part_to_whole": ["pie", "doughnut"],
                "correlation": ["scatter"],
                "distribution": ["histogram", "box_plot"],
                "multi_dimensional": ["radar"],
                "ranking": ["bar", "column"]
            },
            "data_requirements": {
                "minimum_rows": 2,
                "maximum_rows": 10000,
                "minimum_columns": 1,
                "maximum_columns": 50,
                "supported_data_types": ["string", "number", "date", "boolean"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting chart examples: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.get("/templates")
async def get_chart_templates():
    """Get chart configuration templates for quick setup"""
    try:
        templates = {
            "basic_column": {
                "name": "Basic Column Chart",
                "description": "Simple column chart for categorical data",
                "chart_config": {
                    "chart_type": "column",
                    "title": "Column Chart",
                    "series_config": {
                        "x_axis_column": 0,
                        "y_axis_columns": [1],
                        "show_data_labels": False
                    },
                    "position": {
                        "x": 450,
                        "y": 50,
                        "width": 600,
                        "height": 400
                    },
                    "styling": {
                        "color_scheme": "office",
                        "font_family": "Arial",
                        "font_size": 12,
                        "legend_position": "bottom"
                    }
                },
                "use_cases": ["Sales comparison", "Survey results", "Performance metrics"]
            },
            "time_series_line": {
                "name": "Time Series Line Chart", 
                "description": "Line chart optimized for time-based data",
                "chart_config": {
                    "chart_type": "line",
                    "title": "Trend Analysis",
                    "series_config": {
                        "x_axis_column": 0,
                        "y_axis_columns": [1],
                        "show_data_labels": False,
                        "smooth_lines": True
                    },
                    "position": {
                        "x": 450,
                        "y": 50,
                        "width": 700,
                        "height": 400
                    },
                    "styling": {
                        "color_scheme": "modern",
                        "font_family": "Arial", 
                        "font_size": 12,
                        "legend_position": "top"
                    }
                },
                "use_cases": ["Stock prices", "Website traffic", "Temperature trends"]
            },
            "proportion_pie": {
                "name": "Proportion Pie Chart",
                "description": "Pie chart for showing parts of a whole",
                "chart_config": {
                    "chart_type": "pie",
                    "title": "Distribution Analysis",
                    "series_config": {
                        "x_axis_column": 0,
                        "y_axis_columns": [1],
                        "show_data_labels": True
                    },
                    "position": {
                        "x": 450,
                        "y": 50, 
                        "width": 500,
                        "height": 500
                    },
                    "styling": {
                        "color_scheme": "colorful",
                        "font_family": "Arial",
                        "font_size": 11,
                        "legend_position": "right"
                    }
                },
                "use_cases": ["Market share", "Budget allocation", "Survey responses"]
            }
        }
        
        return {
            "success": True,
            "templates": templates,
            "template_categories": {
                "basic": ["basic_column", "time_series_line", "proportion_pie"]
            },
            "customization_tips": [
                "Adjust position and size based on your R7-Office layout",
                "Choose color schemes that match your presentation theme",
                "Enable data labels for clearer communication"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting chart templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.get("/queue/status")
async def get_queue_status(current_user: Optional[Dict] = Depends(get_current_user)):
    """Get Kafka queue status and processing metrics"""
    try:
        # Get Kafka service info
        queue_info = kafka_service.get_queue_info()
        
        # Get processing stats
        from app.services.chart.processor import chart_processing_service
        processing_stats = chart_processing_service.get_processing_stats()
        
        # Get consumer status if available
        consumer_status = None
        try:
            from app.services.kafka.consumer import chart_kafka_consumer
            consumer_status = chart_kafka_consumer.get_consumer_status()
        except ImportError:
            logger.warning("Consumer module not available")
        
        return {
            "success": True,
            "queue_info": queue_info,
            "processing_stats": processing_stats,
            "consumer_status": consumer_status,
            "message": "Queue status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.get("/metrics")
async def get_metrics(
    time_range: int = Query(60, description="Time range in minutes for metrics"),
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Get performance metrics and system health"""
    try:
        from app.services.monitoring import performance_monitor
        
        # Get comprehensive metrics summary
        metrics_summary = performance_monitor.get_metrics_summary(time_range)
        
        return {
            "success": True,
            "metrics": metrics_summary,
            "message": f"Metrics retrieved for last {time_range} minutes"
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chart_router.get("/metrics/trends")
async def get_metrics_trends(
    hours: int = Query(24, description="Number of hours for trend analysis"),
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Get performance trends over time"""
    try:
        from app.services.monitoring import performance_monitor
        
        trends = performance_monitor.get_trends(hours)
        
        return {
            "success": True,
            "trends": trends,
            "hours": hours,
            "message": f"Trends retrieved for last {hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))