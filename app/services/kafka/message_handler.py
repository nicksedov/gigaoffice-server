"""
Message Handler for Kafka Service
Handles message processing, routing, and Dead Letter Queue operations
"""

import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from loguru import logger

from app.utils.json_encoder import DateTimeEncoder
from .config import KafkaConfig
from .models import QueueMessage
from .health_monitor import HealthMonitor
from .connection_manager import ConnectionManager


class MessageHandler:
    """Handles message sending, consuming, and processing"""
    
    def __init__(
        self, 
        config: KafkaConfig, 
        health_monitor: HealthMonitor,
        connection_manager: ConnectionManager
    ):
        """
        Initialize message handler
        
        Args:
            config: Kafka configuration
            health_monitor: Health monitor for metrics tracking
            connection_manager: Connection manager for producer/consumer access
        """
        self.config = config
        self.health_monitor = health_monitor
        self.connection_manager = connection_manager
        
        # State
        self.is_running = False
        self.processing_callbacks: Dict[str, Callable] = {}
    
    async def send_request(
        self,
        request_id: str,
        user_id: int,
        query: str,
        input_range: str,
        category: str,
        input_data: Optional[List[Dict]] = None,
        priority: int = 0
    ) -> bool:
        """
        Send a request message to the request queue
        
        Args:
            request_id: Unique request identifier
            user_id: User identifier
            query: User query string
            input_range: Input data range
            category: Request category
            input_data: Optional input data
            priority: Message priority (default: 0)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Check if producer is initialized
            if not self.connection_manager.producer:
                logger.error("Producer not initialized")
                return False
                
            message = QueueMessage(
                id=request_id,
                user_id=user_id,
                priority=priority,
                input_range=input_range,
                query=query,
                category=category,
                input_data=input_data
            )
            
            message_data = {
                "id": message.id,
                "user_id": message.user_id,
                "priority": message.priority,
                "query": message.query,
                "input_range": message.input_range,
                "category": message.category, 
                "input_data": message.input_data,
                "created_at": message.created_at,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send message using custom encoder
            await self.connection_manager.producer.send_and_wait(
                topic=self.config.topic_requests,
                key=request_id.encode('utf-8'),
                value=json.dumps(message_data, ensure_ascii=False, cls=DateTimeEncoder).encode('utf-8')
            )
            
            self.health_monitor.messages_sent += 1
            logger.info(f"Request {request_id} sent to queue successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send request {request_id} to queue: {e}")
            self.health_monitor.messages_failed += 1
            return False
    
    async def _send_response(self, request_id: str, result: Dict[str, Any], processing_time: float) -> None:
        """
        Send response message to response topic
        
        Args:
            request_id: Request identifier
            result: Processing result
            processing_time: Time taken to process message
        """
        # Check if producer is initialized
        if not self.connection_manager.producer:
            logger.error("Producer not initialized")
            return
            
        try:
            response_data = {
                "request_id": request_id,
                "result": result,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "status": "completed" if result.get("success") else "failed"
            }
            
            await self.connection_manager.producer.send_and_wait(
                topic=self.config.topic_responses,
                key=request_id.encode('utf-8'),
                value=json.dumps(response_data, ensure_ascii=False, cls=DateTimeEncoder).encode('utf-8')
            )
            
        except Exception as e:
            logger.error(f"Failed to send response for {request_id}: {e}")
    
    async def _send_to_dlq(self, msg, error_reason: str) -> None:
        """
        Send failed message to Dead Letter Queue
        
        Args:
            msg: Original Kafka message
            error_reason: Reason for failure
        """
        # Check if producer is initialized
        if not self.connection_manager.producer:
            logger.error("Producer not initialized")
            return
            
        try:
            dlq_data = {
                "original_topic": msg.topic,
                "original_partition": msg.partition,
                "original_offset": msg.offset,
                "original_key": msg.key.decode('utf-8') if msg.key else None,
                "original_value": msg.value.decode('utf-8'),
                "error_reason": error_reason,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.connection_manager.producer.send_and_wait(
                topic=self.config.topic_dlq,
                value=json.dumps(dlq_data, ensure_ascii=False, cls=DateTimeEncoder).encode('utf-8')
            )
            
            logger.warning(f"Message sent to DLQ: {error_reason}")
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")
    
    async def _process_message(self, msg, processor: Callable) -> None:
        """
        Process a single message
        
        Args:
            msg: Kafka message to process
            processor: Callback function for message processing
        """
        # Check if consumer is initialized
        if not self.connection_manager.consumer:
            logger.error("Consumer not initialized")
            return
            
        try:
            # Parse message
            message_data = json.loads(msg.value.decode('utf-8'))
            request_id = message_data.get("id")
            
            logger.info(f"Processing message: {request_id}")
            start_time = time.time()
            
            # Invoke processor
            result = await processor(message_data)
            
            processing_time = time.time() - start_time
            self.health_monitor.processing_times.append(processing_time)
            
            # Send response
            await self._send_response(request_id, result, processing_time)
            
            # Commit message
            await self.connection_manager.consumer.commit()
            
            self.health_monitor.messages_received += 1
            logger.info(f"Message {request_id} processed successfully in {processing_time:.2f}s")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            await self._send_to_dlq(msg, "JSON parsing error")
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            await self._send_to_dlq(msg, str(e))
    
    async def start_consumer(self, message_processor: Callable) -> None:
        """
        Start consuming messages from request topic
        
        Args:
            message_processor: Callback function to process each message
        """
        # Check if consumer is initialized
        if not self.connection_manager.consumer:
            logger.error("Consumer not initialized")
            return
            
        self.is_running = True
        self.processing_callbacks['default'] = message_processor
        
        try:
            logger.info(f"Started consuming from topic: {self.config.topic_requests}")
            
            async for msg in self.connection_manager.consumer:
                if not self.is_running:
                    break
                    
                try:
                    # Process message
                    await self._process_message(msg, message_processor)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self._send_to_dlq(msg, str(e))
                    
        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
        finally:
            logger.info("Consumer stopped")
    
    def stop_consumer(self) -> None:
        """Stop the message consumer"""
        self.is_running = False
        logger.info("Consumer stop requested")
