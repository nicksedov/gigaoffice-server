#!/usr/bin/env python3
"""
Chart Consumer Startup Script
Script to start the Kafka consumer for chart processing
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.services.kafka.consumer import run_chart_consumer

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    
    # Remove default logger
    logger.remove()
    
    # Console logging
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # File logging if specified
    if log_file:
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 day",
            retention="30 days",
            compression="gz"
        )

def validate_environment():
    """Validate required environment variables"""
    
    required_vars = [
        "KAFKA_BOOTSTRAP_SERVERS",
        "DATABASE_URL",
        "GIGACHAT_CLIENT_ID",
        "GIGACHAT_CLIENT_SECRET"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

async def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description="Chart Generation Kafka Consumer")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--log-file", help="Log file path")
    parser.add_argument("--validate-env", action="store_true", help="Validate environment and exit")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    logger.info("Starting Chart Generation Kafka Consumer")
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    if args.validate_env:
        logger.info("Environment validation passed")
        sys.exit(0)
    
    try:
        # Run the consumer
        await run_chart_consumer()
        
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())