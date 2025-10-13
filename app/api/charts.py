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
    ChartGenerationRequest, ChartGenerationResponse, 
    ChartStatusResponse, ChartResultResponse,
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
        
        # Prepare input_data for chart generation
        input_data_payload = {
            "chart_request": chart_request.dict(),
            "processing_type": "chart_generation"
        }
        
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=chart_request.data_source.data_range,
            query_text=chart_request.chart_instruction,
            category="chart_generation",
            input_data=input_data_payload
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
            input_data=[input_data_payload],
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
        db_request = db.query(AIRequest).filter(
            AIRequest.id == request_id,
            AIRequest.category == "chart_generation"
        ).first()
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
        db_request = db.query(AIRequest).filter(
            AIRequest.id == request_id,
            AIRequest.category == "chart_generation"
        ).first()
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
        
        # Parse chart configuration from result_data JSON field
        chart_config = None
        result_data = cast(Any, db_request.result_data)
        
        if result_data is not None and isinstance(result_data, dict):
            try:
                # Extract chart_config from result_data
                chart_config_data = result_data.get("chart_config")
                
                if chart_config_data:
                    if isinstance(chart_config_data, str):
                        chart_config_data = json.loads(chart_config_data)
                    chart_config = ChartConfig(**chart_config_data)
                    
            except Exception as e:
                logger.warning(f"Could not parse chart configuration from result_data: {e}")
        
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

