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

from database import init_database, get_db_session
from model_types import RequestStatus
from model_orm import AIRequest
from gigachat_factory import gigachat_service
from kafka_service import kafka_service
from prompts import prompt_manager

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
    """Process AI request from Kafka queue"""
    try:
        request_id = message_data["id"]
        query = message_data["query"]
        input_range = message_data["input_range"]
        output_range = message_data["output_range"]
        category = message_data["category"]
        input_data = message_data["input_data"]
        
        logger.info(f"Processing Kafka message: {request_id}")
        
        # Process with GigaChat
        result, metadata = await gigachat_service.process_query(query, input_range, output_range, category, input_data)
        
        # Update database
        with get_db_session() as db:
            db_request = db.query(AIRequest).filter(AIRequest.id == request_id).first()
            if db_request:
                db_request.status = RequestStatus.COMPLETED
                db_request.result_data = result
                db_request.tokens_used = metadata.get("total_tokens", 0)
                db_request.processing_time = metadata.get("processing_time", 0)
                db_request.completed_at = datetime.now()
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
                db_request.status = RequestStatus.FAILED
                db_request.error_message = str(e)
                db.commit()
        return {
            "success": False,
            "error": str(e)
        }

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
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return app

