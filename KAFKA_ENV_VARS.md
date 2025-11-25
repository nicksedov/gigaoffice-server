# Kafka Service Environment Variables - Quick Reference

## Consumer Initialization & Retry Settings

```bash
# Maximum number of retry attempts for consumer initialization
# Default: 5
# Recommended: 5-10 for production
KAFKA_CONSUMER_INIT_RETRIES=5

# Initial delay in seconds before first retry
# Default: 2
# Recommended: 2-5 seconds
KAFKA_CONSUMER_INIT_DELAY=2

# Maximum delay in seconds between retries (exponential backoff cap)
# Default: 30
# Recommended: 30-60 seconds
KAFKA_CONSUMER_INIT_MAX_DELAY=30

# Timeout in seconds to wait for coordinator availability
# Default: 60
# Recommended: 60-120 seconds for SSL connections
KAFKA_COORDINATOR_WAIT_TIMEOUT=60
```

## SSL Certificate Settings

```bash
# Enable SSL certificate validation before connection
# Default: true
# Set to false only for troubleshooting
KAFKA_SSL_VERIFY_CERTIFICATES=true
```

## Health Check Settings

```bash
# Enable pre-startup broker health check
# Default: true
# Set to false to skip health verification
KAFKA_STARTUP_HEALTH_CHECK=true
```

## Consumer Timeout Settings (Optimized for SSL)

```bash
# Consumer session timeout in milliseconds
# Default: 30000 (30 seconds)
# Old default was: 10000 (10 seconds)
KAFKA_CONSUMER_SESSION_TIMEOUT_MS=30000

# Consumer heartbeat interval in milliseconds
# Default: 10000 (10 seconds)
# Old default was: 3000 (3 seconds)
KAFKA_CONSUMER_HEARTBEAT_INTERVAL_MS=10000

# Request timeout in milliseconds
# Default: 40000 (40 seconds)
KAFKA_CONSUMER_REQUEST_TIMEOUT_MS=40000

# Maximum idle time for connections in milliseconds
# Default: 600000 (10 minutes)
KAFKA_CONSUMER_CONNECTIONS_MAX_IDLE_MS=600000

# Metadata refresh interval in milliseconds
# Default: 60000 (1 minute)
KAFKA_CONSUMER_METADATA_MAX_AGE_MS=60000
```

## Example Configurations

### Development (Local Kafka, No SSL)
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_USE_SSL=false
KAFKA_CONSUMER_INIT_RETRIES=3
KAFKA_COORDINATOR_WAIT_TIMEOUT=30
```

### Production (SSL Enabled, High Availability)
```bash
KAFKA_BOOTSTRAP_SERVERS=kafka-broker-1:9093,kafka-broker-2:9093
KAFKA_USE_SSL=true
KAFKA_SSL_CAFILE=/etc/kafka/certs/ca-cert.pem
KAFKA_SSL_CERTFILE=/etc/kafka/certs/client-cert.pem
KAFKA_SSL_KEYFILE=/etc/kafka/certs/client-key.pem

KAFKA_SSL_VERIFY_CERTIFICATES=true
KAFKA_STARTUP_HEALTH_CHECK=true

KAFKA_CONSUMER_INIT_RETRIES=10
KAFKA_CONSUMER_INIT_DELAY=3
KAFKA_CONSUMER_INIT_MAX_DELAY=60
KAFKA_COORDINATOR_WAIT_TIMEOUT=120

KAFKA_CONSUMER_SESSION_TIMEOUT_MS=45000
KAFKA_CONSUMER_REQUEST_TIMEOUT_MS=60000
```

### Troubleshooting (Minimal Retries, Detailed Logging)
```bash
KAFKA_BOOTSTRAP_SERVERS=kafka-broker:9093
KAFKA_USE_SSL=true
KAFKA_SSL_CAFILE=/path/to/ca-cert.pem
KAFKA_SSL_CERTFILE=/path/to/client-cert.pem
KAFKA_SSL_KEYFILE=/path/to/client-key.pem

# Fail fast for debugging
KAFKA_CONSUMER_INIT_RETRIES=1
KAFKA_COORDINATOR_WAIT_TIMEOUT=30

# Keep validation enabled to see SSL errors
KAFKA_SSL_VERIFY_CERTIFICATES=true
KAFKA_STARTUP_HEALTH_CHECK=true
```

### Slow Network / High Latency
```bash
KAFKA_BOOTSTRAP_SERVERS=kafka-broker:9093
KAFKA_USE_SSL=true

# More retries with longer delays
KAFKA_CONSUMER_INIT_RETRIES=15
KAFKA_CONSUMER_INIT_DELAY=5
KAFKA_CONSUMER_INIT_MAX_DELAY=120
KAFKA_COORDINATOR_WAIT_TIMEOUT=180

# Extended timeouts
KAFKA_CONSUMER_SESSION_TIMEOUT_MS=60000
KAFKA_CONSUMER_REQUEST_TIMEOUT_MS=90000
```

## Complete .env Template

```bash
# ============================================================================
# Kafka Core Configuration
# ============================================================================
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_REQUESTS=gigaoffice-requests
KAFKA_TOPIC_RESPONSES=gigaoffice-responses
KAFKA_TOPIC_DLQ=gigaoffice-dlq
KAFKA_CONSUMER_GROUP=gigaoffice-consumers

# ============================================================================
# Consumer Initialization & Retry
# ============================================================================
KAFKA_CONSUMER_INIT_RETRIES=5
KAFKA_CONSUMER_INIT_DELAY=2
KAFKA_CONSUMER_INIT_MAX_DELAY=30
KAFKA_COORDINATOR_WAIT_TIMEOUT=60

# ============================================================================
# SSL Configuration
# ============================================================================
KAFKA_USE_SSL=false
# KAFKA_SSL_CAFILE=/path/to/ca-cert.pem
# KAFKA_SSL_CERTFILE=/path/to/client-cert.pem
# KAFKA_SSL_KEYFILE=/path/to/client-key.pem
# KAFKA_SSL_PASSWORD=
KAFKA_SSL_VERIFY_CERTIFICATES=true

# ============================================================================
# Health Checks
# ============================================================================
KAFKA_STARTUP_HEALTH_CHECK=true

# ============================================================================
# Topic Auto-Creation
# ============================================================================
KAFKA_TOPIC_AUTO_CREATE=true
KAFKA_TOPIC_CREATION_TIMEOUT=30
KAFKA_TOPIC_CREATION_RETRIES=3
KAFKA_TOPIC_CREATION_RETRY_DELAY=2

# ============================================================================
# Topic Configuration
# ============================================================================
KAFKA_TOPIC_REQUESTS_PARTITIONS=3
KAFKA_TOPIC_REQUESTS_REPLICATION=1
KAFKA_TOPIC_RESPONSES_PARTITIONS=3
KAFKA_TOPIC_RESPONSES_REPLICATION=1
KAFKA_TOPIC_DLQ_PARTITIONS=1
KAFKA_TOPIC_DLQ_REPLICATION=1

# ============================================================================
# Consumer Timeout Settings (Optimized for SSL)
# ============================================================================
KAFKA_CONSUMER_SESSION_TIMEOUT_MS=30000
KAFKA_CONSUMER_HEARTBEAT_INTERVAL_MS=10000
KAFKA_CONSUMER_REQUEST_TIMEOUT_MS=40000
KAFKA_CONSUMER_CONNECTIONS_MAX_IDLE_MS=600000
KAFKA_CONSUMER_METADATA_MAX_AGE_MS=60000
KAFKA_CONSUMER_AUTO_OFFSET_RESET=earliest
KAFKA_CONSUMER_ENABLE_AUTO_COMMIT=false
KAFKA_CONSUMER_MAX_POLL_RECORDS=500

# ============================================================================
# Producer Configuration
# ============================================================================
KAFKA_PRODUCER_ACKS=all
KAFKA_PRODUCER_RETRY_BACKOFF_MS=100
KAFKA_PRODUCER_LINGER_MS=1
KAFKA_PRODUCER_COMPRESSION_TYPE=gzip
```

## Quick Troubleshooting Guide

| Issue | Check These Variables | Recommended Action |
|-------|----------------------|-------------------|
| GroupCoordinatorNotAvailableError | `KAFKA_CONSUMER_INIT_RETRIES`<br>`KAFKA_COORDINATOR_WAIT_TIMEOUT` | Increase retries to 10<br>Increase timeout to 120s |
| SSL Connection Fails | `KAFKA_SSL_CAFILE`<br>`KAFKA_SSL_CERTFILE`<br>`KAFKA_SSL_KEYFILE`<br>`KAFKA_SSL_VERIFY_CERTIFICATES` | Verify certificate paths<br>Check file permissions<br>Validate certificates |
| Slow Initialization | `KAFKA_CONSUMER_SESSION_TIMEOUT_MS`<br>`KAFKA_CONSUMER_REQUEST_TIMEOUT_MS` | Increase to 45000ms<br>Increase to 60000ms |
| Fast Failure Needed | `KAFKA_CONSUMER_INIT_RETRIES`<br>`KAFKA_STARTUP_HEALTH_CHECK` | Set to 0 or 1<br>Set to false |
| Network Timeouts | `KAFKA_COORDINATOR_WAIT_TIMEOUT`<br>`KAFKA_CONSUMER_INIT_MAX_DELAY` | Increase to 180s<br>Increase to 60s |

## Monitoring These Settings

Check health status to verify configuration:

```python
from app.services.kafka.service import kafka_service

health = kafka_service.get_health_status()
print(health['configuration'])
```

Output includes:
- `consumer_init_retries`: Current retry setting
- `coordinator_wait_timeout`: Current timeout setting
- `ssl_enabled`: Whether SSL is active
- `ssl_verify_certificates`: Whether validation is enabled
- `startup_health_check`: Whether health checks are enabled
