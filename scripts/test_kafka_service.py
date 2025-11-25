"""
Kafka Service Test Script

This script demonstrates the enhanced Kafka service features including:
- Automatic topic creation with validation
- Configuration via environment variables
- Error handling and retry logic
- Health check integration
"""

import asyncio
import os
from app.services.kafka.service import kafka_service


async def test_kafka_service():
    """Test Kafka service initialization and topic creation"""
    
    print("=" * 60)
    print("Kafka Service Enhanced Features Test")
    print("=" * 60)
    
    # Display current configuration
    print("\n1. Current Configuration:")
    print("-" * 60)
    print(f"Bootstrap Servers: {kafka_service.bootstrap_servers}")
    print(f"Auto-create Topics: {kafka_service.topic_auto_create}")
    print(f"Creation Timeout: {kafka_service.topic_creation_timeout}s")
    print(f"Creation Retries: {kafka_service.topic_creation_retries}")
    print(f"Retry Delay: {kafka_service.topic_creation_retry_delay}s")
    
    print("\n2. Topic Configuration:")
    print("-" * 60)
    print(f"Request Topic:")
    print(f"  Name: {kafka_service.topic_requests}")
    print(f"  Partitions: {kafka_service.topic_requests_partitions}")
    print(f"  Replication: {kafka_service.topic_requests_replication}")
    
    print(f"\nResponse Topic:")
    print(f"  Name: {kafka_service.topic_responses}")
    print(f"  Partitions: {kafka_service.topic_responses_partitions}")
    print(f"  Replication: {kafka_service.topic_responses_replication}")
    
    print(f"\nDLQ Topic:")
    print(f"  Name: {kafka_service.topic_dlq}")
    print(f"  Partitions: {kafka_service.topic_dlq_partitions}")
    print(f"  Replication: {kafka_service.topic_dlq_replication}")
    
    # Initialize the service
    print("\n3. Initializing Kafka Service:")
    print("-" * 60)
    try:
        await kafka_service.start()
        print("✓ Kafka service initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Kafka service: {e}")
        return
    
    # Check service health
    print("\n4. Service Health Status:")
    print("-" * 60)
    health = kafka_service.get_health_status()
    print(f"Status: {health['status']}")
    print(f"Consumer Running: {health['consumer_running']}")
    print(f"\nStatistics:")
    for key, value in health['statistics'].items():
        print(f"  {key}: {value}")
    print(f"\nConfiguration:")
    for key, value in health['configuration'].items():
        print(f"  {key}: {value}")
    
    # Check topic health
    print("\n5. Topic Health Status:")
    print("-" * 60)
    topic_health = await kafka_service.get_topic_health()
    print(f"Status: {topic_health['status']}")
    print(f"\nRequired Topics: {', '.join(topic_health['required_topics'])}")
    print(f"Existing Topics: {', '.join(topic_health['existing_topics'])}")
    
    if topic_health['missing_topics']:
        print(f"Missing Topics: {', '.join(topic_health['missing_topics'])}")
    else:
        print("Missing Topics: None")
    
    if topic_health.get('last_verification'):
        print(f"Last Verification: {topic_health['last_verification']}")
    
    # Display final statistics
    print("\n6. Final Statistics:")
    print("-" * 60)
    print(f"Topics Created: {kafka_service.topics_created}")
    print(f"Topic Creation Errors: {kafka_service.topic_creation_errors}")
    print(f"Messages Sent: {kafka_service.messages_sent}")
    print(f"Messages Received: {kafka_service.messages_received}")
    print(f"Messages Failed: {kafka_service.messages_failed}")
    
    # Cleanup
    print("\n7. Cleaning Up:")
    print("-" * 60)
    await kafka_service.cleanup()
    print("✓ Cleanup completed")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


async def test_configuration_validation():
    """Test topic configuration validation"""
    
    print("\n" + "=" * 60)
    print("Configuration Validation Test")
    print("=" * 60)
    
    from app.services.kafka.service import TopicConfig
    
    # Test valid configuration
    print("\n1. Valid Configuration:")
    valid_config = TopicConfig(
        name="test-topic",
        num_partitions=3,
        replication_factor=2
    )
    error = kafka_service._validate_topic_config(valid_config)
    if error:
        print(f"✗ Validation failed: {error}")
    else:
        print("✓ Valid configuration passed")
    
    # Test invalid partition count
    print("\n2. Invalid Partition Count (0):")
    invalid_partitions = TopicConfig(
        name="test-topic",
        num_partitions=0,
        replication_factor=1
    )
    error = kafka_service._validate_topic_config(invalid_partitions)
    if error:
        print(f"✓ Caught error: {error}")
    else:
        print("✗ Should have failed validation")
    
    # Test invalid replication factor
    print("\n3. Invalid Replication Factor (0):")
    invalid_replication = TopicConfig(
        name="test-topic",
        num_partitions=3,
        replication_factor=0
    )
    error = kafka_service._validate_topic_config(invalid_replication)
    if error:
        print(f"✓ Caught error: {error}")
    else:
        print("✗ Should have failed validation")
    
    # Test invalid topic name
    print("\n4. Invalid Topic Name (contains invalid chars):")
    invalid_name = TopicConfig(
        name="test/topic:invalid",
        num_partitions=3,
        replication_factor=1
    )
    error = kafka_service._validate_topic_config(invalid_name)
    if error:
        print(f"✓ Caught error: {error}")
    else:
        print("✗ Should have failed validation")
    
    print("\n" + "=" * 60)


async def test_error_classification():
    """Test error classification logic"""
    
    print("\n" + "=" * 60)
    print("Error Classification Test")
    print("=" * 60)
    
    from app.services.kafka.service import ErrorType
    
    # Test expected errors
    print("\n1. Expected Errors:")
    expected_errors = [
        Exception("Topic already exists"),
        Exception("topic 'test' already exists"),
    ]
    for error in expected_errors:
        error_type = kafka_service._classify_error(error)
        print(f"  '{error}' -> {error_type.value}")
        assert error_type == ErrorType.EXPECTED
    
    # Test retriable errors
    print("\n2. Retriable Errors:")
    retriable_errors = [
        Exception("Connection timeout"),
        Exception("Broker unavailable"),
        Exception("Leader not available"),
        Exception("Network error"),
    ]
    for error in retriable_errors:
        error_type = kafka_service._classify_error(error)
        print(f"  '{error}' -> {error_type.value}")
        assert error_type == ErrorType.RETRIABLE
    
    # Test fatal errors
    print("\n3. Fatal Errors:")
    fatal_errors = [
        Exception("Permission denied"),
        Exception("Authorization failed"),
        Exception("Invalid configuration"),
        Exception("Quota exceeded"),
    ]
    for error in fatal_errors:
        error_type = kafka_service._classify_error(error)
        print(f"  '{error}' -> {error_type.value}")
        assert error_type == ErrorType.FATAL
    
    print("\n✓ All error classifications correct")
    print("=" * 60)


def display_environment_variables():
    """Display relevant environment variables"""
    
    print("\n" + "=" * 60)
    print("Environment Variables")
    print("=" * 60)
    
    env_vars = [
        # Core settings
        "KAFKA_BOOTSTRAP_SERVERS",
        "KAFKA_TOPIC_REQUESTS",
        "KAFKA_TOPIC_RESPONSES",
        "KAFKA_TOPIC_DLQ",
        # Auto-creation settings
        "KAFKA_TOPIC_AUTO_CREATE",
        "KAFKA_TOPIC_CREATION_TIMEOUT",
        "KAFKA_TOPIC_CREATION_RETRIES",
        "KAFKA_TOPIC_CREATION_RETRY_DELAY",
        # Topic configuration
        "KAFKA_TOPIC_REQUESTS_PARTITIONS",
        "KAFKA_TOPIC_REQUESTS_REPLICATION",
        "KAFKA_TOPIC_RESPONSES_PARTITIONS",
        "KAFKA_TOPIC_RESPONSES_REPLICATION",
        "KAFKA_TOPIC_DLQ_PARTITIONS",
        "KAFKA_TOPIC_DLQ_REPLICATION",
        # SSL settings
        "KAFKA_USE_SSL",
    ]
    
    print("\nConfigured Variables:")
    for var in env_vars:
        value = os.getenv(var, "(not set)")
        print(f"  {var} = {value}")
    
    print("=" * 60)


async def main():
    """Main test function"""
    
    # Display environment configuration
    display_environment_variables()
    
    # Test configuration validation
    await test_configuration_validation()
    
    # Test error classification
    await test_error_classification()
    
    # Test main Kafka service
    await test_kafka_service()


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())
