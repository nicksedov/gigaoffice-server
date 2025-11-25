"""
GigaOffice Kafka Service
Сервис для работы с Apache Kafka для балансировки нагрузки и очередей
"""

import os
import json
import time
import ssl
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union, Set
from datetime import datetime
from pathlib import Path
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import KafkaError, TopicAlreadyExistsError, GroupCoordinatorNotAvailableError
from loguru import logger
from dataclasses import dataclass, field
from enum import Enum

# Import custom JSON encoder
from app.utils.json_encoder import DateTimeEncoder

class ErrorType(Enum):
    """Классификация ошибок создания топиков"""
    EXPECTED = "expected"  # Нормальное состояние, не требует внимания
    RETRIABLE = "retriable"  # Временная ошибка, можно повторить
    FATAL = "fatal"  # Критическая ошибка, требует вмешательства

@dataclass
class TopicConfig:
    """Конфигурация топика"""
    name: str
    num_partitions: int
    replication_factor: int

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
        
        # Topic auto-creation configuration
        self.topic_auto_create = os.getenv("KAFKA_TOPIC_AUTO_CREATE", "true").lower() == "true"
        self.topic_creation_timeout = int(os.getenv("KAFKA_TOPIC_CREATION_TIMEOUT", "30"))
        self.topic_creation_retries = int(os.getenv("KAFKA_TOPIC_CREATION_RETRIES", "3"))
        self.topic_creation_retry_delay = int(os.getenv("KAFKA_TOPIC_CREATION_RETRY_DELAY", "2"))
        
        # Consumer initialization retry configuration
        self.consumer_init_retries = int(os.getenv("KAFKA_CONSUMER_INIT_RETRIES", "5"))
        self.consumer_init_delay = int(os.getenv("KAFKA_CONSUMER_INIT_DELAY", "2"))
        self.consumer_init_max_delay = int(os.getenv("KAFKA_CONSUMER_INIT_MAX_DELAY", "30"))
        self.ssl_verify_certificates = os.getenv("KAFKA_SSL_VERIFY_CERTIFICATES", "true").lower() == "true"
        self.startup_health_check = os.getenv("KAFKA_STARTUP_HEALTH_CHECK", "true").lower() == "true"
        self.coordinator_wait_timeout = int(os.getenv("KAFKA_COORDINATOR_WAIT_TIMEOUT", "60"))
        
        # Post-creation delay configuration
        self.post_creation_delay = int(os.getenv("KAFKA_POST_CREATION_DELAY", "3"))
        # Enforce bounds: 0-10 seconds
        self.post_creation_delay = max(0, min(self.post_creation_delay, 10))
        
        # Topic configuration from environment variables
        self.topic_requests_partitions = int(os.getenv("KAFKA_TOPIC_REQUESTS_PARTITIONS", "3"))
        self.topic_requests_replication = int(os.getenv("KAFKA_TOPIC_REQUESTS_REPLICATION", "1"))
        self.topic_responses_partitions = int(os.getenv("KAFKA_TOPIC_RESPONSES_PARTITIONS", "3"))
        self.topic_responses_replication = int(os.getenv("KAFKA_TOPIC_RESPONSES_REPLICATION", "1"))
        self.topic_dlq_partitions = int(os.getenv("KAFKA_TOPIC_DLQ_PARTITIONS", "1"))
        self.topic_dlq_replication = int(os.getenv("KAFKA_TOPIC_DLQ_REPLICATION", "1"))
        
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
        self.topics_created = 0
        self.topic_creation_errors = 0
        self.last_topic_verification: Optional[datetime] = None
        self.consumer_init_attempts = 0
        self.connection_errors_total = 0
        
        # Инициализация будет выполнена в start()
        self._initialized = False
    
    def _validate_ssl_certificates(self) -> None:
        """Валидация SSL сертификатов перед использованием"""
        if not self.use_ssl or not self.ssl_verify_certificates:
            return
        
        logger.info("Validating SSL certificates")
        
        # Check CA certificate file
        if self.ssl_cafile:
            ca_path = Path(self.ssl_cafile)
            if not ca_path.exists():
                raise FileNotFoundError(f"CA certificate file not found: {self.ssl_cafile}")
            if not ca_path.is_file():
                raise ValueError(f"CA certificate path is not a file: {self.ssl_cafile}")
            logger.info(f"✓ CA certificate file exists: {self.ssl_cafile}")
        else:
            raise ValueError("SSL is enabled but KAFKA_SSL_CAFILE is not set")
        
        # Check client certificate file if provided
        if self.ssl_certfile:
            cert_path = Path(self.ssl_certfile)
            if not cert_path.exists():
                raise FileNotFoundError(f"Client certificate file not found: {self.ssl_certfile}")
            if not cert_path.is_file():
                raise ValueError(f"Client certificate path is not a file: {self.ssl_certfile}")
            logger.info(f"✓ Client certificate file exists: {self.ssl_certfile}")
        
        # Check private key file if provided
        if self.ssl_keyfile:
            key_path = Path(self.ssl_keyfile)
            if not key_path.exists():
                raise FileNotFoundError(f"Private key file not found: {self.ssl_keyfile}")
            if not key_path.is_file():
                raise ValueError(f"Private key path is not a file: {self.ssl_keyfile}")
            logger.info(f"✓ Private key file exists: {self.ssl_keyfile}")
        
        logger.info("SSL certificate validation completed successfully")
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Создание SSL контекста для подключения к Kafka"""
        if not self.use_ssl:
            return None
            
        try:
            # Validate certificates first
            self._validate_ssl_certificates()
            
            # Создаем SSL контекст с проверкой сертификата
            logger.info("Creating SSL context for Kafka connection")
            logger.info(f"  Trusted CA file: {self.ssl_cafile}")
            ssl_context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=self.ssl_cafile
            )
            
            # Загружаем клиентский сертификат и ключ если они предоставлены
            if self.ssl_certfile and self.ssl_keyfile:
                logger.info("Loading client certificate and key for Kafka connection") 
                logger.info(f"  Client certificate: {self.ssl_certfile}")
                logger.info(f"  Private key: {self.ssl_keyfile}")
                ssl_context.load_cert_chain(
                    certfile=self.ssl_certfile,
                    keyfile=self.ssl_keyfile,
                    password=self.ssl_password.encode() if self.ssl_password else None
                )
            
            logger.info(f"SSL context created successfully (protocol: {ssl_context.protocol})")
            return ssl_context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            raise
    
    async def _verify_broker_health(self) -> None:
        """Проверка доступности брокера Kafka"""
        if not self.admin_client:
            logger.warning("Admin client not initialized for health check")
            return
        
        logger.info("Verifying Kafka broker health")
        
        try:
            # Get cluster metadata
            metadata = await asyncio.wait_for(
                self.admin_client.list_topics(),
                timeout=self.coordinator_wait_timeout
            )
            
            broker_count = len(metadata)
            logger.info(f"✓ Kafka cluster is healthy: {broker_count} topics found")
            logger.info(f"  Bootstrap servers: {self.bootstrap_servers}")
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout connecting to Kafka broker after {self.coordinator_wait_timeout}s"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to verify Kafka broker health: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    async def _start_consumer_with_retry(self) -> None:
        """Запуск consumer с логикой повторных попыток"""
        if not self.consumer:
            raise ValueError("Consumer not initialized")
        
        retry_count = 0
        current_delay = self.consumer_init_delay
        
        while retry_count <= self.consumer_init_retries:
            try:
                self.consumer_init_attempts += 1
                
                if retry_count > 0:
                    logger.info(
                        f"Attempting to start consumer (attempt {retry_count + 1}/{self.consumer_init_retries + 1})"
                    )
                
                # Try to start consumer
                await asyncio.wait_for(
                    self.consumer.start(),
                    timeout=self.coordinator_wait_timeout
                )
                
                logger.info("✓ Consumer connected successfully")
                return
                
            except GroupCoordinatorNotAvailableError as e:
                self.connection_errors_total += 1
                logger.warning(
                    f"Group coordinator not available (attempt {retry_count + 1}/{self.consumer_init_retries + 1}): {e}"
                )
                
                if retry_count < self.consumer_init_retries:
                    logger.info(f"Waiting {current_delay}s before retry...")
                    await asyncio.sleep(current_delay)
                    # Exponential backoff with max delay cap
                    current_delay = min(current_delay * 2, self.consumer_init_max_delay)
                    retry_count += 1
                else:
                    error_msg = (
                        f"Failed to start consumer after {self.consumer_init_retries + 1} attempts. "
                        f"Group coordinator not available. "
                        f"Please verify: \n"
                        f"  1. Kafka broker is running at {self.bootstrap_servers}\n"
                        f"  2. SSL certificates are valid and trusted\n"
                        f"  3. Network connectivity to Kafka cluster\n"
                        f"  4. Consumer group '{self.consumer_group}' is not locked"
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
            
            except asyncio.TimeoutError:
                self.connection_errors_total += 1
                logger.error(
                    f"Timeout starting consumer (attempt {retry_count + 1}/{self.consumer_init_retries + 1})"
                )
                
                if retry_count < self.consumer_init_retries:
                    logger.info(f"Waiting {current_delay}s before retry...")
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, self.consumer_init_max_delay)
                    retry_count += 1
                else:
                    error_msg = (
                        f"Timeout starting consumer after {self.coordinator_wait_timeout}s. "
                        f"Check network connectivity and broker availability."
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)
            
            except KafkaError as e:
                self.connection_errors_total += 1
                error_str = str(e).lower()
                
                # Classify error type
                is_ssl_error = any(keyword in error_str for keyword in ['ssl', 'certificate', 'handshake'])
                is_network_error = any(keyword in error_str for keyword in ['connection', 'timeout', 'network'])
                
                if is_ssl_error:
                    error_msg = (
                        f"SSL connection error: {e}\n"
                        f"Please verify:\n"
                        f"  1. CA certificate is valid: {self.ssl_cafile}\n"
                        f"  2. Client certificate is valid: {self.ssl_certfile}\n"
                        f"  3. Private key is valid: {self.ssl_keyfile}\n"
                        f"  4. Certificate hostname matches broker address\n"
                        f"  5. Certificates are not expired"
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
                
                if is_network_error and retry_count < self.consumer_init_retries:
                    logger.warning(
                        f"Network error starting consumer (attempt {retry_count + 1}/{self.consumer_init_retries + 1}): {e}"
                    )
                    logger.info(f"Waiting {current_delay}s before retry...")
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, self.consumer_init_max_delay)
                    retry_count += 1
                else:
                    error_msg = f"Failed to start consumer: {e}"
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
            
            except Exception as e:
                self.connection_errors_total += 1
                logger.error(f"Unexpected error starting consumer: {e}")
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
            
            # Consumer configuration from environment variables with optimized timeouts for SSL
            consumer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'group_id': self.consumer_group,
                'client_id': 'gigaoffice-consumer',
                'auto_offset_reset': os.getenv("KAFKA_CONSUMER_AUTO_OFFSET_RESET", "earliest"),
                'enable_auto_commit': os.getenv("KAFKA_CONSUMER_ENABLE_AUTO_COMMIT", "false").lower() == "true",
                'max_poll_records': int(os.getenv("KAFKA_CONSUMER_MAX_POLL_RECORDS", "500")),
                'session_timeout_ms': int(os.getenv("KAFKA_CONSUMER_SESSION_TIMEOUT_MS", "30000")),
                'heartbeat_interval_ms': int(os.getenv("KAFKA_CONSUMER_HEARTBEAT_INTERVAL_MS", "10000")),
                'request_timeout_ms': int(os.getenv("KAFKA_CONSUMER_REQUEST_TIMEOUT_MS", "40000")),
                'connections_max_idle_ms': int(os.getenv("KAFKA_CONSUMER_CONNECTIONS_MAX_IDLE_MS", "600000")),
                'metadata_max_age_ms': int(os.getenv("KAFKA_CONSUMER_METADATA_MAX_AGE_MS", "60000"))
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
            
            # Initialize components with staged approach
            # 1. Admin client first for health checks
            logger.info("Initializing Kafka admin client")
            self.admin_client = AIOKafkaAdminClient(**admin_config)
            await self.admin_client.start()
            logger.info("Admin client started successfully")
            
            # 2. Verify broker connectivity if health check enabled
            if self.startup_health_check:
                await self._verify_broker_health()
            
            # 3. Create topics if they don't exist
            topics_created = await self._create_topics()
            
            # 4. Apply stabilization delay if topics were created
            if topics_created and self.post_creation_delay > 0:
                logger.info(
                    f"Topics were created, waiting {self.post_creation_delay}s for "
                    f"Kafka cluster to stabilize (group coordinator election, metadata propagation)"
                )
                await asyncio.sleep(self.post_creation_delay)
                logger.info("Stabilization period completed, continuing with initialization")
            elif topics_created:
                logger.info("Topics were created, but post-creation delay is disabled (0s)")
            
            # 5. Initialize producer
            logger.info("Initializing Kafka producer")
            self.producer = AIOKafkaProducer(**producer_config)
            await self.producer.start()
            logger.info("Producer started successfully")
            
            # 6. Initialize consumer last with retry logic
            logger.info("Initializing Kafka consumer")
            self.consumer = AIOKafkaConsumer(
                self.topic_requests,
                **consumer_config
            )
            await self._start_consumer_with_retry()
            logger.info("Consumer started successfully")
            
            self._initialized = True
            logger.info("Kafka service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka service: {e}")
            raise
    
    def _validate_topic_config(self, topic_config: TopicConfig) -> Optional[str]:
        """Валидация конфигурации топика"""
        # Validate partition count
        if topic_config.num_partitions <= 0:
            return f"Partition count must be greater than 0 for topic {topic_config.name}"
        
        # Validate replication factor
        if topic_config.replication_factor <= 0:
            return f"Replication factor must be greater than 0 for topic {topic_config.name}"
        
        # Validate topic name (basic Kafka naming rules)
        if not topic_config.name or len(topic_config.name) > 249:
            return f"Topic name must be between 1 and 249 characters"
        
        invalid_chars = set('<>:"/\\|?*')
        if any(char in topic_config.name for char in invalid_chars):
            return f"Topic name '{topic_config.name}' contains invalid characters"
        
        return None
    
    async def _get_existing_topics(self) -> Set[str]:
        """Получение списка существующих топиков"""
        if not self.admin_client:
            logger.warning("Admin client not initialized")
            return set()
        
        try:
            metadata = await self.admin_client.list_topics()
            existing_topics = set(metadata)
            logger.debug(f"Found {len(existing_topics)} existing topics in cluster")
            return existing_topics
        except Exception as e:
            logger.error(f"Failed to list existing topics: {e}")
            return set()
    
    async def _verify_topic_created(self, topic_config: TopicConfig) -> bool:
        """Проверка что топик был создан с правильной конфигурацией"""
        if not self.admin_client:
            return False
        
        try:
            # First, try to get detailed cluster metadata
            try:
                # Get cluster metadata using the admin client's internal client
                cluster_metadata = await self.admin_client._client.fetch_all_metadata()
                
                # Check if topic exists in metadata
                if topic_config.name in cluster_metadata.topics():
                    topic_metadata = cluster_metadata.topics()[topic_config.name]
                    
                    # Verify partition count
                    actual_partitions = len(topic_metadata.partitions)
                    if actual_partitions != topic_config.num_partitions:
                        logger.warning(
                            f"Topic {topic_config.name} partition count mismatch: "
                            f"expected {topic_config.num_partitions}, got {actual_partitions}"
                        )
                    
                    logger.info(
                        f"Topic {topic_config.name} verified: "
                        f"{actual_partitions} partitions"
                    )
                    return True
                else:
                    logger.warning(f"Topic {topic_config.name} not found in cluster metadata")
                    return False
                    
            except Exception as metadata_error:
                # Fallback to simple existence check
                logger.debug(f"Detailed metadata retrieval failed for {topic_config.name}: {metadata_error}")
                logger.debug("Falling back to simple existence check")
                
                # Use list_topics() for simple existence verification
                existing_topics = await self.admin_client.list_topics()
                
                if topic_config.name in existing_topics:
                    logger.info(
                        f"Topic {topic_config.name} verified (existence check only, "
                        f"partition count not verified)"
                    )
                    return True
                else:
                    logger.warning(f"Topic {topic_config.name} not found after creation")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to verify topic {topic_config.name}: {e}")
            return False
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Классификация ошибки для определения стратегии обработки"""
        error_str = str(error).lower()
        
        # Expected errors
        if isinstance(error, TopicAlreadyExistsError) or "already exists" in error_str:
            return ErrorType.EXPECTED
        
        # Retriable errors
        retriable_keywords = [
            "timeout", "connection", "unavailable", 
            "leader not available", "network", "broker"
        ]
        if any(keyword in error_str for keyword in retriable_keywords):
            return ErrorType.RETRIABLE
        
        # Fatal errors
        fatal_keywords = [
            "permission", "authorization", "invalid", 
            "capacity", "quota", "denied"
        ]
        if any(keyword in error_str for keyword in fatal_keywords):
            return ErrorType.FATAL
        
        # Default to retriable for unknown errors
        return ErrorType.RETRIABLE
    
    async def _create_single_topic(
        self, 
        topic_config: TopicConfig, 
        retry_attempt: int = 0
    ) -> bool:
        """Создание одного топика с повторными попытками"""
        if not self.admin_client:
            logger.error("Admin client not initialized")
            return False
        
        try:
            new_topic = NewTopic(
                name=topic_config.name,
                num_partitions=topic_config.num_partitions,
                replication_factor=topic_config.replication_factor
            )
            
            logger.info(
                f"Creating topic {topic_config.name} "
                f"(partitions={topic_config.num_partitions}, "
                f"replication={topic_config.replication_factor})"
            )
            
            await asyncio.wait_for(
                self.admin_client.create_topics([new_topic]),
                timeout=self.topic_creation_timeout
            )
            
            self.topics_created += 1
            logger.info(f"Topic {topic_config.name} created successfully")
            
            # Verify topic was created
            if await self._verify_topic_created(topic_config):
                return True
            else:
                logger.warning(f"Topic {topic_config.name} creation could not be verified")
                return True  # Still consider it created
            
        except asyncio.TimeoutError:
            logger.error(
                f"Timeout creating topic {topic_config.name} "
                f"(attempt {retry_attempt + 1}/{self.topic_creation_retries + 1})"
            )
            error_type = ErrorType.RETRIABLE
            
        except Exception as e:
            error_type = self._classify_error(e)
            
            if error_type == ErrorType.EXPECTED:
                logger.info(
                    f"Topic {topic_config.name} already exists, skipping creation"
                )
                return True
            
            elif error_type == ErrorType.RETRIABLE:
                logger.warning(
                    f"Retriable error creating topic {topic_config.name} "
                    f"(attempt {retry_attempt + 1}/{self.topic_creation_retries + 1}): {e}"
                )
            
            else:  # FATAL
                logger.error(
                    f"Fatal error creating topic {topic_config.name}: {e}"
                )
                self.topic_creation_errors += 1
                raise
        
        # Retry logic for retriable errors
        if retry_attempt < self.topic_creation_retries:
            await asyncio.sleep(self.topic_creation_retry_delay)
            return await self._create_single_topic(topic_config, retry_attempt + 1)
        else:
            logger.error(
                f"Failed to create topic {topic_config.name} "
                f"after {self.topic_creation_retries + 1} attempts"
            )
            self.topic_creation_errors += 1
            return False
    
    async def _create_topics(self) -> bool:
        """Создание топиков если они не существуют (улучшенная версия)
        
        Returns:
            bool: True if any topics were created, False if all topics already existed
        """
        # Check if auto-creation is enabled
        if not self.topic_auto_create:
            logger.info("Topic auto-creation is disabled, skipping")
            return False
        
        # Check if admin client is initialized
        if not self.admin_client:
            logger.warning("Admin client not initialized, skipping topic creation")
            return False
        
        start_time = time.time()
        
        try:
            # Define topic configurations
            topic_configs = [
                TopicConfig(
                    name=self.topic_requests,
                    num_partitions=self.topic_requests_partitions,
                    replication_factor=self.topic_requests_replication
                ),
                TopicConfig(
                    name=self.topic_responses,
                    num_partitions=self.topic_responses_partitions,
                    replication_factor=self.topic_responses_replication
                ),
                TopicConfig(
                    name=self.topic_dlq,
                    num_partitions=self.topic_dlq_partitions,
                    replication_factor=self.topic_dlq_replication
                )
            ]
            
            # Validate all topic configurations
            for topic_config in topic_configs:
                validation_error = self._validate_topic_config(topic_config)
                if validation_error:
                    logger.error(f"Invalid topic configuration: {validation_error}")
                    raise ValueError(validation_error)
            
            # Get existing topics
            existing_topics = await self._get_existing_topics()
            
            # Identify missing topics
            missing_topics = [
                tc for tc in topic_configs 
                if tc.name not in existing_topics
            ]
            
            if not missing_topics:
                logger.info("All required topics already exist")
                self.last_topic_verification = datetime.now()
                return False  # No topics were created
            
            logger.info(
                f"Found {len(missing_topics)} missing topics: "
                f"{[tc.name for tc in missing_topics]}"
            )
            
            # Create missing topics
            creation_results = []
            for topic_config in missing_topics:
                result = await self._create_single_topic(topic_config)
                creation_results.append((topic_config.name, result))
            
            # Log results
            successful = [name for name, result in creation_results if result]
            failed = [name for name, result in creation_results if not result]
            
            duration = time.time() - start_time
            
            if successful:
                logger.info(
                    f"Successfully created {len(successful)} topic(s) in {duration:.2f}s: "
                    f"{successful}"
                )
            
            if failed:
                logger.error(
                    f"Failed to create {len(failed)} topic(s): {failed}"
                )
                raise Exception(f"Failed to create topics: {failed}")
            
            self.last_topic_verification = datetime.now()
            logger.info(f"Topic creation completed in {duration:.2f}s")
            return True  # Topics were created
            
        except Exception as e:
            logger.error(f"Error during topic creation: {e}")
            raise

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

    async def get_topic_health(self) -> Dict[str, Any]:
        """Получение информации о состоянии топиков"""
        if not self.admin_client or not self._initialized:
            return {
                "status": "unavailable",
                "reason": "Service not initialized"
            }
        
        try:
            existing_topics = await self._get_existing_topics()
            required_topics = {
                self.topic_requests,
                self.topic_responses,
                self.topic_dlq
            }
            
            missing_topics = required_topics - existing_topics
            
            return {
                "status": "healthy" if not missing_topics else "degraded",
                "required_topics": list(required_topics),
                "existing_topics": list(required_topics & existing_topics),
                "missing_topics": list(missing_topics),
                "last_verification": self.last_topic_verification.isoformat() if self.last_topic_verification else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get topic health: {e}")
            return {
                "status": "error",
                "error": str(e)
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
                    "messages_failed": self.messages_failed,
                    "topics_created": self.topics_created,
                    "topic_creation_errors": self.topic_creation_errors,
                    "consumer_init_attempts": self.consumer_init_attempts,
                    "connection_errors_total": self.connection_errors_total
                },
                "configuration": {
                    "auto_create_topics": self.topic_auto_create,
                    "creation_retries": self.topic_creation_retries,
                    "creation_timeout": self.topic_creation_timeout,
                    "consumer_init_retries": self.consumer_init_retries,
                    "consumer_init_delay": self.consumer_init_delay,
                    "consumer_init_max_delay": self.consumer_init_max_delay,
                    "post_creation_delay": self.post_creation_delay,
                    "coordinator_wait_timeout": self.coordinator_wait_timeout,
                    "ssl_enabled": self.use_ssl,
                    "ssl_verify_certificates": self.ssl_verify_certificates,
                    "startup_health_check": self.startup_health_check
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