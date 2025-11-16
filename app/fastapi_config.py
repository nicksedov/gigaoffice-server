"""
GigaOffice FastAPI Application Setup
Конфигурация и инициализация FastAPI приложения
"""

import os
import time
import asyncio
from typing import Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response

from app.services.database.session import init_database, get_db_session
from app.models.types.enums import RequestStatus
from app.models.orm.ai_request import AIRequest
# Direct imports for GigaChat services
from app.services.gigachat.prompt_builder import prompt_builder
from app.services.gigachat.factory import create_gigachat_service
from app.services.spreadsheet import create_spreadsheet_processor  # Added import for spreadsheet processor
from app.services.chart import create_chart_processor  # Added import for chart processor
from app.services.histogram import create_histogram_processor  # Added import for histogram processor

# Create services in the module where needed
gigachat_generate_service = create_gigachat_service(prompt_builder, "GIGACHAT_GENERATE_MODEL", "GigaChat generation service")

# Create chart processor for handling chart generation requests
# This processor is used by the Kafka message handler to process chart generation requests
chart_processor = create_chart_processor(gigachat_generate_service)  # Create chart processor

# Create histogram processor for handling histogram analysis requests
# This processor is used by the Kafka message handler to process histogram analysis requests
histogram_processor = create_histogram_processor(gigachat_generate_service)  # Create histogram processor

from app.services.kafka.service import kafka_service
from app.prompts import prompt_manager

# Configuration
APP_VERSION = "1.0.0"
APP_NAME = "GigaOffice AI Service"
APP_DESCRIPTION = "Промежуточный сервис для интеграции Р7-офиса с GigaChat"

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Security
security = HTTPBearer(auto_error=False)

# Global variables
app_start_time = time.time()

async def message_handler(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process AI request from Kafka queue
    
    Handles both spreadsheet and chart processing requests.
    For chart requests, the input_data contains series with 'range' fields
    instead of inline 'values'.
    """
    request_id = None  # Initialize request_id to fix "possibly unbound" error
    try:
        request_id = message_data["id"]
        query = message_data["query"]
        input_range = message_data["input_range"]
        category = message_data["category"]
        input_data = message_data["input_data"]
        
        logger.info(f"Processing Kafka message: {request_id} with category: {category}")
        
        # Route based on category
        if category == "data-histogram":
            # Process as histogram analysis request
            # Deserialize spreadsheet data with statistical metadata
            import json
            spreadsheet_data = json.loads(input_data[0]["spreadsheet_data"]) if input_data and len(input_data) == 1 and "spreadsheet_data" in input_data[0] else {}
            result, metadata = await histogram_processor.process_histogram(query, category, spreadsheet_data)
        elif category == "data-chart":
            # Process as chart generation request
            # Deserialize chart data with range-based series
            import json
            chart_data = json.loads(input_data[0]["spreadsheet_data"]) if input_data and len(input_data) == 1 and "spreadsheet_data" in input_data[0] else {}
            # chart_data will be a list of dicts with 'name', 'range', and 'format' fields
            result, metadata = await chart_processor.process_chart(query, category, chart_data)
        elif category.startswith("spreadsheet-"):
            # Process as enhanced spreadsheet data with category-specific preprocessing
            import json
            if input_data and len(input_data) == 1 and "spreadsheet_data" in input_data[0]:
                spreadsheet_data = json.loads(input_data[0]["spreadsheet_data"])
                
                # Extract required_table_info if provided
                required_table_info = None
                if "required_table_info" in input_data[0]:
                    from app.models.api.prompt import RequiredTableInfo
                    required_table_info_dict = json.loads(input_data[0]["required_table_info"])
                    required_table_info = RequiredTableInfo(**required_table_info_dict)
                
                # Create category-specific processor for optimal data preprocessing
                processor = create_spreadsheet_processor(category, gigachat_generate_service)
                result, metadata = await processor.process_spreadsheet(
                    query, category, spreadsheet_data, required_table_info=required_table_info
                )
            else:
                raise Exception(f"Invalid input data for spreadsheet processing")
        else:
            # Unknown category
            logger.error(f"Unknown category: {category}")
            raise Exception(f"Unknown category: {category}")
        
        # Update database
        with get_db_session() as db:
            db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
            if db_request:
                # Use setattr to avoid type checker issues with direct attribute assignment
                setattr(db_request, 'status', RequestStatus.COMPLETED.value)
                setattr(db_request, 'result_data', result)
                setattr(db_request, 'tokens_used', metadata.get("total_tokens", 0))
                setattr(db_request, 'processing_time', metadata.get("processing_time", 0))
                setattr(db_request, 'completed_at', datetime.now())
                db.commit()
        
        logger.info(f"Request {request_id} processed successfully")
        return {
            "success": True,
            "result": result,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {e}")
        
        # Update database with error
        with get_db_session() as db:
            db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
            if db_request:
                setattr(db_request, 'status', RequestStatus.FAILED.value)
                setattr(db_request, 'error_message', str(e))
                db.commit()
        return {
            "success": False,
            "error": str(e)
        }


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """Wrapper for SlowAPI's rate limit exceeded handler to match FastAPI's exception handler signature"""
    # Type check to ensure we're handling the right exception type
    if isinstance(exc, RateLimitExceeded):
        return _rate_limit_exceeded_handler(request, exc)
    # Fallback response if somehow a different exception type gets here
    return Response("Rate limit exceeded", status_code=429)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for FastAPI app"""
    # Startup logic
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    try:
        init_database()
        logger.info("Database initialized")
        
        await prompt_manager.get_prompt_categories()
        await prompt_manager.get_prompts()
        logger.info("Prompt manager initialized")
        
        await kafka_service.start()
        asyncio.create_task(kafka_service.start_consumer(message_handler))
        logger.info("Kafka consumer started")
        
        yield
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    # Shutdown logic
    logger.info("Shutting down application...")
    try:
        await kafka_service.cleanup()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    return app