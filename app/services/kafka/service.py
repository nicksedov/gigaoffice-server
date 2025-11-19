"""
GigaOffice Kafka Service
Сервис для работы с Apache Kafka для балансировки нагрузки и очередей
"""

import os
import json
import time
import ssl
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from loguru import logger
from dataclasses import dataclass, field

# Import custom JSON encoder
from app.utils.json_encoder import DateTimeEncoder

@dataclass
class QueueMessage:
    """Сообщение в очереди"""
    id: str
    user_id: int
    priority: int
    query: str
    input_range: str
    category: str
    input_data: Optional[List[Dict]] = None
    created_at: float = field(default_factory=time.time)

class KafkaService:
    """Сервис для работы с Apache Kafka через aiokafka"""
    
    def __init__(self):
        # Kafka configuration from environment variables
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic_requests = os.getenv("KAFKA_TOPIC_REQUESTS", "gigaoffice-requests")
        self.topic_responses = os.getenv("KAFKA_TOPIC_RESPONSES", "gigaoffice-responses")
        self.topic_dlq = os.getenv("KAFKA_TOPIC_DLQ", "gigaoffice-dlq")
        
        # Consumer group settings
        self.consumer_group = os.getenv("KAFKA_CONSUMER_GROUP", "gigaoffice-consumers")
        
        # Queue settings
        self.max_queue_size = int(os.getenv("KAFKA_MAX_QUEUE_SIZE", "1000"))
        self.max_processing_time = int(os.getenv("KAFKA_MAX_PROCESSING_TIME", "300"))
        
        # SSL configuration
        self.use_ssl = os.getenv("KAFKA_USE_SSL", "false").lower() == "true"
        self.ssl_cafile = os.getenv("KAFKA_SSL_CAFILE")
        self.ssl_certfile = os.getenv("KAFKA_SSL_CERTFILE")
        self.ssl_keyfile = os.getenv("KAFKA_SSL_KEYFILE")
        self.ssl_password = os.getenv("KAFKA_SSL_PASSWORD")
        
        # Initialize components
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.admin_client: Optional[AIOKafkaAdminClient] = None
        self.is_running = False
        self.processing_callbacks = {}
        
        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_failed = 0
        self.processing_times = []
        
        # Инициализация будет выполнена в start()
        self._initialized = False
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Создание SSL контекста для подключения к Kafka"""
        if not self.use_ssl:
            return None
            
        try:
            # Создаем SSL контекст с проверкой сертификата
            logger.info(f"Creating SSL context for Kafka connection: CA file - {self.ssl_cafile}")
            ssl_context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=self.ssl_cafile
            )
            
            # Загружаем клиентский сертификат и ключ если они предоставлены
            if self.ssl_certfile and self.ssl_keyfile:
                logger.info(f"Loading client certificate and key for Kafka connection: certificate - {self.ssl_certfile}, private key - {self.ssl_keyfile}")
                ssl_context.load_cert_chain(
                    certfile=self.ssl_certfile,
                    keyfile=self.ssl_keyfile,
                    password=self.ssl_password.encode() if self.ssl_password else None
                )
            
            return ssl_context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            raise
    
    async def start(self):
        """Инициализация Kafka компонентов"""
        if self._initialized:
            return
            
        try:
            # Создаем SSL контекст если нужен
            ssl_context = self._create_ssl_context()
            
            # Producer configuration from environment variables
            producer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'client_id': 'gigaoffice-producer',
                'acks': os.getenv("KAFKA_PRODUCER_ACKS", "all"),
                'retry_backoff_ms': int(os.getenv("KAFKA_PRODUCER_RETRY_BACKOFF_MS", "100")),
                'linger_ms': int(os.getenv("KAFKA_PRODUCER_LINGER_MS", "1")),
                'compression_type': os.getenv("KAFKA_PRODUCER_COMPRESSION_TYPE", "gzip")
            }
            
            # Add SSL configuration if enabled
            if self.use_ssl and ssl_context:
                producer_config['security_protocol'] = 'SSL'
                producer_config['ssl_context'] = ssl_context
            
            # Consumer configuration from environment variables
            consumer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'group_id': self.consumer_group,
                'client_id': 'gigaoffice-consumer',
                'auto_offset_reset': os.getenv("KAFKA_CONSUMER_AUTO_OFFSET_RESET", "earliest"),
                'enable_auto_commit': os.getenv("KAFKA_CONSUMER_ENABLE_AUTO_COMMIT", "false").lower() == "true",
                'max_poll_records': int(os.getenv("KAFKA_CONSUMER_MAX_POLL_RECORDS", "500")),
                'session_timeout_ms': int(os.getenv("KAFKA_CONSUMER_SESSION_TIMEOUT_MS", "10000")),
                'heartbeat_interval_ms': int(os.getenv("KAFKA_CONSUMER_HEARTBEAT_INTERVAL_MS", "3000"))
            }
            
            # Add SSL configuration if enabled
            if self.use_ssl and ssl_context:
                consumer_config['security_protocol'] = 'SSL'
                consumer_config['ssl_context'] = ssl_context
            
            # Admin configuration with explicit integer parameters
            admin_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'client_id': 'gigaoffice-admin',
                'request_timeout_ms': 30000,
                'connections_max_idle_ms': 540000,
                'retry_backoff_ms': 100,
                'metadata_max_age_ms': 300000
            }
            
            # Add SSL configuration if enabled
            if self.use_ssl and ssl_context:
                admin_config['security_protocol'] = 'SSL'
                admin_config['ssl_context'] = ssl_context
            
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
        # Check if admin client is initialized
        if not self.admin_client:
            logger.warning("Admin client not initialized, skipping topic creation")
            return
            
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
        category: str,
        input_data: Optional[List[Dict]] = None,
        priority: int = 0
    ) -> bool:
        """
        Отправка запроса в очередь Kafka
        """
        try:
            if not self._initialized:
                await self.start()
                
            # Check if producer is initialized
            if not self.producer:
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
            
            # Отправляем сообщение используя custom encoder
            await self.producer.send_and_wait(
                topic=self.topic_requests,
                key=request_id.encode('utf-8'),
                value=json.dumps(message_data, ensure_ascii=False, cls=DateTimeEncoder).encode('utf-8')
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
            
        # Check if consumer is initialized
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
            
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
        # Check if consumer is initialized
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
            
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
        # Check if producer is initialized
        if not self.producer:
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
            
            await self.producer.send_and_wait(
                topic=self.topic_responses,
                key=request_id.encode('utf-8'),
                value=json.dumps(response_data, ensure_ascii=False, cls=DateTimeEncoder).encode('utf-8')
            )
            
        except Exception as e:
            logger.error(f"Failed to send response for {request_id}: {e}")

    async def _send_to_dlq(self, msg, error_reason: str):
        """Отправка сообщения в Dead Letter Queue"""
        # Check if producer is initialized
        if not self.producer:
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
            
            await self.producer.send_and_wait(
                topic=self.topic_dlq,
                value=json.dumps(dlq_data, ensure_ascii=False, cls=DateTimeEncoder).encode('utf-8')
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

# Create global instance
kafka_service = KafkaService()