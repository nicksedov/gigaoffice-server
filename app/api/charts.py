"""
Chart Generation API Router
Router for chart generation with AI assistance and R7-Office compatibility
"""

import json
from typing import Any, Dict, Optional, cast
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.fastapi_config import security
from app.models.api.chart import (
    ChartConfig,
    ChartGenerationRequest,
    ChartGenerationResponse,
    ChartResultResponse,
    ChartStatusResponse,
)
from app.models.orm.ai_request import AIRequest
from app.models.types.enums import RequestStatus
from app.services.database.session import get_db
from app.services.kafka.service import kafka_service

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
@limiter.limit("30/minute")
async def process_chart_request(
    request: Request,
    chart_request: ChartGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process chart generation request asynchronously
    
    This endpoint accepts chart generation requests with range-based data series.
    The chart_data field contains series with 'range' references instead of inline values.
    
    Example request:
    {
        "data_range": "A1:C18",
        "chart_data": [
            {"name": "Время", "range": "A2:A18", "format": "hh:mm"},
            {"name": "Цена открытия", "range": "B2:B18", "format": "# ##0.00"}
        ],
        "chart_type": "data-chart",
        "query_text": "Построй график изменения величины во времени."
    }
    """
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        # Serialize chart data with range fields using Pydantic serialization
        chart_data_list = chart_request.chart_data
        # Use Pydantic's model_dump to serialize with range field
        chart_data_dicts = [series.model_dump() for series in chart_data_list]
        chart_data_json = json.dumps(chart_data_dicts, ensure_ascii=False)
        
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=chart_request.data_range,
            query_text=chart_request.query_text,
            category=chart_request.chart_type,
            input_data=chart_data_json  # Stores JSON with range field
        )
        
        db.add(db_request)
        db.commit()
        
        # Send to Kafka for processing with range-based data
        success = await kafka_service.send_request(
            request_id=request_id,
            user_id=user_id,
            query=chart_request.query_text,
            input_range=chart_request.data_range,
            category=chart_request.chart_type,
            input_data=[{"spreadsheet_data": chart_data_json}],  # Range-based data in message
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
            AIRequest.id == request_id
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
            AIRequest.id == request_id
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
                processing_time=None,
                error_details=None
            )
        
        # Parse chart configuration from result_data JSON field
        chart_config = None
        result_data = cast(Any, db_request.result_data)
        
        if result_data is not None and isinstance(result_data, dict):
            try:
                chart_config = ChartConfig(**result_data)
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
            processing_time=processing_time_value,
            error_details=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

