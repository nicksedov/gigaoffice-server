"""
Topic Management for Kafka Service
Handles topic creation, validation, and management operations
"""

import time
import asyncio
from typing import Optional, Set
from datetime import datetime
from loguru import logger
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

from .config import KafkaConfig
from .models import TopicConfig, ErrorType
from .health_monitor import HealthMonitor


class TopicManager:
    """Manages Kafka topic operations including creation, validation, and verification"""
    
    def __init__(self, config: KafkaConfig, health_monitor: HealthMonitor):
        """
        Initialize topic manager
        
        Args:
            config: Kafka configuration
            health_monitor: Health monitor for metrics tracking
        """
        self.config = config
        self.health_monitor = health_monitor
    
    def validate_topic_config(self, topic_config: TopicConfig) -> Optional[str]:
        """
        Validate topic configuration
        
        Args:
            topic_config: Topic configuration to validate
            
        Returns:
            Error message if validation fails, None otherwise
        """
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
    
    async def verify_topic_created(
        self, 
        admin_client: AIOKafkaAdminClient,
        topic_config: TopicConfig
    ) -> bool:
        """
        Verify that topic was created with correct configuration
        
        Args:
            admin_client: Admin client for verification
            topic_config: Topic configuration to verify
            
        Returns:
            True if topic exists and is configured correctly, False otherwise
        """
        if not admin_client:
            return False
        
        try:
            # First, try to get detailed cluster metadata
            try:
                # Get cluster metadata using the admin client's internal client
                cluster_metadata = await admin_client._client.fetch_all_metadata()
                
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
                existing_topics = await admin_client.list_topics()
                
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
    
    def classify_error(self, error: Exception) -> ErrorType:
        """
        Classify error for determining handling strategy
        
        Args:
            error: Exception to classify
            
        Returns:
            ErrorType classification
        """
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
    
    async def create_single_topic(
        self,
        admin_client: AIOKafkaAdminClient,
        topic_config: TopicConfig,
        retry_attempt: int = 0
    ) -> bool:
        """
        Create a single topic with retry logic
        
        Args:
            admin_client: Admin client for topic creation
            topic_config: Topic configuration
            retry_attempt: Current retry attempt number
            
        Returns:
            True if topic was created successfully, False otherwise
        """
        if not admin_client:
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
                admin_client.create_topics([new_topic]),
                timeout=self.config.topic_creation_timeout
            )
            
            self.health_monitor.topics_created += 1
            logger.info(f"Topic {topic_config.name} created successfully")
            
            # Verify topic was created
            if await self.verify_topic_created(admin_client, topic_config):
                return True
            else:
                logger.warning(f"Topic {topic_config.name} creation could not be verified")
                return True  # Still consider it created
            
        except asyncio.TimeoutError:
            logger.error(
                f"Timeout creating topic {topic_config.name} "
                f"(attempt {retry_attempt + 1}/{self.config.topic_creation_retries + 1})"
            )
            error_type = ErrorType.RETRIABLE
            
        except Exception as e:
            error_type = self.classify_error(e)
            
            if error_type == ErrorType.EXPECTED:
                logger.info(
                    f"Topic {topic_config.name} already exists, skipping creation"
                )
                return True
            
            elif error_type == ErrorType.RETRIABLE:
                logger.warning(
                    f"Retriable error creating topic {topic_config.name} "
                    f"(attempt {retry_attempt + 1}/{self.config.topic_creation_retries + 1}): {e}"
                )
            
            else:  # FATAL
                logger.error(
                    f"Fatal error creating topic {topic_config.name}: {e}"
                )
                self.health_monitor.topic_creation_errors += 1
                raise
        
        # Retry logic for retriable errors
        if retry_attempt < self.config.topic_creation_retries:
            await asyncio.sleep(self.config.topic_creation_retry_delay)
            return await self.create_single_topic(admin_client, topic_config, retry_attempt + 1)
        else:
            logger.error(
                f"Failed to create topic {topic_config.name} "
                f"after {self.config.topic_creation_retries + 1} attempts"
            )
            self.health_monitor.topic_creation_errors += 1
            return False
    
    async def validate_replication_settings(self) -> None:
        """
        Validate replication settings against broker count
        
        Raises:
            Exception: If replication configuration is incompatible with broker count
        """
        # Skip validation if broker count is unknown
        if self.health_monitor.broker_count is None or self.health_monitor.broker_count == 0:
            logger.warning("Broker count unknown, skipping replication validation")
            return
        
        # Define topic replication configurations to validate
        replication_configs = [
            ("requests", self.config.topic_requests, self.config.topic_requests_replication),
            ("responses", self.config.topic_responses, self.config.topic_responses_replication),
            ("dlq", self.config.topic_dlq, self.config.topic_dlq_replication)
        ]
        
        validation_issues = []
        
        for topic_type, topic_name, replication_factor in replication_configs:
            if replication_factor > self.health_monitor.broker_count:
                issue = (
                    f"Topic '{topic_name}' has replication factor {replication_factor} "
                    f"but only {self.health_monitor.broker_count} broker(s) available"
                )
                validation_issues.append(issue)
        
        if validation_issues:
            error_msg = (
                f"Invalid replication configuration detected:\n"
                f"  - Available brokers: {self.health_monitor.broker_count}\n"
            )
            for issue in validation_issues:
                error_msg += f"  - {issue}\n"
            
            error_msg += (
                f"\nRemediation:\n"
                f"  For single-broker development:\n"
                f"    - Set KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 on broker\n"
                f"    - Set KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1 on broker\n"
                f"    - Set KAFKA_DEFAULT_REPLICATION_FACTOR=1 on broker\n"
                f"    - Set KAFKA_MIN_INSYNC_REPLICAS=1 on broker\n"
                f"    - Delete Kafka data directory and restart broker\n"
                f"  \n"
                f"  For production environments:\n"
                f"    - Deploy at least {max(self.config.topic_requests_replication, self.config.topic_responses_replication, self.config.topic_dlq_replication)} Kafka brokers\n"
                f"    - Configure broker-level replication settings appropriately\n"
                f"\n"
                f"  See KAFKA_ENV_VARS.md for detailed configuration instructions."
            )
            
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Add warning for single-broker setup
        if self.health_monitor.broker_count == 1:
            warning = (
                "Single-broker Kafka cluster detected. This is suitable for development only. "
                "Production environments should use at least 3 brokers with replication factor 3."
            )
            logger.warning(warning)
            self.health_monitor.configuration_warnings.append(warning)
        
        logger.info(
            f"✓ Replication settings validated: {self.health_monitor.broker_count} broker(s), "
            f"max replication factor {max(self.config.topic_requests_replication, self.config.topic_responses_replication, self.config.topic_dlq_replication)}"
        )
    
    async def create_topics(self, admin_client: AIOKafkaAdminClient) -> bool:
        """
        Create required topics if they don't exist
        
        Args:
            admin_client: Admin client for topic operations
            
        Returns:
            True if any topics were created, False if all topics already existed
            
        Raises:
            Exception: If topic creation fails
        """
        # Check if auto-creation is enabled
        if not self.config.topic_auto_create:
            logger.info("Topic auto-creation is disabled, skipping")
            return False
        
        # Check if admin client is initialized
        if not admin_client:
            logger.warning("Admin client not initialized, skipping topic creation")
            return False
        
        start_time = time.time()
        
        try:
            # Define topic configurations
            topic_configs = [
                TopicConfig(
                    name=self.config.topic_requests,
                    num_partitions=self.config.topic_requests_partitions,
                    replication_factor=self.config.topic_requests_replication
                ),
                TopicConfig(
                    name=self.config.topic_responses,
                    num_partitions=self.config.topic_responses_partitions,
                    replication_factor=self.config.topic_responses_replication
                ),
                TopicConfig(
                    name=self.config.topic_dlq,
                    num_partitions=self.config.topic_dlq_partitions,
                    replication_factor=self.config.topic_dlq_replication
                )
            ]
            
            # Validate all topic configurations
            for topic_config in topic_configs:
                validation_error = self.validate_topic_config(topic_config)
                if validation_error:
                    logger.error(f"Invalid topic configuration: {validation_error}")
                    raise ValueError(validation_error)
            
            # Get existing topics
            existing_topics = await self.health_monitor.get_existing_topics(admin_client)
            
            # Identify missing topics
            missing_topics = [
                tc for tc in topic_configs 
                if tc.name not in existing_topics
            ]
            
            if not missing_topics:
                logger.info("All required topics already exist")
                self.health_monitor.last_topic_verification = datetime.now()
                return False  # No topics were created
            
            logger.info(
                f"Found {len(missing_topics)} missing topics: "
                f"{[tc.name for tc in missing_topics]}"
            )
            
            # Create missing topics
            creation_results = []
            for topic_config in missing_topics:
                result = await self.create_single_topic(admin_client, topic_config)
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
            
            self.health_monitor.last_topic_verification = datetime.now()
            logger.info(f"Topic creation completed in {duration:.2f}s")
            return True  # Topics were created
            
        except Exception as e:
            logger.error(f"Error during topic creation: {e}")
            raise
