"""
Application Lifespan Management
Handles application startup and shutdown events
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from app.core.config import settings
from app.db.session import database_manager
from app.services.ai.factory import gigachat_factory
from app.services.kafka.service import kafka_service
from app.services.prompts.manager import prompt_manager
from app.utils.logger import structured_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager
    
    Handles startup and shutdown events for the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # Startup events
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        # Initialize database
        await startup_database()
        
        # Initialize AI services
        await startup_ai_services()
        
        # Initialize Kafka service
        await startup_kafka_service()
        
        # Initialize other services
        await startup_additional_services()
        
        logger.info("Application startup completed successfully")
        structured_logger.log_service_call(
            service="application",
            method="startup",
            duration=0,
            success=True,
            metadata={"version": settings.app_version}
        )
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        structured_logger.log_service_call(
            service="application",
            method="startup",
            duration=0,
            success=False,
            error=str(e)
        )
        raise
    
    # Application is running
    yield
    
    # Shutdown events
    logger.info("Shutting down application...")
    
    try:
        # Cleanup services in reverse order
        await shutdown_kafka_service()
        await shutdown_ai_services()
        await shutdown_database()
        await shutdown_additional_services()
        
        logger.info("Application shutdown completed successfully")
        structured_logger.log_service_call(
            service="application",
            method="shutdown",
            duration=0,
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")
        structured_logger.log_service_call(
            service="application",
            method="shutdown",
            duration=0,
            success=False,
            error=str(e)
        )


async def startup_database():
    """Initialize database connections and check health"""
    try:
        logger.info("Initializing database...")
        
        # Initialize database manager
        await database_manager.initialize()
        
        # Check database connection
        if not database_manager.check_connection():
            raise Exception("Database connection check failed")
        
        # Get database info
        db_info = database_manager.get_db_info()
        logger.info(f"Database connected: {db_info.get('database_name', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Database startup failed: {e}")
        raise


async def startup_ai_services():
    """Initialize AI services"""
    try:
        logger.info("Initializing AI services...")
        
        # Initialize GigaChat factory
        await gigachat_factory.initialize()
        
        # Test services
        generate_service = gigachat_factory.get_service("generate")
        classify_service = gigachat_factory.get_service("classify")
        
        # Check service health
        generate_health = generate_service.check_service_health()
        classify_health = classify_service.check_service_health()
        
        logger.info(f"GigaChat Generate Service: {generate_health.get('status', 'unknown')}")
        logger.info(f"GigaChat Classify Service: {classify_health.get('status', 'unknown')}")
        
    except Exception as e:
        logger.error(f"AI services startup failed: {e}")
        # Don't raise - allow app to start without AI services in development
        if settings.environment == "production":
            raise


async def startup_kafka_service():
    """Initialize Kafka service"""
    try:
        logger.info("Initializing Kafka service...")
        
        # Start Kafka service
        await kafka_service.start()
        
        # Check Kafka health
        kafka_health = kafka_service.get_health_status()
        logger.info(f"Kafka Service: {kafka_health.get('status', 'unknown')}")
        
        # Note: Consumer will be started separately when needed
        
    except Exception as e:
        logger.error(f"Kafka service startup failed: {e}")
        # Don't raise - allow app to start without Kafka in development
        if settings.environment == "production":
            raise


async def startup_additional_services():
    """Initialize additional services and components"""
    try:
        logger.info("Initializing additional services...")
        
        # Initialize prompt manager cache
        # This will pre-load categories and prompts
        categories = await prompt_manager.get_prompt_categories()
        logger.info(f"Loaded {len(categories)} prompt categories")
        
        # Initialize any other services here
        # ...
        
    except Exception as e:
        logger.error(f"Additional services startup failed: {e}")
        # Don't raise - these are non-critical services


async def shutdown_database():
    """Cleanup database connections"""
    try:
        logger.info("Shutting down database connections...")
        await database_manager.cleanup()
        
    except Exception as e:
        logger.error(f"Database shutdown error: {e}")


async def shutdown_ai_services():
    """Cleanup AI services"""
    try:
        logger.info("Shutting down AI services...")
        await gigachat_factory.cleanup()
        
    except Exception as e:
        logger.error(f"AI services shutdown error: {e}")


async def shutdown_kafka_service():
    """Cleanup Kafka service"""
    try:
        logger.info("Shutting down Kafka service...")
        
        # Stop Kafka service
        await kafka_service.cleanup()
        
    except Exception as e:
        logger.error(f"Kafka service shutdown error: {e}")


async def shutdown_additional_services():
    """Cleanup additional services"""
    try:
        logger.info("Shutting down additional services...")
        
        # Clear prompt manager cache
        prompt_manager._clear_cache()
        
        # Cleanup any other services here
        # ...
        
    except Exception as e:
        logger.error(f"Additional services shutdown error: {e}")


# Health check function for use in endpoints
async def check_services_health():
    """
    Check health of all services
    
    Returns:
        Dict with health status of all services
    """
    health_status = {
        "database": False,
        "ai_services": False,
        "kafka": False,
        "overall": False
    }
    
    try:
        # Check database
        health_status["database"] = database_manager.check_connection()
        
        # Check AI services
        try:
            generate_service = gigachat_factory.get_service("generate")
            ai_health = generate_service.check_service_health()
            health_status["ai_services"] = ai_health.get("status") == "healthy"
        except Exception:
            health_status["ai_services"] = False
        
        # Check Kafka
        try:
            kafka_health = kafka_service.get_health_status()
            health_status["kafka"] = kafka_health.get("status") == "healthy"
        except Exception:
            health_status["kafka"] = False
        
        # Overall health
        health_status["overall"] = all([
            health_status["database"],
            health_status["ai_services"] or settings.environment != "production",
            health_status["kafka"] or settings.environment != "production"
        ])
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    return health_status