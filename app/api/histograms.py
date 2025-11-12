"""
Histogram Analysis API Router
Router for histogram generation with AI assistance and statistical metadata processing
"""

import os
import uuid
import json
from typing import Dict, Any, Optional, Union, List, cast
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from app.models.types.enums import RequestStatus
from app.models.api.histogram import (
    HistogramRequest,
    HistogramResponse,
    HistogramProcessResponse,
    HistogramStatusResponse,
    HistogramResultResponse
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

histogram_router = APIRouter(prefix="/api/v1/histograms", tags=["Histogram Analysis"])


@histogram_router.post("/process", response_model=HistogramProcessResponse)
@limiter.limit("30/minute")
async def process_histogram_request(
    request: Request,
    histogram_request: HistogramRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process histogram analysis request asynchronously
    
    This endpoint accepts histogram analysis requests with spreadsheet data containing
    statistical metadata (min, max, median, count) for numerical columns.
    
    The request is queued for asynchronous processing by GigaChat, which will analyze
    the data and return optimal histogram configuration recommendations.
    
    Example request:
    ```json
    {
        "spreadsheet_data": {
            "metadata": {"version": "1.0"},
            "worksheet": {"name": "Prices", "range": "A1:B100"},
            "data": {
                "header": {"values": ["Product", "Price"], "range": "A1:B1"},
                "rows": [...]
            },
            "columns": [
                {"index": 0, "format": "General", "range": "A2:A100"},
                {
                    "index": 1,
                    "format": "# ##0.00",
                    "range": "B2:B100",
                    "min": 50.0,
                    "max": 5000.0,
                    "median": 850.0,
                    "count": 99
                }
            ]
        },
        "query_text": "Построй гистограмму распределения цен",
        "category": "data-histogram"
    }
    ```
    
    Returns:
        HistogramProcessResponse with request_id for status tracking
    """
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        # Validate that spreadsheet_data contains columns with statistical metadata
        spreadsheet_data = histogram_request.spreadsheet_data
        
        # Check if columns exist and have statistical metadata
        if not isinstance(spreadsheet_data, dict):
            raise HTTPException(
                status_code=400,
                detail="spreadsheet_data must be a valid dictionary"
            )
        
        columns = spreadsheet_data.get("columns", [])
        if not columns:
            raise HTTPException(
                status_code=400,
                detail="spreadsheet_data must contain at least one column definition"
            )
        
        # Validate statistical metadata consistency for numerical columns
        for col in columns:
            if not isinstance(col, dict):
                continue
            
            # Validate range field is present
            if "range" not in col:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column {col.get('index', 'unknown')} must have a 'range' field"
                )
            
            # Validate statistical field consistency if present
            min_val = col.get("min")
            max_val = col.get("max")
            median_val = col.get("median")
            count_val = col.get("count")
            
            if min_val is not None and max_val is not None:
                if min_val > max_val:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column {col.get('index')}: min must be <= max"
                    )
            
            if median_val is not None:
                if min_val is not None and median_val < min_val:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column {col.get('index')}: median must be >= min"
                    )
                if max_val is not None and median_val > max_val:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column {col.get('index')}: median must be <= max"
                    )
            
            if count_val is not None and count_val <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column {col.get('index')}: count must be > 0"
                )
        
        # Serialize spreadsheet data including statistical metadata
        spreadsheet_json = json.dumps(spreadsheet_data, cls=DateTimeEncoder, ensure_ascii=False)
        
        # Get worksheet range for tracking
        worksheet_info = spreadsheet_data.get("worksheet", {})
        input_range = worksheet_info.get("range", "A1")
        
        # Create database record
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=input_range,
            query_text=histogram_request.query_text,
            category=histogram_request.category,
            input_data=spreadsheet_json
        )
        
        db.add(db_request)
        db.commit()
        
        # Send to Kafka for processing
        success = await kafka_service.send_request(
            request_id=request_id,
            user_id=user_id,
            query=histogram_request.query_text,
            input_range=input_range,
            category=histogram_request.category,
            input_data=[{"spreadsheet_data": spreadsheet_json}],
            priority=1 if current_user and current_user.get("role") == "premium" else 0
        )
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to queue histogram analysis request"
            )
        
        return HistogramProcessResponse(
            success=True,
            request_id=request_id,
            status="queued",
            message="Histogram analysis request queued for processing",
            error_message=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing histogram request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@histogram_router.get("/status/{request_id}", response_model=HistogramStatusResponse)
async def get_histogram_status(
    request_id: str, 
    db: Session = Depends(get_db)
):
    """Get the processing status of a histogram analysis request
    
    Poll this endpoint to check the current status of a histogram analysis request.
    
    Possible status values:
    - "pending": Request is queued and waiting to be processed
    - "processing": Request is currently being processed by GigaChat
    - "completed": Analysis completed successfully, result available
    - "failed": Analysis failed, error message available
    
    Args:
        request_id: UUID of the histogram analysis request
        
    Returns:
        HistogramStatusResponse with current status
        
    Raises:
        HTTPException: 404 if request_id not found
    """
    try:
        db_request = db.query(AIRequest).filter(
            AIRequest.id == request_id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=404, 
                detail="Histogram request not found"
            )
        
        # Type-safe access to ORM attributes
        status_value = cast(str, db_request.status)
        error_msg = cast(Optional[str], db_request.error_message)
        
        # Determine message based on status
        if status_value == RequestStatus.PENDING.value:
            message = "Histogram analysis request is queued"
        elif status_value == RequestStatus.PROCESSING.value:
            message = "Histogram analysis in progress"
        elif status_value == RequestStatus.COMPLETED.value:
            message = "Histogram analysis completed successfully"
        elif status_value == RequestStatus.FAILED.value:
            message = error_msg or "Histogram analysis failed"
        else:
            message = f"Histogram analysis status: {status_value}"
        
        return HistogramStatusResponse(
            success=status_value in [RequestStatus.COMPLETED.value, RequestStatus.PROCESSING.value],
            request_id=request_id,
            status=status_value,
            message=message,
            error_message=error_msg if status_value == RequestStatus.FAILED.value else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting histogram status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@histogram_router.get("/result/{request_id}", response_model=HistogramResultResponse)
async def get_histogram_result(
    request_id: str, 
    db: Session = Depends(get_db)
):
    """Get the result of a histogram analysis request
    
    Retrieve the completed histogram configuration generated by GigaChat.
    This endpoint should only be called after the status endpoint indicates "completed".
    
    The histogram_config contains:
    - source_columns: Indices of columns to use for histogram
    - recommended_bins: Optimal number of bins
    - range_column_name: Suggested name for bin range column (in Russian)
    - count_column_name: Suggested name for frequency count column (in Russian)
    
    Args:
        request_id: UUID of the histogram analysis request
        
    Returns:
        HistogramResultResponse with histogram configuration if completed
        
    Raises:
        HTTPException: 404 if request_id not found
    """
    try:
        db_request = db.query(AIRequest).filter(
            AIRequest.id == request_id
        ).first()
        
        if not db_request:
            raise HTTPException(
                status_code=404, 
                detail="Histogram request not found"
            )
        
        # Type-safe access to ORM attributes
        status_value = cast(str, db_request.status)
        
        # If not completed, return appropriate message
        if status_value != RequestStatus.COMPLETED.value:
            message = (
                "Histogram analysis is still in progress"
                if status_value in [RequestStatus.PENDING.value, RequestStatus.PROCESSING.value]
                else "Histogram analysis failed or was cancelled"
            )
            return HistogramResultResponse(
                success=False,
                status=status_value,
                message=message,
                histogram_config=None,
                tokens_used=None,
                processing_time=None
            )
        
        # Parse histogram configuration from result_data
        histogram_config = None
        result_data = cast(Any, db_request.result_data)
        
        if result_data is not None:
            try:
                # If result_data is a string, parse it
                if isinstance(result_data, str):
                    result_dict = json.loads(result_data)
                elif isinstance(result_data, dict):
                    result_dict = result_data
                else:
                    result_dict = None
                
                # Validate and create HistogramResponse
                if result_dict:
                    histogram_config = HistogramResponse(**result_dict)
                    
            except Exception as e:
                logger.warning(f"Could not parse histogram configuration: {e}")
        
        # Type-safe access to metrics
        tokens_used_value = cast(Optional[int], db_request.tokens_used)
        processing_time_value = cast(Optional[float], db_request.processing_time)
        
        return HistogramResultResponse(
            success=True,
            status=status_value,
            message="Histogram analysis completed successfully",
            histogram_config=histogram_config,
            tokens_used=tokens_used_value,
            processing_time=processing_time_value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting histogram result: {e}")
        raise HTTPException(status_code=500, detail=str(e))
