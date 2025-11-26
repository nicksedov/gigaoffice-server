"""
Kafka Service Module
Modularized Kafka service with backward-compatible exports
"""

# Export main service and global instance
from .service import KafkaService, kafka_service

# Export models for external use (especially tests)
from .models import ErrorType, TopicConfig, QueueMessage

# Export configuration for advanced use cases
from .config import KafkaConfig

__all__ = [
    # Main service
    'KafkaService',
    'kafka_service',
    
    # Models
    'ErrorType',
    'TopicConfig',
    'QueueMessage',
    
    # Configuration
    'KafkaConfig',
]