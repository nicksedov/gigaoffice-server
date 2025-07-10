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
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import KafkaError
from loguru import logger
from dataclasses import dataclass
from resource_loader import resource_loader

@dataclass
class QueueMessage:
    """Сообщение в очереди"""
    id: str
    user_id: int
    priority: int
    query: str
    input_range: str
    output_range: str
    input_data: Optional[List[Dict]] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

class KafkaService:
    """Сервис для работы с Apache Kafka через aiokafka"""
    
    def __init__(self):
        # Kafka configuration
        config = resource_loader.get_config("kafka_config")
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", config.get("bootstrap_servers"))
        self.topic_requests = os.getenv("KAFKA_TOPIC_REQUESTS", config["topics"]["requests"])
        self.topic_responses = os.getenv("KAFKA_TOPIC_RESPONSES", config["topics"]["responses"])
        self.topic_dlq = os.getenv("KAFKA_TOPIC_DLQ", config["topics"]["dlq"])
        
        # Consumer group settings
        self.consumer_group = os.getenv("KAFKA_CONSUMER_GROUP", config["consumer_group"])
        
        # Queue settings
        self.max_queue_size = int(os.getenv("MAX_QUEUE_SIZE", config["max_queue_size"]))
        self.max_processing_time = int(os.getenv("MAX_PROCESSING_TIME", config["max_processing_time"]))
        
        # Initialize components
        self.producer = None
        self.consumer = None
        self.admin_client = None
        self.is_running = False
        self.processing_callbacks = {}
        
        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_failed = 0
        self.processing_times = []
        
        # Инициализация будет выполнена в start()
        self._initialized = False
    
    async def start(self):
        """Инициализация Kafka компонентов"""
        if self._initialized:
            return
            
        config = resource_loader.get_config("kafka_config")
        try:
            # Producer configuration
            producer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'client_id': 'gigaoffice-producer',
                **config.get("producer_config", {})
            }
            
            # Consumer configuration  
            consumer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'group_id': self.consumer_group,
                'client_id': 'gigaoffice-consumer',
                **config.get("consumer_config", {})
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
            
            # Create topics if they don't exist
            await self._create_topics()
            
            self._initialized = True
            logger.info("Kafka service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka service: {e}")
            raise
    
    async def _create_topics(self):
        """Создание топиков если они не существуют"""
        try:
            topics = [
                NewTopic(
                    name=self.topic_requests,
                    num_partitions=3,
                    replication_factor=1
                ),
                NewTopic(
                    name=self.topic_responses,
                    num_partitions=3,
                    replication_factor=1
                ),
                NewTopic(
                    name=self.topic_dlq,
                    num_partitions=1,
                    replication_factor=1
                )
            ]
            
            # Создаем топики
            await self.admin_client.create_topics(topics)
            logger.info("Topics created successfully")
            
        except Exception as e:
            # Игнорируем ошибку если топики уже существуют
            if "already exists" not in str(e).lower():
                logger.error(f"Error creating topics: {e}")

    async def send_request(
        self, 
        request_id: str, 
        user_id: int, 
        query: str,
        input_range: str,
        output_range: str, 
        input_data: Optional[List[Dict]] = None,
        priority: int = 0
    ) -> bool:
        """
        Отправка запроса в очередь Kafka
        """
        try:
            if not self._initialized:
                await self.start()
                
            message = QueueMessage(
                id=request_id,
                user_id=user_id,
                priority=priority,
                input_range=input_range,
                output_range=output_range,
                query=query,
                input_data=input_data
            )
            
            message_data = {
                "id": message.id,
                "user_id": message.user_id,
                "priority": message.priority,
                "query": message.query,
                "input_range": message.input_range,
                "output_range": message.output_range, 
                "input_data": message.input_data,
                "created_at": message.created_at,
                "timestamp": datetime.now().isoformat()
            }
            
            # Отправляем сообщение
            await self.producer.send_and_wait(
                topic=self.topic_requests,
                key=request_id.encode('utf-8'),
                value=json.dumps(message_data, ensure_ascii=False).encode('utf-8')
            )
            
            self.messages_sent += 1
            logger.info(f"Request {request_id} sent to queue successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send request {request_id} to queue: {e}")
            self.messages_failed += 1
            return False

    async def start_consumer(self, message_processor: Callable):
        """
        Запуск потребителя сообщений
        """
        if not self._initialized:
            await self.start()
            
        self.is_running = True
        self.processing_callbacks['default'] = message_processor
        
        try:
            logger.info(f"Started consuming from topic: {self.topic_requests}")
            
            async for msg in self.consumer:
                if not self.is_running:
                    break
                    
                try:
                    # Обрабатываем сообщение
                        await self._process_message(msg, message_processor)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self._send_to_dlq(msg, str(e))
                    
        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
        finally:
            logger.info("Consumer stopped")

    async def _process_message(self, msg, processor: Callable):
        """Обработка одного сообщения"""
        try:
            # Парсим сообщение
            message_data = json.loads(msg.value.decode('utf-8'))
            request_id = message_data.get("id")
            
            logger.info(f"Processing message: {request_id}")
            start_time = time.time()
            
            # Вызываем обработчик
            result = await processor(message_data)
            
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            
            # Отправляем ответ
            await self._send_response(request_id, result, processing_time)
            
            # Подтверждаем обработку сообщения
            await self.consumer.commit()
            
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
            
            await self.producer.send_and_wait(
                topic=self.topic_responses,
                key=request_id.encode('utf-8'),
                value=json.dumps(response_data, ensure_ascii=False).encode('utf-8')
            )
            
        except Exception as e:
            logger.error(f"Failed to send response for {request_id}: {e}")

    async def _send_to_dlq(self, msg, error_reason: str):
        """Отправка сообщения в Dead Letter Queue"""
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
            
            await self.producer.send_and_wait(
                topic=self.topic_dlq,
                value=json.dumps(dlq_data, ensure_ascii=False).encode('utf-8')
            )
            
            logger.warning(f"Message sent to DLQ: {error_reason}")
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")

    def stop_consumer(self):
        """Остановка потребителя"""
        self.is_running = False
        logger.info("Consumer stop requested")

    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            self.stop_consumer()
            
            if self.producer:
                await self.producer.stop()
                
            if self.consumer:
                await self.consumer.stop()
                
            if self.admin_client:
                await self.admin_client.close()
                
            logger.info("Kafka service cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during Kafka cleanup: {e}")

    def get_queue_info(self) -> Dict[str, Any]:
        """Получение информации об очереди"""
        try:
            queue_info = {
                "topics": {
                    "requests": self.topic_requests,
                    "responses": self.topic_responses,
                    "dlq": self.topic_dlq
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
            return {
                "status": "healthy" if self._initialized else "initializing",
                "bootstrap_servers": self.bootstrap_servers,
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