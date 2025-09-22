"""
Spreadsheet API Router
Router for enhanced spreadsheet manipulation endpoints
"""

import uuid
import json
from typing import Dict, Any, Optional, Union, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from app.models.types.enums import RequestStatus
from app.models.api.spreadsheet import SpreadsheetRequest, SpreadsheetProcessResponse, SpreadsheetResultResponse, SpreadsheetSearchRequest, SearchResult, SearchResultItem
from app.models.orm.ai_request import AIRequest
from app.services.database.session import get_db
# Direct imports for GigaChat services
from app.services.gigachat.prompt_builder import prompt_builder
from app.services.gigachat.factory import create_gigachat_services

# Import custom JSON encoder
from app.utils.json_encoder import DateTimeEncoder

# Create services in the module where needed
_, gigachat_generate_service = create_gigachat_services(prompt_builder)

from app.services.kafka.service import kafka_service
from app.fastapi_config import security

# Import for vector search functionality
from app.services.database.vector_search import vector_search_service

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}

spreadsheet_router = APIRouter(prefix="/api/spreadsheets", tags=["Spreadsheet Processing"])

@spreadsheet_router.post("/process", response_model=SpreadsheetProcessResponse)
@limiter.limit("10/minute")
async def process_spreadsheet_request(
    request: Request,
    spreadsheet_request: SpreadsheetRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process enhanced spreadsheet data with AI"""
    try:
        request_id = str(uuid.uuid4())
        user_id = current_user.get("id", 0) if current_user else 0
        
        # Convert spreadsheet data to JSON for storage using custom encoder
        spreadsheet_json = json.dumps(spreadsheet_request.spreadsheet_data.dict(), cls=DateTimeEncoder)
        
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=spreadsheet_request.spreadsheet_data.worksheet.range,
            query_text=spreadsheet_request.query_text,
            category=spreadsheet_request.category,
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
            category=spreadsheet_request.category,
            input_data=[{"spreadsheet_data": spreadsheet_json}],
            priority=1 if current_user and current_user.get("role") == "premium" else 0
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to queue request")
        
        return SpreadsheetProcessResponse(
            success=True,
            request_id=request_id,
            status="queued",
            message="Spreadsheet processing request added to queue"
        )
        
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
        if db_request.status == RequestStatus.FAILED:
            message = db_request.error_message
        elif db_request.status == RequestStatus.COMPLETED:
            message = "Request completed successfully"
        else:
            message = "Request is being processed"
        
        return SpreadsheetProcessResponse(
            success=db_request.status == RequestStatus.COMPLETED,
            request_id=request_id,
            status=db_request.status,
            message=message,
            error_message=db_request.error_message if db_request.status == RequestStatus.FAILED else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spreadsheet processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@spreadsheet_router.get("/result/{request_id}", response_model=SpreadsheetResultResponse)
async def get_spreadsheet_result(request_id: str, db: Session = Depends(get_db)):
    """Get the result of a spreadsheet processing request"""
    try:
        db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if db_request.status != RequestStatus.COMPLETED:
            return SpreadsheetResultResponse(
                success=False,
                status=db_request.status,
                message="Request is still being processed" if db_request.status in [RequestStatus.PENDING, RequestStatus.PROCESSING] else "Request failed or was cancelled",
                result=None,
                tokens_used=None,
                processing_time=None
            )
        
        # Try to parse result data if available
        result_data = None
        if db_request.result_data:
            try:
                # If result_data is a string, parse it
                if isinstance(db_request.result_data, str):
                    result_data = json.loads(db_request.result_data)
                # If it's already a dict, use it directly
                elif isinstance(db_request.result_data, dict):
                    result_data = db_request.result_data
            except Exception as e:
                logger.warning(f"Could not parse result data: {e}")
        
        return SpreadsheetResultResponse(
            success=True,
            status=db_request.status,
            message="Request completed successfully",
            result=result_data,
            tokens_used=db_request.tokens_used,
            processing_time=db_request.processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spreadsheet result: {e}")
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
    """Search spreadsheet data using vector embeddings"""
    try:
        # Validate domain parameter
        if domain != "header":
            raise HTTPException(status_code=400, detail="Invalid domain parameter. Only 'header' is supported.")
        
        # Prepare search strings
        search_strings = search_request.data if isinstance(search_request.data, list) else [search_request.data]
        
        # Collect all results
        all_results = []
        
        # Search for each string
        for search_string in search_strings:
            
            # Perform vector search
            results = vector_search_service.fulltext_search(search_string, "header_embeddings", limit)
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
    except Exception as e:
        logger.error(f"Error searching spreadsheet data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
