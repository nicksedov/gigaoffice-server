# Kafka Service Configuration Guide

## Overview

The GigaOffice Kafka service provides enhanced automatic topic creation with configurable settings, robust error handling, retry mechanisms, and comprehensive health monitoring.

## Features

### Automatic Topic Creation
- **Auto-discovery**: Checks for existing topics before attempting creation
- **Configurable Settings**: All topic parameters can be set via environment variables
- **Retry Logic**: Automatic retries for transient failures
- **Validation**: Pre-creation validation of topic configurations
- **Verification**: Post-creation verification of topic metadata
- **Error Classification**: Smart error handling with different strategies for different error types

### Health Monitoring
- **Service Health**: Monitor overall Kafka service status
- **Topic Health**: Check existence and configuration of required topics
- **Statistics**: Track messages, topic creations, and errors
- **Configuration Visibility**: View current service configuration

## Environment Variables

### Core Kafka Settings

```bash
# Kafka broker connection
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Topic names
KAFKA_TOPIC_REQUESTS=gigaoffice-requests
KAFKA_TOPIC_RESPONSES=gigaoffice-responses
KAFKA_TOPIC_DLQ=gigaoffice-dlq

# Consumer group
KAFKA_CONSUMER_GROUP=gigaoffice-consumers
```

### Topic Auto-Creation Settings

```bash
# Enable/disable automatic topic creation (default: true)
KAFKA_TOPIC_AUTO_CREATE=true

# Timeout for topic creation operations in seconds (default: 30)
KAFKA_TOPIC_CREATION_TIMEOUT=30

# Number of retry attempts for topic creation (default: 3)
KAFKA_TOPIC_CREATION_RETRIES=3

# Delay between retry attempts in seconds (default: 2)
KAFKA_TOPIC_CREATION_RETRY_DELAY=2
```

### Request Topic Configuration

```bash
# Number of partitions for request topic (default: 3)
KAFKA_TOPIC_REQUESTS_PARTITIONS=3

# Replication factor for request topic (default: 1)
KAFKA_TOPIC_REQUESTS_REPLICATION=1
```

**Recommendations:**
- Set partitions equal to expected number of consumer instances for parallel processing
- Use replication factor ≥ 2 in production for durability
- Higher partition count improves throughput but increases resource usage

### Response Topic Configuration

```bash
# Number of partitions for response topic (default: 3)
KAFKA_TOPIC_RESPONSES_PARTITIONS=3

# Replication factor for response topic (default: 1)
KAFKA_TOPIC_RESPONSES_REPLICATION=1
```

**Recommendations:**
- Match partition count with request topic for balanced processing
- Use same replication factor as request topic for consistency

### Dead Letter Queue Configuration

```bash
# Number of partitions for DLQ topic (default: 1)
KAFKA_TOPIC_DLQ_PARTITIONS=1

# Replication factor for DLQ topic (default: 1)
KAFKA_TOPIC_DLQ_REPLICATION=1
```

**Recommendations:**
- Single partition is usually sufficient as DLQ traffic should be minimal
- Use replication factor ≥ 2 in production to ensure failure data is not lost

### SSL/TLS Configuration

```bash
# Enable SSL (default: false)
KAFKA_USE_SSL=true

# SSL certificate files
KAFKA_SSL_CAFILE=/path/to/ca-cert
KAFKA_SSL_CERTFILE=/path/to/client-cert
KAFKA_SSL_KEYFILE=/path/to/client-key
KAFKA_SSL_PASSWORD=optional-key-password
```

### Producer Configuration

```bash
# Acknowledgment level: all, 1, or 0 (default: all)
KAFKA_PRODUCER_ACKS=all

# Retry backoff in milliseconds (default: 100)
KAFKA_PRODUCER_RETRY_BACKOFF_MS=100

# Linger time in milliseconds (default: 1)
KAFKA_PRODUCER_LINGER_MS=1

# Compression type: gzip, snappy, lz4, or none (default: gzip)
KAFKA_PRODUCER_COMPRESSION_TYPE=gzip
```

### Consumer Configuration

```bash
# Auto offset reset: earliest or latest (default: earliest)
KAFKA_CONSUMER_AUTO_OFFSET_RESET=earliest

# Enable auto commit (default: false)
KAFKA_CONSUMER_ENABLE_AUTO_COMMIT=false

# Max records to poll at once (default: 500)
KAFKA_CONSUMER_MAX_POLL_RECORDS=500

# Session timeout in milliseconds (default: 10000)
KAFKA_CONSUMER_SESSION_TIMEOUT_MS=10000

# Heartbeat interval in milliseconds (default: 3000)
KAFKA_CONSUMER_HEARTBEAT_INTERVAL_MS=3000
```

## Error Handling

The service classifies errors into three categories:

### Expected Errors
Normal conditions that don't require attention:
- Topic already exists
- Concurrent topic creation by another instance

**Handling**: Logged at INFO level, normal operation continues

### Retriable Errors
Temporary conditions that may resolve with retry:
- Connection timeout
- Broker unavailable
- Leader not available
- Network issues

**Handling**: Logged at WARNING level, automatic retry with configurable delay

### Fatal Errors
Permanent conditions requiring intervention:
- Invalid configuration
- Insufficient permissions
- Cluster capacity exceeded
- Authorization failures

**Handling**: Logged at ERROR level, service initialization fails

## Topic Creation Workflow

1. **Check Auto-Creation Flag**: Skip if disabled
2. **Validate Configuration**: Check all topic settings
3. **Query Existing Topics**: List topics from Kafka cluster
4. **Identify Missing Topics**: Compare required vs existing
5. **Create Missing Topics**: Sequential creation with retry
6. **Verify Creation**: Confirm topics exist with correct settings
7. **Update Statistics**: Track creation metrics

## Health Checks

### Service Health

Get overall service status:

```python
from app.services.kafka.service import kafka_service

health = kafka_service.get_health_status()
```

**Response:**
```json
{
  "status": "healthy",
  "bootstrap_servers": "localhost:9092",
  "consumer_running": true,
  "statistics": {
    "messages_sent": 150,
    "messages_received": 145,
    "messages_failed": 2,
    "topics_created": 3,
    "topic_creation_errors": 0
  },
  "configuration": {
    "auto_create_topics": true,
    "creation_retries": 3,
    "creation_timeout": 30
  }
}
```

### Topic Health

Get detailed topic status:

```python
health = await kafka_service.get_topic_health()
```

**Response:**
```json
{
  "status": "healthy",
  "required_topics": [
    "gigaoffice-requests",
    "gigaoffice-responses",
    "gigaoffice-dlq"
  ],
  "existing_topics": [
    "gigaoffice-requests",
    "gigaoffice-responses",
    "gigaoffice-dlq"
  ],
  "missing_topics": [],
  "last_verification": "2025-11-25T10:30:00"
}
```

## Configuration Validation

The service validates topic configurations before creation:

| Parameter | Validation Rule | Error Message |
|-----------|----------------|---------------|
| Partition count | Must be > 0 | "Partition count must be greater than 0 for topic {name}" |
| Replication factor | Must be > 0 | "Replication factor must be greater than 0 for topic {name}" |
| Topic name length | 1-249 characters | "Topic name must be between 1 and 249 characters" |
| Topic name chars | No special chars | "Topic name contains invalid characters" |

## Usage Examples

### Development Environment

Minimal configuration for local development:

```bash
# .env.development
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_AUTO_CREATE=true
KAFKA_TOPIC_REQUESTS_PARTITIONS=1
KAFKA_TOPIC_RESPONSES_PARTITIONS=1
KAFKA_TOPIC_DLQ_PARTITIONS=1
```

### Production Environment

Robust configuration for production:

```bash
# .env.production
KAFKA_BOOTSTRAP_SERVERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
KAFKA_TOPIC_AUTO_CREATE=true
KAFKA_TOPIC_CREATION_TIMEOUT=60
KAFKA_TOPIC_CREATION_RETRIES=5
KAFKA_TOPIC_CREATION_RETRY_DELAY=3

# Request topic - high throughput
KAFKA_TOPIC_REQUESTS_PARTITIONS=12
KAFKA_TOPIC_REQUESTS_REPLICATION=3

# Response topic - matches request topic
KAFKA_TOPIC_RESPONSES_PARTITIONS=12
KAFKA_TOPIC_RESPONSES_REPLICATION=3

# DLQ - low throughput, high durability
KAFKA_TOPIC_DLQ_PARTITIONS=3
KAFKA_TOPIC_DLQ_REPLICATION=3

# SSL enabled
KAFKA_USE_SSL=true
KAFKA_SSL_CAFILE=/etc/kafka/certs/ca-cert.pem
KAFKA_SSL_CERTFILE=/etc/kafka/certs/client-cert.pem
KAFKA_SSL_KEYFILE=/etc/kafka/certs/client-key.pem

# Producer settings
KAFKA_PRODUCER_ACKS=all
KAFKA_PRODUCER_COMPRESSION_TYPE=lz4

# Consumer settings
KAFKA_CONSUMER_MAX_POLL_RECORDS=1000
```

### Disable Auto-Creation

For environments where topics are pre-created:

```bash
KAFKA_TOPIC_AUTO_CREATE=false
```

## Monitoring and Observability

### Statistics Tracked

The service tracks the following metrics:

- `messages_sent`: Total messages produced to Kafka
- `messages_received`: Total messages consumed from Kafka
- `messages_failed`: Total failed message operations
- `topics_created`: Number of topics created by this service instance
- `topic_creation_errors`: Number of topic creation failures
- `last_topic_verification`: Timestamp of last topic verification

### Log Levels

- **DEBUG**: Topic listing operations
- **INFO**: Successful operations, topic already exists
- **WARNING**: Retriable errors, verification warnings, partial failures
- **ERROR**: Fatal errors, creation failures, initialization failures

## Troubleshooting

### Topics Not Created

**Symptoms**: Service starts but topics are missing

**Possible Causes:**
1. Auto-creation disabled
2. Insufficient permissions
3. Network connectivity issues
4. Invalid configuration

**Solutions:**
```bash
# Check if auto-creation is enabled
echo $KAFKA_TOPIC_AUTO_CREATE

# Check service logs for errors
# Look for "Topic creation" related messages

# Verify Kafka connection
# Check bootstrap servers are reachable

# Check Kafka user permissions
# Ensure CREATE permission on cluster
```

### Topic Creation Timeout

**Symptoms**: "Timeout creating topic" in logs

**Solutions:**
```bash
# Increase timeout
KAFKA_TOPIC_CREATION_TIMEOUT=60

# Check Kafka cluster health
# Verify all brokers are running

# Check network latency
# Ensure stable connection to Kafka cluster
```

### Permission Errors

**Symptoms**: "Fatal error" with "permission" or "authorization"

**Solutions:**
1. Grant CREATE permission to Kafka user
2. Grant DESCRIBE permission for topic listing
3. Grant DESCRIBE_CONFIGS for metadata access

### Replication Factor Too High

**Symptoms**: Error mentioning replication factor

**Solutions:**
```bash
# Reduce replication factor to match broker count
# Example: 3 brokers = max replication factor of 3
KAFKA_TOPIC_REQUESTS_REPLICATION=2
KAFKA_TOPIC_RESPONSES_REPLICATION=2
KAFKA_TOPIC_DLQ_REPLICATION=2
```

## Best Practices

### Development
- Use partition count of 1 for simplicity
- Enable auto-creation for convenience
- Use minimal replication (1) to save resources

### Staging
- Match production partition count
- Use replication factor of 2
- Enable auto-creation with monitoring
- Test failover scenarios

### Production
- Partition count = expected consumer instances
- Replication factor ≥ 3 for high availability
- Consider disabling auto-creation after initial deployment
- Monitor topic health regularly
- Use SSL/TLS for security
- Set appropriate retention policies

### Capacity Planning
- **Partition count**: Based on throughput requirements and consumer parallelism
- **Replication factor**: Based on durability requirements (typically 2-3)
- **Retention**: Based on processing time and replay requirements
- **Storage**: Consider message size × retention × throughput

## Migration Guide

### From Previous Version

The enhanced Kafka service is backward compatible. No changes required for existing deployments.

**Optional Enhancements:**
1. Add new environment variables for custom configuration
2. Enable topic health monitoring
3. Adjust partition/replication settings based on load

### Example Migration

```bash
# Before (hardcoded values)
# No configuration needed

# After (configurable, but compatible)
KAFKA_TOPIC_REQUESTS_PARTITIONS=3  # Same as before
KAFKA_TOPIC_RESPONSES_PARTITIONS=3  # Same as before
KAFKA_TOPIC_DLQ_PARTITIONS=1  # Same as before
KAFKA_TOPIC_AUTO_CREATE=true  # Enabled by default
```

## Security Considerations

### Permissions Required

The Kafka service account needs:
- **CREATE**: To create topics
- **DESCRIBE**: To list and verify topics
- **DESCRIBE_CONFIGS**: To read topic metadata
- **READ**: To consume messages
- **WRITE**: To produce messages

### SSL/TLS Best Practices

1. Use separate certificates per environment
2. Rotate certificates regularly
3. Store private keys securely (e.g., secrets manager)
4. Use strong encryption (TLS 1.2+)
5. Validate certificate chains

### Network Security

1. Use firewall rules to restrict Kafka access
2. Enable authentication (SASL)
3. Use encrypted connections (SSL/TLS)
4. Monitor unauthorized access attempts

## Performance Tuning

### High Throughput

```bash
KAFKA_TOPIC_REQUESTS_PARTITIONS=24
KAFKA_PRODUCER_LINGER_MS=10
KAFKA_PRODUCER_COMPRESSION_TYPE=lz4
KAFKA_CONSUMER_MAX_POLL_RECORDS=5000
```

### Low Latency

```bash
KAFKA_PRODUCER_LINGER_MS=0
KAFKA_PRODUCER_COMPRESSION_TYPE=none
KAFKA_CONSUMER_MAX_POLL_RECORDS=100
```

### High Reliability

```bash
KAFKA_PRODUCER_ACKS=all
KAFKA_TOPIC_REQUESTS_REPLICATION=3
KAFKA_TOPIC_CREATION_RETRIES=5
```

## Support

For issues or questions:
1. Check service logs for detailed error messages
2. Verify environment variable configuration
3. Test Kafka connectivity independently
4. Review Kafka broker logs
5. Consult Kafka documentation for cluster-specific issues
