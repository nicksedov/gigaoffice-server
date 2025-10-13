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
from app.models.orm.ai_request import AIRequest
from app.services.database.session import get_db
from app.services.kafka.service import kafka_service
from app.fastapi_config import security

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
        chart_json = json.dumps(chart_request.chart_data.list(), cls=DateTimeEncoder)
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=chart_request.data_range,
            query_text=chart_request.query_text,
            category=chart_request.category if chart_request.category is not None else 'data_chart',
            input_data=spreadsheet_json
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

@chart_router.get("/types")
async def get_supported_chart_types():
    """Get list of supported chart types with descriptions"""
    try:
        chart_types_info = {
            "column": {
                "name": "Column Chart",
                "description": "Best for comparing values across categories",
                "use_cases": ["Categorical comparisons", "Sales by region", "Survey responses"]
            },
            "line": {
                "name": "Line Chart", 
                "description": "Ideal for showing trends over time",
                "use_cases": ["Time series data", "Stock prices", "Temperature changes"]
            },
            "pie": {
                "name": "Pie Chart",
                "description": "Perfect for showing parts of a whole",
                "use_cases": ["Market share", "Budget allocation", "Survey results"]
            },
            "area": {
                "name": "Area Chart",
                "description": "Shows trends and proportions over time",
                "use_cases": ["Cumulative values", "Resource usage", "Population growth"]
            },
            "scatter": {
                "name": "Scatter Plot",
                "description": "Reveals correlations between variables",
                "use_cases": ["Height vs weight", "Price vs quality", "Performance analysis"]
            },
            "bar": {
                "name": "Bar Chart",
                "description": "Horizontal comparison of categories",
                "use_cases": ["Rankings", "Survey responses", "Performance metrics"]
            },
            "histogram": {
                "name": "Histogram",
                "description": "Shows distribution of numerical data",
                "use_cases": ["Age distribution", "Test scores", "Quality measurements"]
            },
            "doughnut": {
                "name": "Doughnut Chart",
                "description": "Modern alternative to pie chart",
                "use_cases": ["Resource allocation", "Category proportions", "Progress indicators"]
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
                "recommended_instruction": "Create a line chart showing sales trends over the first half of the year"
            },
            "market_share": {
                "description": "Market share distribution",
                "chart_type": "pie",
                "sample_data": {
                    "headers": ["Company", "Market Share"],
                    "data_rows": [
                        ["Company A", 35],
                        ["Company B", 28],
                        ["Company C", 20],
                        ["Company D", 17]
                    ]
                },
                "recommended_instruction": "Show market share distribution as a pie chart with percentages"
            },
            "performance_comparison": {
                "description": "Performance comparison across categories",
                "chart_type": "column",
                "sample_data": {
                    "headers": ["Department", "Q1", "Q2", "Q3", "Q4"],
                    "data_rows": [
                        ["Sales", 85, 92, 88, 95],
                        ["Marketing", 78, 85, 90, 87],
                        ["Support", 92, 89, 94, 96]
                    ]
                },
                "recommended_instruction": "Compare quarterly performance across departments using grouped columns"
            }
        }
        
        return {
            "success": True,
            "examples": examples,
            "usage_tips": [
                "Use clear, descriptive instructions for better AI recommendations",
                "Ensure data has proper headers and consistent formatting",
                "Consider your audience when choosing chart types",
                "Pie charts work best with 2-8 categories",
                "Line charts are ideal for time-based data"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting chart examples: {e}")
        raise HTTPException(status_code=500, detail=str(e))