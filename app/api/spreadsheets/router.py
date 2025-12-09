"""
Spreadsheet API Router
Main router for spreadsheet processing endpoints
"""

import uuid
import json
from typing import Dict, Any, Optional, cast
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from loguru import logger

from app.models.types.enums import RequestStatus
from app.models.api.spreadsheet import (
    SpreadsheetRequest, 
    SpreadsheetProcessResponse, 
    SpreadsheetResultResponse,
    SpreadsheetData
)
from app.models.orm.ai_request import AIRequest
from app.services.database.session import get_db
from app.utils.json_encoder import DateTimeEncoder
from app.services.kafka.service import kafka_service
from app.services.spreadsheet.data_optimizer import SpreadsheetDataOptimizer

from .dependencies import get_current_user, limiter
from .validation import validate_spreadsheet_structure, validate_with_consistency_check
from .search import search_router


# Create main spreadsheet router
spreadsheet_router = APIRouter(prefix="/api/v1/spreadsheets", tags=["Spreadsheet Processing"])

# Include search router
spreadsheet_router.include_router(search_router)


@spreadsheet_router.post("/process", response_model=SpreadsheetProcessResponse)
@limiter.limit("30/minute")
async def process_spreadsheet_request(
    request: Request,
    spreadsheet_request: SpreadsheetRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process enhanced spreadsheet data with AI using style reference architecture
    
    Args:
        request: FastAPI request object (for rate limiting)
        spreadsheet_request: Spreadsheet processing request with data and query
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        Processing response with request_id and status
        
    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        # Validate the spreadsheet data format
        spreadsheet_data_dict = spreadsheet_request.spreadsheet_data.model_dump()
        
        # Validate using extracted validation logic
        is_valid, validation_errors = validate_spreadsheet_structure(spreadsheet_data_dict)
        
        if not is_valid:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid spreadsheet data: {', '.join(validation_errors)}"
            )
        
        # Initialize data optimizer
        optimizer = SpreadsheetDataOptimizer(db)
        
        # Optimize spreadsheet data based on requirements
        optimized_data, optimization_id = optimizer.optimize_data(
            spreadsheet_data=spreadsheet_data_dict,
            required_table_info=spreadsheet_request.required_table_info
        )
        
        # Convert optimized data to JSON for Kafka
        optimized_json = json.dumps(optimized_data, cls=DateTimeEncoder)
        
        # Serialize required_table_info if provided
        required_table_info_json = None
        if spreadsheet_request.required_table_info:
            required_table_info_json = json.dumps(
                spreadsheet_request.required_table_info.model_dump(), 
                cls=DateTimeEncoder
            )
        
        # Create AI request with optimization reference
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=spreadsheet_request.spreadsheet_data.worksheet.range,
            query_text=spreadsheet_request.query_text,
            category=spreadsheet_request.category if spreadsheet_request.category is not None else 'uncertain',
            optimization_id=optimization_id
        )
        db.add(db_request)
        db.commit()
        
        logger.info(
            f"Request {request_id} created with optimization {optimization_id} "
            f"for category {spreadsheet_request.category}"
        )
        
        # Send to Kafka for processing with optimized data
        # Prepare input data with optimized spreadsheet and optional required_table_info
        kafka_input_data = [{"spreadsheet_data": optimized_json}]
        if required_table_info_json:
            kafka_input_data[0]["required_table_info"] = required_table_info_json
        
        success = await kafka_service.send_request(
            request_id=request_id,
            user_id=user_id,
            query=spreadsheet_request.query_text,
            input_range=spreadsheet_request.spreadsheet_data.worksheet.range,
            category=spreadsheet_request.category if spreadsheet_request.category is not None else 'uncertain',
            input_data=kafka_input_data,
            priority=1 if current_user and current_user.get("role") == "premium" else 0
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue request")
        
        return SpreadsheetProcessResponse(
            success=True,
            request_id=request_id,
            status="queued",
            message="Spreadsheet processing request added to queue",
            error_message=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing spreadsheet request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@spreadsheet_router.get("/status/{request_id}", response_model=SpreadsheetProcessResponse)
async def get_spreadsheet_processing_status(request_id: str, db: Session = Depends(get_db)):
    """
    Get the processing status of a spreadsheet request
    
    Args:
        request_id: Unique request identifier
        db: Database session
        
    Returns:
        Processing status response
        
    Raises:
        HTTPException: 404 if request not found, 500 for server errors
    """
    try:
        db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Determine message based on status
        # Type-safe access to ORM attributes using cast
        status_value = cast(str, db_request.status)
        error_msg: str | None = cast(Optional[str], db_request.error_message)
        
        if status_value == RequestStatus.FAILED.value:
            message = error_msg or "Request failed"
        elif status_value == RequestStatus.COMPLETED.value:
            message = "Request completed successfully"
        else:
            message = "Request is being processed"
        
        return SpreadsheetProcessResponse(
            success=status_value == RequestStatus.COMPLETED.value,
            request_id=request_id,
            status=status_value,
            message=message,
            error_message=error_msg if status_value == RequestStatus.FAILED.value else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spreadsheet processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@spreadsheet_router.get("/result/{request_id}", response_model=SpreadsheetResultResponse)
async def get_spreadsheet_result(
    request_id: str, 
    db: Session = Depends(get_db)
):
    """
    Get the result of a spreadsheet processing request
    
    Args:
        request_id: Unique request identifier
        db: Database session
        
    Returns:
        Processing result response with spreadsheet data
        
    Raises:
        HTTPException: 404 if request not found, 500 for server errors
    """
    try:
        db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Type-safe access to ORM attributes using cast
        status_value = cast(str, db_request.status)
        
        if status_value != RequestStatus.COMPLETED.value:
            message = (
                "Request is still being processed" 
                if status_value in [RequestStatus.PENDING.value, RequestStatus.PROCESSING.value] 
                else "Request failed or was cancelled"
            )
            return SpreadsheetResultResponse(
                success=False,
                status=status_value,
                message=message,
                result=None,
                tokens_used=None,
                processing_time=None
            )
        
        # Try to parse result data if available
        result_data = None
        text_content = None
        raw_result_data = cast(Any, db_request.result_data)
        
        if raw_result_data is not None:
            try:
                # If result_data is a string, parse it
                parsed_data = None
                if isinstance(raw_result_data, str):
                    parsed_data = json.loads(raw_result_data)
                # If it's already a dict, use it directly
                elif isinstance(raw_result_data, dict):
                    parsed_data = raw_result_data
                
                # Check if this is a text-only response (assistance category)
                if parsed_data and 'text_content' in parsed_data:
                    text_content = parsed_data.get('text_content')
                    # Create minimal valid SpreadsheetData structure for text responses
                    result_data = SpreadsheetData().model_dump()
                elif parsed_data:
                    # Validate and parse the data using Pydantic model_validate
                    try:
                        validated_data = SpreadsheetData.model_validate(parsed_data)
                        result_data = validated_data.model_dump()
                        logger.debug(f"Successfully validated SpreadsheetData for request {request_id}")
                    except Exception as validation_error:
                        logger.warning(
                            f"SpreadsheetData validation failed for request {request_id}: {validation_error}. "
                            f"Falling back to minimal structure with defaults."
                        )
                        # Fallback to minimal structure with defaults
                        result_data = SpreadsheetData().model_dump()
                        
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse result data as JSON for request {request_id}: {e}")
                result_data = SpreadsheetData().model_dump()
            except Exception as e:
                logger.warning(f"Could not parse result data for request {request_id}: {e}")
                result_data = SpreadsheetData().model_dump()
        
        # Type-safe access to ORM attributes using cast
        tokens_used_value = cast(Optional[int], db_request.tokens_used)
        processing_time_value = cast(Optional[float], db_request.processing_time)
        
        # Determine message based on response type
        if text_content:
            message = text_content
        else:
            message = "Request completed successfully"
        
        return SpreadsheetResultResponse(
            success=True,
            status=status_value,
            message=message,
            result=cast(Optional[SpreadsheetData], result_data),
            tokens_used=tokens_used_value,
            processing_time=processing_time_value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spreadsheet result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@spreadsheet_router.post("/validate")
async def validate_spreadsheet_data(
    data: SpreadsheetData,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """
    Validate spreadsheet data format and style references
    
    Args:
        data: Spreadsheet data to validate
        current_user: Current authenticated user (optional)
        
    Returns:
        Validation result dictionary with errors and warnings
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        data_dict = data.model_dump()
        
        # Use extracted validation logic
        return validate_with_consistency_check(data_dict)
        
    except Exception as e:
        logger.error(f"Error validating spreadsheet data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
