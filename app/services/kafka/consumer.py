"""
Kafka Consumer for Chart Processing
Consumer service to handle chart generation requests from Kafka queue
"""

import asyncio
import json
import signal
from typing import Dict, Any, Optional
from loguru import logger

from app.services.kafka.service import kafka_service
from app.services.chart.processor import chart_processing_service

class ChartKafkaConsumer:
    """Kafka consumer for chart processing requests"""
    
    def __init__(self):
        self.is_running = False
        self.consumer_task = None
        self.shutdown_event = asyncio.Event()
        
    async def start_consumer(self):
        """Start the Kafka consumer for chart processing"""
        
        if self.is_running:
            logger.warning("Consumer is already running")
            return
            
        try:
            logger.info("Starting Kafka consumer for chart processing...")
            
            # Initialize Kafka service
            await kafka_service.start()
            
            # Start consumer with message processor
            self.consumer_task = asyncio.create_task(
                kafka_service.start_consumer(self.process_chart_message)
            )
            
            self.is_running = True
            logger.info("Chart Kafka consumer started successfully")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error starting Kafka consumer: {e}")
            raise
        finally:
            await self.stop_consumer()
    
    async def process_chart_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chart generation message from Kafka"""
        
        request_id = message_data.get("id", "unknown")
        
        try:
            logger.info(f"Processing chart message: {request_id}")
            
            # Validate message structure
            if not self._validate_message_structure(message_data):
                return {
                    "success": False,
                    "error": "Invalid message structure",
                    "request_id": request_id
                }
            
            # Check message category
            category = message_data.get("category", "")
            if category != "chart_generation":
                logger.warning(f"Unexpected message category: {category}")
                return {
                    "success": False,
                    "error": f"Unsupported message category: {category}",
                    "request_id": request_id
                }
            
            # Process chart generation request
            result = await chart_processing_service.process_chart_request(message_data)
            
            logger.info(f"Chart processing completed for {request_id}: {result.get('success', False)}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing chart message {request_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "request_id": request_id
            }
    
    def _validate_message_structure(self, message_data: Dict[str, Any]) -> bool:
        """Validate the structure of received message"""
        
        required_fields = ["id", "user_id", "category", "query", "input_data"]
        
        for field in required_fields:
            if field not in message_data:
                logger.error(f"Missing required field in message: {field}")
                return False
        
        # Validate input_data structure
        input_data = message_data.get("input_data", [])
        if not isinstance(input_data, list) or not input_data:
            logger.error("input_data must be a non-empty list")
            return False
        
        # Validate chart request data
        first_input = input_data[0]
        if not isinstance(first_input, dict) or "chart_request" not in first_input:
            logger.error("First input_data item must contain chart_request")
            return False
        
        return True
    
    async def stop_consumer(self):
        """Stop the Kafka consumer"""
        
        if not self.is_running:
            return
            
        try:
            logger.info("Stopping Kafka consumer...")
            
            # Stop Kafka service consumer
            kafka_service.stop_consumer()
            
            # Cancel consumer task
            if self.consumer_task and not self.consumer_task.done():
                self.consumer_task.cancel()
                try:
                    await self.consumer_task
                except asyncio.CancelledError:
                    logger.info("Consumer task cancelled")
            
            # Cleanup Kafka resources
            await kafka_service.cleanup()
            
            self.is_running = False
            logger.info("Kafka consumer stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Kafka consumer: {e}")
    
    def shutdown(self):
        """Signal shutdown of the consumer"""
        self.shutdown_event.set()
    
    def get_consumer_status(self) -> Dict[str, Any]:
        """Get current consumer status"""
        
        return {
            "is_running": self.is_running,
            "consumer_task_active": self.consumer_task is not None and not self.consumer_task.done(),
            "kafka_service_status": kafka_service.get_health_status(),
            "processing_stats": chart_processing_service.get_processing_stats()
        }

# Global consumer instance
chart_kafka_consumer = ChartKafkaConsumer()

# Signal handlers for graceful shutdown
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        chart_kafka_consumer.shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# Consumer entry point
async def run_chart_consumer():
    """Entry point for running the chart consumer"""
    
    setup_signal_handlers()
    
    try:
        await chart_kafka_consumer.start_consumer()
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        raise
    finally:
        logger.info("Chart consumer shutdown complete")

if __name__ == "__main__":
    asyncio.run(run_chart_consumer())