"""
Enhanced Kafka Service
Improved Kafka integration with better error handling, monitoring, and configuration management
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import KafkaError
from loguru import logger

from ...core.config import get_settings, load_config_file, app_state
from ...utils.logger import structured_logger, performance_timer
from ...utils.resource_loader import resource_loader


@dataclass
class QueueMessage:
    """Enhanced queue message with validation and serialization"""
    id: str
    user_id: int
    priority: int
    query: str
    input_range: str
    category: str
    input_data: Optional[List[Dict]] = None
    created_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueMessage':
        """Create from dictionary"""
        return cls(**data)
    
    def increment_retry(self) -> bool:
        """Increment retry count, return True if retries remaining"""
        self.retry_count += 1
        return self.retry_count <= self.max_retries


@dataclass
class MessageProcessingResult:
    """Result of message processing"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class KafkaService:
    """Enhanced Kafka service with improved reliability and monitoring"""
    
    def __init__(self):
        self.settings = get_settings()
        self.config = load_config_file("kafka_config")
        
        # Kafka configuration
        self.bootstrap_servers = self.settings.kafka_bootstrap_servers
        self.topic_requests = self.settings.kafka_request_topic
        self.topic_responses = self.settings.kafka_response_topic
        self.topic_dlq = self.config.get("topics", {}).get("dlq", "gigaoffice-dlq")
        
        # Consumer configuration
        self.consumer_group = self.settings.kafka_group_id
        self.auto_offset_reset = self.settings.kafka_auto_offset_reset
        
        # Service settings
        self.max_queue_size = int(self.config.get("max_queue_size", 1000))
        self.max_processing_time = int(self.config.get("max_processing_time", 300))
        self.consumer_batch_size = int(self.config.get("consumer_batch_size", 10))
        
        # Components
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.admin_client: Optional[AIOKafkaAdminClient] = None
        
        # State management
        self.is_running = False
        self.is_initialized = False
        self.processing_callbacks: Dict[str, Callable] = {}
        
        # Statistics and monitoring
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_failed = 0
        self.messages_retried = 0
        self.processing_times: List[float] = []
        self.error_counts: Dict[str, int] = {}
        
        logger.info("KafkaService initialized")
    
    async def start(self):
        """Initialize and start Kafka components"""
        if self.is_initialized:
            return
        
        try:
            with performance_timer("kafka_initialization"):
                await self._initialize_components()
                await self._create_topics()
            
            self.is_initialized = True
            app_state.mark_component_ready("kafka")
            
            structured_logger.log_service_call(
                "KafkaService", "start", 0, True,
                bootstrap_servers=self.bootstrap_servers
            )
            
            logger.info("Kafka service started successfully")
            
        except Exception as e:
            app_state.mark_component_failed("kafka")
            structured_logger.log_error(e, {"operation": "kafka_start"})
            logger.error(f"Failed to start Kafka service: {e}")
            raise
    
    async def _initialize_components(self):
        """Initialize Kafka producer, consumer, and admin client"""
        # Producer configuration
        producer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'client_id': 'gigaoffice-producer',
            'acks': 'all',  # Wait for all replicas
            'retries': 3,
            'enable_idempotence': True,
            **self.config.get("producer_config", {})
        }
        
        # Consumer configuration
        consumer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': self.consumer_group,
            'client_id': 'gigaoffice-consumer',
            'auto_offset_reset': self.auto_offset_reset,
            'enable_auto_commit': False,  # Manual commit for better reliability
            'max_poll_records': self.consumer_batch_size,
            **self.config.get("consumer_config", {})
        }
        
        # Admin configuration
        admin_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'client_id': 'gigaoffice-admin'
        }
        
        # Initialize components
        self.producer = AIOKafkaProducer(**producer_config)
        self.consumer = AIOKafkaConsumer(
            self.topic_requests,
            **consumer_config
        )
        self.admin_client = AIOKafkaAdminClient(**admin_config)
        
        # Start components
        await self.producer.start()
        await self.consumer.start()
        await self.admin_client.start()
        
        logger.info("Kafka components initialized")
    
    async def _create_topics(self):
        """Create topics if they don't exist"""
        try:
            topic_config = self.config.get("topic_config", {})
            
            topics = [
                NewTopic(
                    name=self.topic_requests,
                    num_partitions=topic_config.get("num_partitions", 3),
                    replication_factor=topic_config.get("replication_factor", 1)
                ),
                NewTopic(
                    name=self.topic_responses,
                    num_partitions=topic_config.get("num_partitions", 3),
                    replication_factor=topic_config.get("replication_factor", 1)
                ),
                NewTopic(
                    name=self.topic_dlq,
                    num_partitions=1,  # DLQ typically doesn't need partitioning
                    replication_factor=topic_config.get("replication_factor", 1)
                )
            ]
            
            await self.admin_client.create_topics(topics)
            logger.info("Kafka topics created successfully")
            
        except Exception as e:
            # Ignore if topics already exist
            if "already exists" not in str(e).lower() and "topic already exists" not in str(e).lower():
                logger.error(f"Error creating topics: {e}")
                raise
            else:
                logger.info("Kafka topics already exist")
    
    async def send_request(
        self,
        request_id: str,
        user_id: int,
        query: str,
        input_range: str,
        category: str,
        input_data: Optional[List[Dict]] = None,
        priority: int = 0,
        max_retries: int = 3
    ) -> bool:
        """Send request to Kafka queue with enhanced error handling"""
        if not self.is_initialized:
            await self.start()
        
        try:
            with performance_timer("kafka_send_request", request_id=request_id):
                message = QueueMessage(
                    id=request_id,
                    user_id=user_id,
                    priority=priority,
                    query=query,
                    input_range=input_range,
                    category=category,
                    input_data=input_data,
                    max_retries=max_retries
                )
                
                # Add timestamp and metadata
                message_data = message.to_dict()
                message_data.update({
                    "timestamp": datetime.now().isoformat(),
                    "sent_at": time.time()
                })
                
                # Send message
                await self.producer.send_and_wait(
                    topic=self.topic_requests,
                    key=request_id.encode('utf-8'),
                    value=json.dumps(message_data, ensure_ascii=False).encode('utf-8')
                )
                
                self.messages_sent += 1
                
                structured_logger.log_kafka_message(
                    self.topic_requests, "produce", request_id,
                    success=True, priority=priority
                )
                
                logger.info(f"Request {request_id} sent to queue successfully")
                return True
                
        except Exception as e:
            self.messages_failed += 1
            self._increment_error_count("send_request")
            
            structured_logger.log_kafka_message(
                self.topic_requests, "produce", request_id,
                success=False
            )
            structured_logger.log_error(e, {
                "operation": "send_request",
                "request_id": request_id,
                "topic": self.topic_requests
            })
            
            logger.error(f"Failed to send request {request_id} to queue: {e}")
            return False
    
    async def start_consumer(self, message_processor: Callable[[Dict[str, Any]], MessageProcessingResult]):
        """Start message consumer with enhanced processing"""
        if not self.is_initialized:
            await self.start()
        
        self.is_running = True
        self.processing_callbacks['default'] = message_processor
        
        try:
            logger.info(f"Started consuming from topic: {self.topic_requests}")
            
            async for message_batch in self._consume_messages():
                if not self.is_running:
                    break
                
                # Process messages in batch
                await self._process_message_batch(message_batch, message_processor)
                
        except Exception as e:
            structured_logger.log_error(e, {"operation": "start_consumer"})
            logger.error(f"Consumer error: {e}")
        finally:
            logger.info("Consumer stopped")
    
    async def _consume_messages(self):
        """Consume messages with batching support"""
        try:
            async for msg in self.consumer:
                if not self.is_running:
                    break
                
                yield [msg]  # For now, process one message at a time
                
        except KafkaError as e:
            logger.error(f"Kafka consumer error: {e}")
            raise
    
    async def _process_message_batch(self, messages: List, processor: Callable):
        """Process a batch of messages"""
        tasks = []
        
        for msg in messages:
            task = asyncio.create_task(self._process_single_message(msg, processor))
            tasks.append(task)
        
        # Wait for all messages in batch to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Commit offset after successful batch processing
        try:
            await self.consumer.commit()
        except Exception as e:
            logger.error(f"Failed to commit offset: {e}")
    
    async def _process_single_message(self, msg, processor: Callable):
        """Process a single message with retry logic"""
        try:
            # Parse message
            message_data = json.loads(msg.value.decode('utf-8'))
            request_id = message_data.get("id", "unknown")
            
            # Create QueueMessage object
            queue_message = QueueMessage.from_dict(message_data)
            
            with performance_timer("process_message", request_id=request_id):
                logger.info(f"Processing message: {request_id}")
                
                start_time = time.time()
                
                # Call processor
                result = await processor(message_data)
                
                processing_time = time.time() - start_time
                self.processing_times.append(processing_time)
                
                # Handle result
                if isinstance(result, MessageProcessingResult):
                    await self._handle_processing_result(request_id, result)
                else:
                    # Legacy support - convert dict result
                    legacy_result = MessageProcessingResult(
                        success=result.get("success", False),
                        result=result,
                        processing_time=processing_time
                    )
                    await self._handle_processing_result(request_id, legacy_result)
                
                self.messages_received += 1
                
                structured_logger.log_kafka_message(
                    self.topic_requests, "consume", request_id,
                    duration=processing_time, success=True
                )
                
                logger.info(f"Message {request_id} processed successfully in {processing_time:.2f}s")
                
        except json.JSONDecodeError as e:
            await self._handle_message_error(msg, "JSON parsing error", e)
        except Exception as e:
            await self._handle_message_error(msg, "Processing error", e)
    
    async def _handle_processing_result(self, request_id: str, result: MessageProcessingResult):
        """Handle the result of message processing"""
        try:
            # Send response
            await self._send_response(request_id, result)
            
            if not result.success:
                self.messages_failed += 1
                self._increment_error_count("processing_failed")
                
        except Exception as e:
            structured_logger.log_error(e, {
                "operation": "handle_processing_result",
                "request_id": request_id
            })
    
    async def _handle_message_error(self, msg, error_type: str, error: Exception):
        """Handle message processing errors with retry logic"""
        try:
            self.messages_failed += 1
            self._increment_error_count(error_type)
            
            # Try to parse message for retry logic
            try:
                message_data = json.loads(msg.value.decode('utf-8'))
                queue_message = QueueMessage.from_dict(message_data)
                
                if queue_message.increment_retry():
                    # Retry the message
                    await self._retry_message(queue_message)
                    self.messages_retried += 1
                    logger.warning(f"Message {queue_message.id} queued for retry ({queue_message.retry_count}/{queue_message.max_retries})")
                    return
                    
            except (json.JSONDecodeError, KeyError):
                pass  # Cannot parse message, send to DLQ
            
            # Send to DLQ
            await self._send_to_dlq(msg, error_type, str(error))
            
            structured_logger.log_kafka_message(
                self.topic_requests, "process", "unknown",
                success=False
            )
            
        except Exception as dlq_error:
            logger.error(f"Failed to handle message error: {dlq_error}")
    
    async def _retry_message(self, message: QueueMessage):
        """Retry a failed message"""
        try:
            # Add delay before retry
            await asyncio.sleep(min(2 ** message.retry_count, 30))  # Exponential backoff, max 30s
            
            # Send message back to queue
            message_data = message.to_dict()
            message_data["retried_at"] = datetime.now().isoformat()
            
            await self.producer.send_and_wait(
                topic=self.topic_requests,
                key=message.id.encode('utf-8'),
                value=json.dumps(message_data, ensure_ascii=False).encode('utf-8')
            )
            
        except Exception as e:
            logger.error(f"Failed to retry message {message.id}: {e}")
            # If retry fails, it will eventually go to DLQ via normal error handling
    
    async def _send_response(self, request_id: str, result: MessageProcessingResult):
        """Send response to response topic"""
        try:
            response_data = {
                "request_id": request_id,
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "processing_time": result.processing_time,
                "metadata": result.metadata,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.producer.send_and_wait(
                topic=self.topic_responses,
                key=request_id.encode('utf-8'),
                value=json.dumps(response_data, ensure_ascii=False).encode('utf-8')
            )
            
            structured_logger.log_kafka_message(
                self.topic_responses, "produce", request_id,
                success=True
            )
            
        except Exception as e:
            structured_logger.log_error(e, {
                "operation": "send_response",
                "request_id": request_id
            })
            logger.error(f"Failed to send response for {request_id}: {e}")
    
    async def _send_to_dlq(self, msg, error_type: str, error_message: str):
        """Send message to Dead Letter Queue"""
        try:
            dlq_data = {
                "original_topic": msg.topic,
                "original_partition": msg.partition,
                "original_offset": msg.offset,
                "original_key": msg.key.decode('utf-8') if msg.key else None,
                "original_value": msg.value.decode('utf-8'),
                "error_type": error_type,
                "error_message": error_message,
                "timestamp": datetime.now().isoformat(),
                "dlq_timestamp": time.time()
            }
            
            await self.producer.send_and_wait(
                topic=self.topic_dlq,
                value=json.dumps(dlq_data, ensure_ascii=False).encode('utf-8')
            )
            
            structured_logger.log_kafka_message(
                self.topic_dlq, "produce", "dlq_message",
                success=True, error_type=error_type
            )
            
            logger.warning(f"Message sent to DLQ: {error_type}")
            
        except Exception as e:
            structured_logger.log_error(e, {"operation": "send_to_dlq"})
            logger.error(f"Failed to send message to DLQ: {e}")
    
    def _increment_error_count(self, error_type: str):
        """Increment error count for monitoring"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def stop_consumer(self):
        """Stop message consumer"""
        self.is_running = False
        logger.info("Consumer stop requested")
    
    async def cleanup(self):
        """Clean up Kafka resources"""
        try:
            self.stop_consumer()
            
            # Give consumer time to finish current processing
            await asyncio.sleep(1.0)
            
            # Stop components
            if self.producer:
                await self.producer.stop()
            
            if self.consumer:
                await self.consumer.stop()
            
            if self.admin_client:
                await self.admin_client.close()
            
            self.is_initialized = False
            
            structured_logger.log_service_call(
                "KafkaService", "cleanup", 0, True
            )
            
            logger.info("Kafka service cleaned up successfully")
            
        except Exception as e:
            structured_logger.log_error(e, {"operation": "cleanup"})
            logger.error(f"Error during Kafka cleanup: {e}")
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        recent_processing_times = self.processing_times[-100:]  # Last 100 messages
        
        return {
            "messages": {
                "sent": self.messages_sent,
                "received": self.messages_received,
                "failed": self.messages_failed,
                "retried": self.messages_retried
            },
            "performance": {
                "avg_processing_time": sum(recent_processing_times) / len(recent_processing_times) if recent_processing_times else 0,
                "max_processing_time": max(recent_processing_times) if recent_processing_times else 0,
                "min_processing_time": min(recent_processing_times) if recent_processing_times else 0
            },
            "error_counts": dict(self.error_counts),
            "configuration": {
                "bootstrap_servers": self.bootstrap_servers,
                "consumer_group": self.consumer_group,
                "topics": {
                    "requests": self.topic_requests,
                    "responses": self.topic_responses,
                    "dlq": self.topic_dlq
                }
            },
            "status": {
                "initialized": self.is_initialized,
                "running": self.is_running
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        try:
            error_rate = (self.messages_failed / max(1, self.messages_sent + self.messages_received)) * 100
            
            status = "healthy"
            if not self.is_initialized:
                status = "initializing"
            elif error_rate > 10:  # More than 10% error rate
                status = "degraded"
            elif not self.is_running:
                status = "stopped"
            
            return {
                "status": status,
                "initialized": self.is_initialized,
                "consumer_running": self.is_running,
                "error_rate_percent": error_rate,
                "bootstrap_servers": self.bootstrap_servers,
                "topics_status": "configured",
                "last_message_time": max(self.processing_times) if self.processing_times else None
            }
            
        except Exception as e:
            structured_logger.log_error(e, {"operation": "get_health_status"})
            return {
                "status": "unhealthy",
                "error": str(e),
                "initialized": self.is_initialized
            }


# Global service instance
kafka_service = KafkaService()