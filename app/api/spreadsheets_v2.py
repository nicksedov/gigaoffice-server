"""
Enhanced Spreadsheet API Router V2
Router for enhanced spreadsheet manipulation with style reference architecture
"""

import os
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
from app.models.api.spreadsheet_v2 import (
    SpreadsheetRequestV2, 
    SpreadsheetProcessResponseV2, 
    SpreadsheetResultResponseV2,
    SpreadsheetDataV2
)
from app.models.api.spreadsheet import SpreadsheetSearchRequest, SearchResult, SearchResultItem
from app.models.orm.ai_request import AIRequest
from app.services.database.session import get_db
from app.services.spreadsheet.data_transformer import transformation_service
from app.services.spreadsheet.style_registry import StyleValidator, create_style_registry_from_data

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

# Support for full-text search
db_vector_support = os.getenv("DB_VECTOR_SUPPORT", "false").lower() == "true"

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token (simplified implementation)"""
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}

spreadsheet_v2_router = APIRouter(prefix="/api/v2/spreadsheets", tags=["Spreadsheet Processing V2"])

@spreadsheet_v2_router.post("/process", response_model=SpreadsheetProcessResponseV2)
@limiter.limit("10/minute")
async def process_spreadsheet_request_v2(
    request: Request,
    spreadsheet_request: SpreadsheetRequestV2,
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
        
        # Convert to legacy format for processing (backward compatibility with AI service)
        legacy_data, transform_errors = transformation_service.transform_to_legacy_format(
            spreadsheet_data_dict, validate=False
        )
        
        if transform_errors:
            logger.warning(f"Transformation warnings: {transform_errors}")
        
        # Convert spreadsheet data to JSON for storage using custom encoder
        spreadsheet_json = json.dumps(legacy_data, cls=DateTimeEncoder)
        
        db_request = AIRequest(
            id=request_id,
            user_id=user_id,
            status=RequestStatus.PENDING,
            input_range=spreadsheet_request.spreadsheet_data.worksheet.range,
            query_text=spreadsheet_request.query_text,
            category=spreadsheet_request.category if spreadsheet_request.category else 'uncertain',
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
        
        return SpreadsheetProcessResponseV2(
            success=True,
            request_id=request_id,
            status="queued",
            message="Spreadsheet processing request added to queue"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing spreadsheet request V2: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@spreadsheet_v2_router.get("/status/{request_id}", response_model=SpreadsheetProcessResponseV2)
async def get_spreadsheet_processing_status_v2(request_id: str, db: Session = Depends(get_db)):
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
        
        return SpreadsheetProcessResponseV2(
            success=db_request.status == RequestStatus.COMPLETED,
            request_id=request_id,
            status=db_request.status,
            message=message,
            error_message=db_request.error_message if db_request.status == RequestStatus.FAILED else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spreadsheet processing status V2: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@spreadsheet_v2_router.get("/result/{request_id}", response_model=SpreadsheetResultResponseV2)
async def get_spreadsheet_result_v2(
    request_id: str, 
    format_version: str = Query("2.0", description="Response format version (1.0 or 2.0)"),
    db: Session = Depends(get_db)
):
    """Get the result of a spreadsheet processing request with format selection"""
    try:
        db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
        if not db_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if db_request.status != RequestStatus.COMPLETED:
            return SpreadsheetResultResponseV2(
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
                    legacy_result = json.loads(db_request.result_data)
                # If it's already a dict, use it directly
                elif isinstance(db_request.result_data, dict):
                    legacy_result = db_request.result_data
                else:
                    legacy_result = None
                
                if legacy_result:
                    # Transform based on requested format
                    if format_version == "2.0":
                        result_data, transform_errors = transformation_service.transform_to_new_format(
                            legacy_result, validate=True
                        )
                        if transform_errors:
                            logger.warning(f"Result transformation warnings: {transform_errors}")
                    else:
                        result_data = legacy_result
                        
            except Exception as e:
                logger.warning(f"Could not parse result data: {e}")
        
        return SpreadsheetResultResponseV2(
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
        logger.error(f"Error getting spreadsheet result V2: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@spreadsheet_v2_router.post("/transform/to-legacy")
async def transform_to_legacy_format(
    data: SpreadsheetDataV2,
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Transform spreadsheet data from V2 format to legacy format"""
    try:
        data_dict = data.dict()
        legacy_data, errors = transformation_service.transform_to_legacy_format(data_dict)
        
        return {
            "success": True,
            "data": legacy_data,
            "errors": errors if errors else None,
            "message": "Successfully transformed to legacy format"
        }
        
    except Exception as e:
        logger.error(f"Error transforming to legacy format: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@spreadsheet_v2_router.post("/transform/from-legacy")
async def transform_from_legacy_format(
    data: Dict[str, Any],
    current_user: Optional[Dict] = Depends(get_current_user)
):
    """Transform spreadsheet data from legacy format to V2 format"""
    try:
        new_data, errors = transformation_service.transform_to_new_format(data)
        
        return {
            "success": True,
            "data": new_data,
            "errors": errors if errors else None,
            "message": "Successfully transformed to V2 format"
        }
        
    except Exception as e:
        logger.error(f"Error transforming from legacy format: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@spreadsheet_v2_router.post("/validate")
async def validate_spreadsheet_data(
    data: SpreadsheetDataV2,
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

@spreadsheet_v2_router.post("/data/search", response_model=List[SearchResult])
@limiter.limit("10/minute")
async def search_spreadsheet_data_v2(
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
        logger.error(f"Error searching spreadsheet data V2: {e}")
        raise HTTPException(status_code=500, detail="Error searching spreadsheet data")