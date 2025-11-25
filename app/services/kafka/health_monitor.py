"""
Health Monitoring and Metrics for Kafka Service
Monitors service health, collects metrics, and provides health status reporting
"""

import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from loguru import logger
from aiokafka.admin import AIOKafkaAdminClient

from .config import KafkaConfig


class HealthMonitor:
    """Monitors Kafka service health and collects operational metrics"""
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize health monitor
        
        Args:
            config: Kafka configuration
        """
        self.config = config
        
        # Metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.messages_failed = 0
        self.processing_times: List[float] = []
        self.topics_created = 0
        self.topic_creation_errors = 0
        self.consumer_init_attempts = 0
        self.connection_errors_total = 0
        
        # State
        self.broker_count: Optional[int] = None
        self.configuration_warnings: List[str] = []
        self.last_topic_verification: Optional[datetime] = None
    
    async def detect_broker_count(self, admin_client: AIOKafkaAdminClient) -> int:
        """
        Detect the number of available brokers in the cluster
        
        Args:
            admin_client: Admin client for cluster metadata access
            
        Returns:
            Number of active brokers
        """
        if not admin_client:
            logger.warning("Admin client not initialized for broker count detection")
            return 0
        
        try:
            # Get cluster metadata
            cluster_metadata = await admin_client._client.fetch_all_metadata()
            
            # Count brokers
            broker_count = len(cluster_metadata.brokers())
            logger.info(f"Detected {broker_count} Kafka broker(s) in cluster")
            
            self.broker_count = broker_count
            return broker_count
            
        except Exception as e:
            logger.warning(f"Failed to detect broker count: {e}")
            return 0
    
    async def verify_broker_health(self, admin_client: AIOKafkaAdminClient) -> None:
        """
        Verify Kafka broker availability and health
        
        Args:
            admin_client: Admin client for health checks
            
        Raises:
            Exception: If broker is unhealthy or unreachable
        """
        if not admin_client:
            logger.warning("Admin client not initialized for health check")
            return
        
        logger.info("Verifying Kafka broker health")
        
        try:
            # Get cluster metadata
            metadata = await asyncio.wait_for(
                admin_client.list_topics(),
                timeout=self.config.coordinator_wait_timeout
            )
            
            topic_count = len(metadata)
            logger.info(f"✓ Kafka cluster is healthy: {topic_count} topics found")
            logger.info(f"  Bootstrap servers: {self.config.bootstrap_servers}")
            
            # Detect broker count
            await self.detect_broker_count(admin_client)
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout connecting to Kafka broker after {self.config.coordinator_wait_timeout}s"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to verify Kafka broker health: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    async def get_existing_topics(self, admin_client: AIOKafkaAdminClient) -> Set[str]:
        """
        Get list of existing topics in the cluster
        
        Args:
            admin_client: Admin client for topic listing
            
        Returns:
            Set of existing topic names
        """
        if not admin_client:
            logger.warning("Admin client not initialized")
            return set()
        
        try:
            metadata = await admin_client.list_topics()
            existing_topics = set(metadata)
            logger.debug(f"Found {len(existing_topics)} existing topics in cluster")
            return existing_topics
        except Exception as e:
            logger.error(f"Failed to list existing topics: {e}")
            return set()
    
    async def get_topic_health(self, admin_client: Optional[AIOKafkaAdminClient], initialized: bool) -> Dict[str, Any]:
        """
        Get health status of topics
        
        Args:
            admin_client: Admin client for topic checks
            initialized: Whether service is initialized
            
        Returns:
            Dictionary containing topic health information
        """
        if not admin_client or not initialized:
            return {
                "status": "unavailable",
                "reason": "Service not initialized"
            }
        
        try:
            existing_topics = await self.get_existing_topics(admin_client)
            required_topics = {
                self.config.topic_requests,
                self.config.topic_responses,
                self.config.topic_dlq
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
    
    def get_health_status(self, initialized: bool, is_running: bool) -> Dict[str, Any]:
        """
        Get comprehensive health status of Kafka service
        
        Args:
            initialized: Whether service is initialized
            is_running: Whether consumer is running
            
        Returns:
            Dictionary containing comprehensive health data
        """
        try:
            health_data = {
                "status": "healthy" if initialized else "initializing",
                "bootstrap_servers": self.config.bootstrap_servers,
                "consumer_running": is_running,
                "broker_count": self.broker_count,
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
                    "auto_create_topics": self.config.topic_auto_create,
                    "creation_retries": self.config.topic_creation_retries,
                    "creation_timeout": self.config.topic_creation_timeout,
                    "consumer_init_retries": self.config.consumer_init_retries,
                    "consumer_init_delay": self.config.consumer_init_delay,
                    "consumer_init_max_delay": self.config.consumer_init_max_delay,
                    "post_creation_delay": self.config.post_creation_delay,
                    "coordinator_wait_timeout": self.config.coordinator_wait_timeout,
                    "ssl_enabled": self.config.use_ssl,
                    "ssl_verify_certificates": self.config.ssl_verify_certificates,
                    "startup_health_check": self.config.startup_health_check,
                    "replication_factors": {
                        "requests_topic": self.config.topic_requests_replication,
                        "responses_topic": self.config.topic_responses_replication,
                        "dlq_topic": self.config.topic_dlq_replication
                    }
                }
            }
            
            # Add configuration warnings if any
            if self.configuration_warnings:
                health_data["configuration_warnings"] = self.configuration_warnings
            
            # Add replication validation status
            if self.broker_count is not None and self.broker_count > 0:
                max_replication = max(
                    self.config.topic_requests_replication,
                    self.config.topic_responses_replication,
                    self.config.topic_dlq_replication
                )
                
                if max_replication > self.broker_count:
                    health_data["replication_validation"] = "error: replication factor exceeds broker count"
                elif self.broker_count == 1:
                    health_data["replication_validation"] = "warning: single-broker detected (development only)"
                else:
                    health_data["replication_validation"] = "ok"
            else:
                health_data["replication_validation"] = "unknown: broker count not detected"
            
            return health_data
            
        except Exception as e:
            logger.error(f"Kafka health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "bootstrap_servers": self.config.bootstrap_servers
            }
    
    def get_queue_info(self, is_running: bool) -> Dict[str, Any]:
        """
        Get information about message queues
        
        Args:
            is_running: Whether consumer is running
            
        Returns:
            Dictionary containing queue information
        """
        try:
            queue_info = {
                "topics": {
                    "requests": self.config.topic_requests,
                    "responses": self.config.topic_responses,
                    "dlq": self.config.topic_dlq
                },
                "statistics": {
                    "messages_sent": self.messages_sent,
                    "messages_received": self.messages_received,
                    "messages_failed": self.messages_failed,
                    "avg_processing_time": sum(self.processing_times[-100:]) / len(self.processing_times[-100:]) if self.processing_times else 0
                },
                "status": "running" if is_running else "stopped"
            }
            
            return queue_info
            
        except Exception as e:
            logger.error(f"Failed to get queue info: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
