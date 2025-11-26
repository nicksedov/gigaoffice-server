"""
GigaOffice Kafka Service - Refactored Modular Architecture
Main service orchestrator that coordinates all Kafka operations
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from loguru import logger

# Import modular components
from .config import KafkaConfig
from .models import ErrorType, TopicConfig, QueueMessage
from .ssl_handler import SSLHandler
from .health_monitor import HealthMonitor
from .topic_manager import TopicManager
from .connection_manager import ConnectionManager
from .message_handler import MessageHandler


class KafkaService:
    """
    Main Kafka Service Orchestrator
    
    Coordinates all Kafka operations through modular components:
    - Configuration management
    - SSL handling
    - Connection lifecycle
    - Topic management
    - Message processing
    - Health monitoring
    """
    
    def __init__(self):
        """Initialize Kafka service with modular components"""
        # Load configuration from environment
        self.config = KafkaConfig.from_env()
        
        # Initialize modular components
        self.health_monitor = HealthMonitor(self.config)
        self.ssl_handler = SSLHandler(self.config)
        self.connection_manager = ConnectionManager(self.config, self.health_monitor)
        self.topic_manager = TopicManager(self.config, self.health_monitor)
        self.message_handler = MessageHandler(self.config, self.health_monitor, self.connection_manager)
        
        # Service state
        self._initialized = False
    
    async def start(self):
        """
        Initialize Kafka service components in staged sequence
        
        Raises:
            Exception: If initialization fails
        """
        if self._initialized:
            return
            
        try:
            # 1. Create SSL context if needed
            ssl_context = self.ssl_handler.create_ssl_context()
            
            # 2. Initialize admin client first for health checks
            await self.connection_manager.initialize_admin_client(ssl_context)
            
            # 3. Verify broker connectivity if health check enabled
            if self.config.startup_health_check:
                await self.health_monitor.verify_broker_health(self.connection_manager.admin_client)
            else:
                # Still detect broker count even if health check is disabled
                await self.health_monitor.detect_broker_count(self.connection_manager.admin_client)
            
            # 4. Validate replication settings against broker count
            await self.topic_manager.validate_replication_settings()
            
            # 5. Create topics if they don't exist
            topics_created = await self.topic_manager.create_topics(self.connection_manager.admin_client)
            
            # 6. Apply stabilization delay if topics were created
            if topics_created and self.config.post_creation_delay > 0:
                logger.info(
                    f"Topics were created, waiting {self.config.post_creation_delay}s for "
                    f"Kafka cluster to stabilize (group coordinator election, metadata propagation)"
                )
                await asyncio.sleep(self.config.post_creation_delay)
                logger.info("Stabilization period completed, continuing with initialization")
            elif topics_created:
                logger.info("Topics were created, but post-creation delay is disabled (0s)")
            
            # 7. Initialize producer
            await self.connection_manager.initialize_producer(ssl_context)
            
            # 8. Initialize consumer with retry logic
            await self.connection_manager.initialize_consumer(ssl_context)
            
            self._initialized = True
            logger.info("Kafka service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka service: {e}")
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
        if not self._initialized:
            await self.start()
        
        return await self.message_handler.send_request(
            request_id=request_id,
            user_id=user_id,
            query=query,
            input_range=input_range,
            category=category,
            input_data=input_data,
            priority=priority
        )
    
    async def start_consumer(self, message_processor: Callable):
        """
        Start consuming messages from request topic
        
        Args:
            message_processor: Callback function to process each message
        """
        if not self._initialized:
            await self.start()
        
        await self.message_handler.start_consumer(message_processor)
    
    def stop_consumer(self):
        """Stop the message consumer"""
        self.message_handler.stop_consumer()
    
    async def cleanup(self):
        """
        Cleanup and close all Kafka connections
        """
        try:
            self.stop_consumer()
            await self.connection_manager.cleanup()
            logger.info("Kafka service cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during Kafka cleanup: {e}")
    
    def get_queue_info(self) -> Dict[str, Any]:
        """
        Get information about message queues
        
        Returns:
            Dictionary containing queue information
        """
        return self.health_monitor.get_queue_info(self.message_handler.is_running)
    
    async def get_topic_health(self) -> Dict[str, Any]:
        """
        Get health status of topics
        
        Returns:
            Dictionary containing topic health information
        """
        return await self.health_monitor.get_topic_health(
            self.connection_manager.admin_client,
            self._initialized
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of Kafka service
        
        Returns:
            Dictionary containing comprehensive health data
        """
        return self.health_monitor.get_health_status(
            self._initialized,
            self.message_handler.is_running
        )


# Create global instance for backward compatibility
kafka_service = KafkaService()
