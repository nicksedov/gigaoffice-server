"""
Kafka Service Configuration Management
Centralize all configuration loading and validation from environment variables
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class KafkaConfig:
    """Kafka service configuration loaded from environment variables"""
    
    # Connection settings
    bootstrap_servers: str
    topic_requests: str
    topic_responses: str
    topic_dlq: str
    consumer_group: str
    
    # Queue settings
    max_queue_size: int
    max_processing_time: int
    
    # Topic auto-creation configuration
    topic_auto_create: bool
    topic_creation_timeout: int
    topic_creation_retries: int
    topic_creation_retry_delay: int
    post_creation_delay: int
    
    # Consumer initialization retry configuration
    consumer_init_retries: int
    consumer_init_delay: int
    consumer_init_max_delay: int
    coordinator_wait_timeout: int
    
    # Topic configuration
    topic_requests_partitions: int
    topic_requests_replication: int
    topic_responses_partitions: int
    topic_responses_replication: int
    topic_dlq_partitions: int
    topic_dlq_replication: int
    
    # SSL configuration
    use_ssl: bool
    ssl_verify_certificates: bool
    ssl_cafile: Optional[str]
    ssl_certfile: Optional[str]
    ssl_keyfile: Optional[str]
    ssl_password: Optional[str]
    
    # Health check settings
    startup_health_check: bool
    
    # Producer configuration
    producer_acks: str
    producer_retry_backoff_ms: int
    producer_linger_ms: int
    producer_compression_type: str
    
    # Consumer configuration
    consumer_auto_offset_reset: str
    consumer_enable_auto_commit: bool
    consumer_max_poll_records: int
    consumer_session_timeout_ms: int
    consumer_heartbeat_interval_ms: int
    consumer_request_timeout_ms: int
    consumer_connections_max_idle_ms: int
    consumer_metadata_max_age_ms: int
    
    @classmethod
    def from_env(cls) -> 'KafkaConfig':
        """Load configuration from environment variables"""
        
        # Parse post_creation_delay with bounds enforcement
        post_creation_delay = int(os.getenv("KAFKA_POST_CREATION_DELAY", "3"))
        post_creation_delay = max(0, min(post_creation_delay, 10))
        
        return cls(
            # Connection settings
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            topic_requests=os.getenv("KAFKA_TOPIC_REQUESTS", "gigaoffice-requests"),
            topic_responses=os.getenv("KAFKA_TOPIC_RESPONSES", "gigaoffice-responses"),
            topic_dlq=os.getenv("KAFKA_TOPIC_DLQ", "gigaoffice-dlq"),
            consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "gigaoffice-consumers"),
            
            # Queue settings
            max_queue_size=int(os.getenv("KAFKA_MAX_QUEUE_SIZE", "1000")),
            max_processing_time=int(os.getenv("KAFKA_MAX_PROCESSING_TIME", "300")),
            
            # Topic auto-creation configuration
            topic_auto_create=os.getenv("KAFKA_TOPIC_AUTO_CREATE", "true").lower() == "true",
            topic_creation_timeout=int(os.getenv("KAFKA_TOPIC_CREATION_TIMEOUT", "30")),
            topic_creation_retries=int(os.getenv("KAFKA_TOPIC_CREATION_RETRIES", "3")),
            topic_creation_retry_delay=int(os.getenv("KAFKA_TOPIC_CREATION_RETRY_DELAY", "2")),
            post_creation_delay=post_creation_delay,
            
            # Consumer initialization retry configuration
            consumer_init_retries=int(os.getenv("KAFKA_CONSUMER_INIT_RETRIES", "5")),
            consumer_init_delay=int(os.getenv("KAFKA_CONSUMER_INIT_DELAY", "2")),
            consumer_init_max_delay=int(os.getenv("KAFKA_CONSUMER_INIT_MAX_DELAY", "30")),
            coordinator_wait_timeout=int(os.getenv("KAFKA_COORDINATOR_WAIT_TIMEOUT", "60")),
            
            # Topic configuration
            topic_requests_partitions=int(os.getenv("KAFKA_TOPIC_REQUESTS_PARTITIONS", "3")),
            topic_requests_replication=int(os.getenv("KAFKA_TOPIC_REQUESTS_REPLICATION", "1")),
            topic_responses_partitions=int(os.getenv("KAFKA_TOPIC_RESPONSES_PARTITIONS", "3")),
            topic_responses_replication=int(os.getenv("KAFKA_TOPIC_RESPONSES_REPLICATION", "1")),
            topic_dlq_partitions=int(os.getenv("KAFKA_TOPIC_DLQ_PARTITIONS", "1")),
            topic_dlq_replication=int(os.getenv("KAFKA_TOPIC_DLQ_REPLICATION", "1")),
            
            # SSL configuration
            use_ssl=os.getenv("KAFKA_USE_SSL", "false").lower() == "true",
            ssl_verify_certificates=os.getenv("KAFKA_SSL_VERIFY_CERTIFICATES", "true").lower() == "true",
            ssl_cafile=os.getenv("KAFKA_SSL_CAFILE"),
            ssl_certfile=os.getenv("KAFKA_SSL_CERTFILE"),
            ssl_keyfile=os.getenv("KAFKA_SSL_KEYFILE"),
            ssl_password=os.getenv("KAFKA_SSL_PASSWORD"),
            
            # Health check settings
            startup_health_check=os.getenv("KAFKA_STARTUP_HEALTH_CHECK", "true").lower() == "true",
            
            # Producer configuration
            producer_acks=os.getenv("KAFKA_PRODUCER_ACKS", "all"),
            producer_retry_backoff_ms=int(os.getenv("KAFKA_PRODUCER_RETRY_BACKOFF_MS", "100")),
            producer_linger_ms=int(os.getenv("KAFKA_PRODUCER_LINGER_MS", "1")),
            producer_compression_type=os.getenv("KAFKA_PRODUCER_COMPRESSION_TYPE", "gzip"),
            
            # Consumer configuration
            consumer_auto_offset_reset=os.getenv("KAFKA_CONSUMER_AUTO_OFFSET_RESET", "earliest"),
            consumer_enable_auto_commit=os.getenv("KAFKA_CONSUMER_ENABLE_AUTO_COMMIT", "false").lower() == "true",
            consumer_max_poll_records=int(os.getenv("KAFKA_CONSUMER_MAX_POLL_RECORDS", "500")),
            consumer_session_timeout_ms=int(os.getenv("KAFKA_CONSUMER_SESSION_TIMEOUT_MS", "30000")),
            consumer_heartbeat_interval_ms=int(os.getenv("KAFKA_CONSUMER_HEARTBEAT_INTERVAL_MS", "10000")),
            consumer_request_timeout_ms=int(os.getenv("KAFKA_CONSUMER_REQUEST_TIMEOUT_MS", "40000")),
            consumer_connections_max_idle_ms=int(os.getenv("KAFKA_CONSUMER_CONNECTIONS_MAX_IDLE_MS", "600000")),
            consumer_metadata_max_age_ms=int(os.getenv("KAFKA_CONSUMER_METADATA_MAX_AGE_MS", "60000"))
        )
