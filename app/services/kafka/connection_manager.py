"""
Connection Management for Kafka Service
Manages Kafka client lifecycle and connections with retry logic
"""

import asyncio
import ssl
from typing import Optional
from loguru import logger
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.errors import KafkaError, GroupCoordinatorNotAvailableError

from .config import KafkaConfig
from .health_monitor import HealthMonitor


class ConnectionManager:
    """Manages Kafka client connections and lifecycle"""
    
    def __init__(self, config: KafkaConfig, health_monitor: HealthMonitor):
        """
        Initialize connection manager
        
        Args:
            config: Kafka configuration
            health_monitor: Health monitor for metrics tracking
        """
        self.config = config
        self.health_monitor = health_monitor
        
        # Kafka clients
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.admin_client: Optional[AIOKafkaAdminClient] = None
    
    async def initialize_admin_client(self, ssl_context: Optional[ssl.SSLContext]) -> None:
        """
        Initialize Kafka admin client
        
        Args:
            ssl_context: SSL context for secure connections (if SSL enabled)
            
        Raises:
            Exception: If admin client initialization fails
        """
        # Admin configuration with explicit integer parameters
        admin_config = {
            'bootstrap_servers': self.config.bootstrap_servers,
            'client_id': 'gigaoffice-admin',
            'request_timeout_ms': 30000,
            'connections_max_idle_ms': 540000,
            'retry_backoff_ms': 100,
            'metadata_max_age_ms': 300000
        }
        
        # Add SSL configuration if enabled
        if self.config.use_ssl and ssl_context:
            admin_config['security_protocol'] = 'SSL'
            admin_config['ssl_context'] = ssl_context
        
        logger.info("Initializing Kafka admin client")
        self.admin_client = AIOKafkaAdminClient(**admin_config)
        await self.admin_client.start()
        logger.info("Admin client started successfully")
    
    async def initialize_producer(self, ssl_context: Optional[ssl.SSLContext]) -> None:
        """
        Initialize Kafka producer
        
        Args:
            ssl_context: SSL context for secure connections (if SSL enabled)
            
        Raises:
            Exception: If producer initialization fails
        """
        # Producer configuration from environment variables
        producer_config = {
            'bootstrap_servers': self.config.bootstrap_servers,
            'client_id': 'gigaoffice-producer',
            'acks': self.config.producer_acks,
            'retry_backoff_ms': self.config.producer_retry_backoff_ms,
            'linger_ms': self.config.producer_linger_ms,
            'compression_type': self.config.producer_compression_type
        }
        
        # Add SSL configuration if enabled
        if self.config.use_ssl and ssl_context:
            producer_config['security_protocol'] = 'SSL'
            producer_config['ssl_context'] = ssl_context
        
        logger.info("Initializing Kafka producer")
        self.producer = AIOKafkaProducer(**producer_config)
        await self.producer.start()
        logger.info("Producer started successfully")
    
    async def start_consumer_with_retry(self) -> None:
        """
        Start consumer with retry logic and exponential backoff
        
        Raises:
            Exception: If consumer fails to start after all retries
        """
        if not self.consumer:
            raise ValueError("Consumer not initialized")
        
        retry_count = 0
        current_delay = self.config.consumer_init_delay
        
        while retry_count <= self.config.consumer_init_retries:
            try:
                self.health_monitor.consumer_init_attempts += 1
                
                if retry_count > 0:
                    logger.info(
                        f"Attempting to start consumer (attempt {retry_count + 1}/{self.config.consumer_init_retries + 1})"
                    )
                
                # Try to start consumer
                await asyncio.wait_for(
                    self.consumer.start(),
                    timeout=self.config.coordinator_wait_timeout
                )
                
                logger.info("✓ Consumer connected successfully")
                return
                
            except GroupCoordinatorNotAvailableError as e:
                self.health_monitor.connection_errors_total += 1
                logger.warning(
                    f"Group coordinator not available (attempt {retry_count + 1}/{self.config.consumer_init_retries + 1}): {e}"
                )
                
                if retry_count < self.config.consumer_init_retries:
                    logger.info(f"Waiting {current_delay}s before retry...")
                    await asyncio.sleep(current_delay)
                    # Exponential backoff with max delay cap
                    current_delay = min(current_delay * 2, self.config.consumer_init_max_delay)
                    retry_count += 1
                else:
                    error_msg = (
                        f"Failed to start consumer after {self.config.consumer_init_retries + 1} attempts. "
                        f"Group coordinator not available. "
                        f"Please verify: \n"
                        f"  1. Kafka broker is running at {self.config.bootstrap_servers}\n"
                        f"  2. SSL certificates are valid and trusted\n"
                        f"  3. Network connectivity to Kafka cluster\n"
                        f"  4. Consumer group '{self.config.consumer_group}' is not locked"
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
            
            except asyncio.TimeoutError:
                self.health_monitor.connection_errors_total += 1
                logger.error(
                    f"Timeout starting consumer (attempt {retry_count + 1}/{self.config.consumer_init_retries + 1})"
                )
                
                if retry_count < self.config.consumer_init_retries:
                    logger.info(f"Waiting {current_delay}s before retry...")
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, self.config.consumer_init_max_delay)
                    retry_count += 1
                else:
                    error_msg = (
                        f"Timeout starting consumer after {self.config.coordinator_wait_timeout}s. "
                        f"Check network connectivity and broker availability."
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg)
            
            except KafkaError as e:
                self.health_monitor.connection_errors_total += 1
                error_str = str(e).lower()
                
                # Classify error type
                is_ssl_error = any(keyword in error_str for keyword in ['ssl', 'certificate', 'handshake'])
                is_network_error = any(keyword in error_str for keyword in ['connection', 'timeout', 'network'])
                
                if is_ssl_error:
                    error_msg = (
                        f"SSL connection error: {e}\n"
                        f"Please verify:\n"
                        f"  1. CA certificate is valid: {self.config.ssl_cafile}\n"
                        f"  2. Client certificate is valid: {self.config.ssl_certfile}\n"
                        f"  3. Private key is valid: {self.config.ssl_keyfile}\n"
                        f"  4. Certificate hostname matches broker address\n"
                        f"  5. Certificates are not expired"
                    )
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
                
                if is_network_error and retry_count < self.config.consumer_init_retries:
                    logger.warning(
                        f"Network error starting consumer (attempt {retry_count + 1}/{self.config.consumer_init_retries + 1}): {e}"
                    )
                    logger.info(f"Waiting {current_delay}s before retry...")
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, self.config.consumer_init_max_delay)
                    retry_count += 1
                else:
                    error_msg = f"Failed to start consumer: {e}"
                    logger.error(error_msg)
                    raise Exception(error_msg) from e
            
            except Exception as e:
                self.health_monitor.connection_errors_total += 1
                logger.error(f"Unexpected error starting consumer: {e}")
                raise
    
    async def initialize_consumer(self, ssl_context: Optional[ssl.SSLContext]) -> None:
        """
        Initialize Kafka consumer with retry logic
        
        Args:
            ssl_context: SSL context for secure connections (if SSL enabled)
            
        Raises:
            Exception: If consumer initialization fails
        """
        # Consumer configuration from environment variables with optimized timeouts for SSL
        consumer_config = {
            'bootstrap_servers': self.config.bootstrap_servers,
            'group_id': self.config.consumer_group,
            'client_id': 'gigaoffice-consumer',
            'auto_offset_reset': self.config.consumer_auto_offset_reset,
            'enable_auto_commit': self.config.consumer_enable_auto_commit,
            'max_poll_records': self.config.consumer_max_poll_records,
            'session_timeout_ms': self.config.consumer_session_timeout_ms,
            'heartbeat_interval_ms': self.config.consumer_heartbeat_interval_ms,
            'request_timeout_ms': self.config.consumer_request_timeout_ms,
            'connections_max_idle_ms': self.config.consumer_connections_max_idle_ms,
            'metadata_max_age_ms': self.config.consumer_metadata_max_age_ms
        }
        
        # Add SSL configuration if enabled
        if self.config.use_ssl and ssl_context:
            consumer_config['security_protocol'] = 'SSL'
            consumer_config['ssl_context'] = ssl_context
        
        logger.info("Initializing Kafka consumer")
        self.consumer = AIOKafkaConsumer(
            self.config.topic_requests,
            **consumer_config
        )
        await self.start_consumer_with_retry()
        logger.info("Consumer started successfully")
    
    async def cleanup(self) -> None:
        """
        Cleanup and close all Kafka connections
        
        Logs errors but doesn't raise exceptions to ensure all cleanup attempts are made
        """
        try:
            if self.producer:
                await self.producer.stop()
                logger.info("Producer stopped")
                
            if self.consumer:
                await self.consumer.stop()
                logger.info("Consumer stopped")
                
            if self.admin_client:
                await self.admin_client.close()
                logger.info("Admin client closed")
                
            logger.info("Kafka connections cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
