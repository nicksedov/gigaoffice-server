"""
GigaOffice Kafka Service
Сервис для работы с Apache Kafka для балансировки нагрузки и очередей
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
from loguru import logger
import threading
from queue import Queue
from dataclasses import dataclass

@dataclass
class QueueMessage:
    """Сообщение в очереди"""
    id: str
    user_id: int
    priority: int
    query: str
    input_data: Optional[List[Dict]] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

class KafkaService:
    """Сервис для работы с Apache Kafka"""
    
    def __init__(self):
        # Kafka configuration
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic_requests = os.getenv("KAFKA_TOPIC_REQUESTS", "gigaoffice-requests")
        self.topic_responses = os.getenv("KAFKA_TOPIC_RESPONSES", "gigaoffice-responses")
        self.topic_dlq = os.getenv("KAFKA_TOPIC_DLQ", "gigaoffice-dlq")  # Dead Letter Queue
        
        # Consumer group settings
        self.consumer_group = os.getenv("KAFKA_CONSUMER_GROUP", "gigaoffice-processors")
        
        # Queue settings
        self.max_queue_size = int(os.getenv("MAX_QUEUE_SIZE", "1000"))
        self.max_processing_time = int(os.getenv("MAX_PROCESSING_TIME", "300"))  # 5 minutes
        
        # Initialize components
        self.producer = None
        self.consumer = None
        self.admin_client = None
        self.is_running = False
        self.processing_callbacks = {}
        
        # Internal queues for priority handling
        self.priority_queue = Queue()
        self.processing_queue = Queue()
        
        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_failed = 0
        self.processing_times = []
        
        self._init_kafka()
    
    def _init_kafka(self):
        """Инициализация Kafka компонентов"""
        try:
            # Common configuration
            common_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': 'gigaoffice-service'
            }
            
            # Producer configuration
            producer_config = {
                **common_config,
                'acks': 'all',  # Wait for all replicas
                'retries': 3,
                'enable.idempotence': True,
                'compression.type': 'snappy',
                'batch.size': 16384,
                'linger.ms': 10,
                'max.in.flight.requests.per.connection': 1
            }
            
            # Consumer configuration
            consumer_config = {
                **common_config,
                'group.id': self.consumer_group,
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,
                'max.poll.interval.ms': 300000,  # 5 minutes
                'session.timeout.ms': 30000,
                'partition.assignment.strategy': 'roundrobin'
            }
            
            # Initialize components
            self.producer = Producer(producer_config)
            self.consumer = Consumer(consumer_config)
            self.admin_client = AdminClient(common_config)
            
            # Create topics if they don't exist
            self._create_topics()
            
            logger.info("Kafka service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka service: {e}")
            raise
    
    def _create_topics(self):
        """Создание топиков если они не существуют"""
        try:
            topics = [
                NewTopic(self.topic_requests, num_partitions=3, replication_factor=1),
                NewTopic(self.topic_responses, num_partitions=3, replication_factor=1),
                NewTopic(self.topic_dlq, num_partitions=1, replication_factor=1)
            ]
            
            # Check existing topics
            existing_topics = self.admin_client.list_topics(timeout=10).topics
            topics_to_create = [topic for topic in topics if topic.topic not in existing_topics]
            
            if topics_to_create:
                fs = self.admin_client.create_topics(topics_to_create)
                
                for topic, f in fs.items():
                    try:
                        f.result()  # The result itself is None
                        logger.info(f"Topic '{topic}' created successfully")
                    except Exception as e:
                        logger.warning(f"Failed to create topic '{topic}': {e}")
            
        except Exception as e:
            logger.error(f"Error creating topics: {e}")
    
    async def send_request(
        self, 
        request_id: str, 
        user_id: int, 
        query: str, 
        input_data: Optional[List[Dict]] = None,
        priority: int = 0
    ) -> bool:
        """
        Отправка запроса в очередь Kafka
        
        Args:
            request_id: Уникальный ID запроса
            user_id: ID пользователя
            query: Текст запроса
            input_data: Входные данные
            priority: Приоритет запроса (выше = важнее)
        
        Returns:
            bool: Успешность отправки
        """
        try:
            message = QueueMessage(
                id=request_id,
                user_id=user_id,
                priority=priority,
                query=query,
                input_data=input_data
            )
            
            message_data = {
                "id": message.id,
                "user_id": message.user_id,
                "priority": message.priority,
                "query": message.query,
                "input_data": message.input_data,
                "created_at": message.created_at,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to Kafka
            self.producer.produce(
                topic=self.topic_requests,
                key=request_id,
                value=json.dumps(message_data, ensure_ascii=False),
                callback=self._delivery_callback
            )
            
            # Flush to ensure delivery
            self.producer.flush(timeout=10)
            
            self.messages_sent += 1
            logger.info(f"Request {request_id} sent to queue successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send request {request_id} to queue: {e}")
            self.messages_failed += 1
            return False
    
    def _delivery_callback(self, err, msg):
        """Callback для подтверждения доставки сообщения"""
        if err:
            logger.error(f"Message delivery failed: {err}")
            self.messages_failed += 1
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")
    
    async def start_consumer(self, message_processor: Callable):
        """
        Запуск потребителя сообщений
        
        Args:
            message_processor: Функция для обработки сообщений
        """
        self.is_running = True
        self.processing_callbacks['default'] = message_processor
        
        try:
            self.consumer.subscribe([self.topic_requests])
            logger.info(f"Started consuming from topic: {self.topic_requests}")
            
            while self.is_running:
                try:
                    # Poll for messages
                    msg = self.consumer.poll(timeout=1.0)
                    
                    if msg is None:
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            logger.debug(f"End of partition reached {msg.topic()} [{msg.partition()}] @ {msg.offset()}")
                        else:
                            logger.error(f"Consumer error: {msg.error()}")
                        continue
                    
                    # Process message
                    await self._process_message(msg, message_processor)
                    
                except KafkaException as e:
                    logger.error(f"Kafka exception in consumer: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
                except Exception as e:
                    logger.error(f"Unexpected error in consumer: {e}")
                    await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
        finally:
            self.consumer.close()
            logger.info("Consumer stopped")
    
    async def _process_message(self, msg, processor: Callable):
        """Обработка одного сообщения"""
        try:
            # Parse message
            message_data = json.loads(msg.value().decode('utf-8'))
            request_id = message_data.get("id")
            
            logger.info(f"Processing message: {request_id}")
            start_time = time.time()
            
            # Call processor
            result = await processor(message_data)
            
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            
            # Send response
            await self._send_response(request_id, result, processing_time)
            
            # Commit offset
            self.consumer.commit(asynchronous=False)
            
            self.messages_received += 1
            logger.info(f"Message {request_id} processed successfully in {processing_time:.2f}s")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            await self._send_to_dlq(msg, "JSON parsing error")
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            await self._send_to_dlq(msg, str(e))
    
    async def _send_response(self, request_id: str, result: Dict[str, Any], processing_time: float):
        """Отправка ответа в топик ответов"""
        try:
            response_data = {
                "request_id": request_id,
                "result": result,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "status": "completed" if result.get("success") else "failed"
            }
            
            self.producer.produce(
                topic=self.topic_responses,
                key=request_id,
                value=json.dumps(response_data, ensure_ascii=False),
                callback=self._delivery_callback
            )
            
            self.producer.flush(timeout=5)
            
        except Exception as e:
            logger.error(f"Failed to send response for {request_id}: {e}")
    
    async def _send_to_dlq(self, msg, error_reason: str):
        """Отправка сообщения в Dead Letter Queue"""
        try:
            dlq_data = {
                "original_topic": msg.topic(),
                "original_partition": msg.partition(),
                "original_offset": msg.offset(),
                "original_key": msg.key().decode('utf-8') if msg.key() else None,
                "original_value": msg.value().decode('utf-8'),
                "error_reason": error_reason,
                "timestamp": datetime.now().isoformat()
            }
            
            self.producer.produce(
                topic=self.topic_dlq,
                value=json.dumps(dlq_data, ensure_ascii=False),
                callback=self._delivery_callback
            )
            
            self.producer.flush(timeout=5)
            logger.warning(f"Message sent to DLQ: {error_reason}")
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")
    
    def stop_consumer(self):
        """Остановка потребителя"""
        self.is_running = False
        logger.info("Consumer stop requested")
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Получение информации об очереди"""
        try:
            # Get topic metadata
            metadata = self.admin_client.list_topics(timeout=5)
            
            queue_info = {
                "topics": {
                    "requests": self.topic_requests in metadata.topics,
                    "responses": self.topic_responses in metadata.topics,
                    "dlq": self.topic_dlq in metadata.topics
                },
                "statistics": {
                    "messages_sent": self.messages_sent,
                    "messages_received": self.messages_received,
                    "messages_failed": self.messages_failed,
                    "avg_processing_time": sum(self.processing_times[-100:]) / len(self.processing_times[-100:]) if self.processing_times else 0
                },
                "status": "running" if self.is_running else "stopped"
            }
            
            return queue_info
            
        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Проверка состояния Kafka сервиса"""
        try:
            # Try to get metadata as health check
            start_time = time.time()
            metadata = self.admin_client.list_topics(timeout=5)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "bootstrap_servers": self.bootstrap_servers,
                "topics_available": len(metadata.topics),
                "consumer_running": self.is_running,
                "statistics": {
                    "messages_sent": self.messages_sent,
                    "messages_received": self.messages_received,
                    "messages_failed": self.messages_failed
                }
            }
            
        except Exception as e:
            logger.error(f"Kafka health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "bootstrap_servers": self.bootstrap_servers
            }
    
    def cleanup(self):
        """Очистка ресурсов"""
        try:
            self.stop_consumer()
            
            if self.producer:
                self.producer.flush(timeout=10)
                
            if self.consumer:
                self.consumer.close()
                
            logger.info("Kafka service cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during Kafka cleanup: {e}")

# Create global instance
kafka_service = KafkaService()