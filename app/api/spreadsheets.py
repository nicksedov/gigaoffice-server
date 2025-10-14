"""
Enhanced Spreadsheet API Router
Router for enhanced spreadsheet manipulation with style reference architecture
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
from app.models.api.spreadsheet import (
    SpreadsheetRequest, 
    SpreadsheetProcessResponse, 
    SpreadsheetResultResponse,
    SpreadsheetData,
    SpreadsheetSearchRequest, SearchResult, SearchResultItem
)
from app.models.orm.ai_request import AIRequest
from app.services.database.session import get_db
from app.services.spreadsheet.style_registry import StyleValidator, create_style_registry_from_data

# Direct imports for GigaChat services
from app.services.gigachat.prompt_builder import prompt_builder

# Import custom JSON encoder
from app.utils.json_encoder import DateTimeEncoder

from app.services.kafka.service import kafka_service
from app.fastapi_config import security

# Import for vector search functionality
from app.services.database.vector_search import vector_search_service

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Support for full-text search
db_vector_support = os.getenv("DB_VECTOR_SUPPORT", "false").lower() == "true"

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}

spreadsheet_router = APIRouter(prefix="/api/v1/spreadsheets", tags=["Spreadsheet Processing"])

@spreadsheet_router.post("/process", response_model=SpreadsheetProcessResponse)
@limiter.limit("10/minute")
async def process_spreadsheet_request(
    request: Request,
    spreadsheet_request: SpreadsheetRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process enhanced spreadsheet data with AI using style reference architecture"""
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        # Validate the spreadsheet data format
        spreadsheet_data_dict = spreadsheet_request.spreadsheet_data.dict()
        
        # Create style registry and validate
        registry = create_style_registry_from_data(spreadsheet_data_dict)
        validator = StyleValidator(registry)
        is_valid, validation_errors = validator.validate_spreadsheet_data(spreadsheet_data_dict)
        
        if not is_valid:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid spreadsheet data: {', '.join(validation_errors)}"
            )
        
        # Convert spreadsheet data to JSON for storage using custom encoder
        spreadsheet_json = json.dumps(spreadsheet_data_dict, cls=DateTimeEncoder)
        
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=spreadsheet_request.spreadsheet_data.worksheet.range,
            query_text=spreadsheet_request.query_text,
            category=spreadsheet_request.category if spreadsheet_request.category is not None else 'uncertain',
            input_data=spreadsheet_json
        )
        db.add(db_request)
        db.commit()
          
        
        # Send to Kafka for processing
        success = await kafka_service.send_request(
            request_id=request_id,
            user_id=user_id,
            query=spreadsheet_request.query_text,
            input_range=spreadsheet_request.spreadsheet_data.worksheet.range,
            category=spreadsheet_request.category if spreadsheet_request.category is not None else 'uncertain',
            input_data=[{"spreadsheet_data": spreadsheet_json}],
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
    """Get the processing status of a spreadsheet request"""
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
    """Get the result of a spreadsheet processing request"""
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
        raw_result_data = cast(Any, db_request.result_data)
        
        if raw_result_data is not None:
            try:
                # If result_data is a string, parse it
                if isinstance(raw_result_data, str):
                    result_data = json.loads(raw_result_data)
                # If it's already a dict, use it directly
                elif isinstance(raw_result_data, dict):
                    result_data = raw_result_data
                        
            except Exception as e:
                logger.warning(f"Could not parse result data: {e}")
        
        # Type-safe access to ORM attributes using cast
        tokens_used_value = cast(Optional[int], db_request.tokens_used)
        processing_time_value = cast(Optional[float], db_request.processing_time)
        
        return SpreadsheetResultResponse(
            success=True,
            status=status_value,
            message="Request completed successfully",
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
    """Validate spreadsheet data format and style references"""
    try:
        data_dict = data.dict()
        
        # Create style registry and validate
        registry = create_style_registry_from_data(data_dict)
        validator = StyleValidator(registry)
        
        # Perform comprehensive validation
        is_valid, validation_errors = validator.validate_spreadsheet_data(data_dict)
        is_consistent, consistency_warnings = validator.validate_style_consistency(data_dict)
        
        return {
            "success": True,
            "is_valid": is_valid,
            "is_consistent": is_consistent,
            "validation_errors": validation_errors,
            "consistency_warnings": consistency_warnings,
            "style_count": len(data_dict.get("styles", [])),
            "message": "Validation completed"
        }
        
    except Exception as e:
        logger.error(f"Error validating spreadsheet data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@spreadsheet_router.post("/data/search", response_model=List[SearchResult])
@limiter.limit("10/minute")
async def search_spreadsheet_data(
    request: Request,
    search_request: SpreadsheetSearchRequest,
    domain: str = Query(..., description="Domain area for search. Currently only supports 'header'"),
    limit: int = Query(..., description="Number of most relevant results to return per search string"),
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search spreadsheet data using vector embeddings or fast lemmatization matching"""
    try:
        # Validate domain parameter
        if domain != "header":
            raise HTTPException(status_code=400, detail="Invalid domain parameter. Only 'header' is supported.")
        
        # Validate limit parameter
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        # Prepare search strings
        search_strings = search_request.data if isinstance(search_request.data, list) else [search_request.data]
        
        search_mode = "fulltext" if db_vector_support else "fast"

        # Collect all results
        all_results = []
        
        # Search for each string using the specified mode
        for search_string in search_strings:
            # Perform search using the unified search method
            results = vector_search_service.search(
                search_string, 
                "header_embeddings", 
                search_mode, 
                limit
            )
            item_search_results = []
            # Convert to SearchResultItem objects
            for header, language, score in results:
                item_search_results.append(SearchResultItem(
                    text=header,
                    language=language,
                    score=score
                ))
            search_result = SearchResult(search_text=search_string, search_results=item_search_results)
            all_results.append(search_result)   
        
        return all_results
            
    except HTTPException:
        raise
    except ValueError as e:
        # Handle search_mode validation errors from vector_search_service
        logger.error(f"Invalid search mode: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching spreadsheet data: {e}")
        raise HTTPException(status_code=500, detail="Error searching spreadsheet data")