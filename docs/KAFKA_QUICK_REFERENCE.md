# Kafka Service Quick Reference

## Essential Environment Variables

### Minimal Setup (Development)
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_AUTO_CREATE=true
```

### Production Setup
```bash
# Connection
KAFKA_BOOTSTRAP_SERVERS=kafka-1:9092,kafka-2:9092,kafka-3:9092

# Auto-Creation
KAFKA_TOPIC_AUTO_CREATE=true
KAFKA_TOPIC_CREATION_TIMEOUT=60
KAFKA_TOPIC_CREATION_RETRIES=5

# Request Topic
KAFKA_TOPIC_REQUESTS_PARTITIONS=12
KAFKA_TOPIC_REQUESTS_REPLICATION=3

# Response Topic
KAFKA_TOPIC_RESPONSES_PARTITIONS=12
KAFKA_TOPIC_RESPONSES_REPLICATION=3

# DLQ Topic
KAFKA_TOPIC_DLQ_PARTITIONS=3
KAFKA_TOPIC_DLQ_REPLICATION=3

# Security
KAFKA_USE_SSL=true
KAFKA_SSL_CAFILE=/path/to/ca-cert.pem
KAFKA_SSL_CERTFILE=/path/to/client-cert.pem
KAFKA_SSL_KEYFILE=/path/to/client-key.pem
```

## Key Features

✅ **Automatic Topic Creation** - Topics created on first service startup
✅ **Smart Error Handling** - Classifies and handles errors appropriately
✅ **Retry Logic** - Automatic retries for transient failures
✅ **Configuration Validation** - Validates settings before creation
✅ **Post-Creation Verification** - Confirms topics created correctly
✅ **Health Monitoring** - Service and topic health endpoints

## Configuration Defaults

| Setting | Default | Description |
|---------|---------|-------------|
| Auto-create | `true` | Enable automatic topic creation |
| Timeout | `30s` | Topic creation timeout |
| Retries | `3` | Number of retry attempts |
| Retry Delay | `2s` | Delay between retries |
| Request Partitions | `3` | Request topic partitions |
| Response Partitions | `3` | Response topic partitions |
| DLQ Partitions | `1` | DLQ topic partitions |
| Replication Factor | `1` | All topics replication |

## Health Check Endpoints

### Service Health
```python
from app.services.kafka.service import kafka_service
health = kafka_service.get_health_status()
```

Returns: `status`, `statistics`, `configuration`

### Topic Health
```python
topic_health = await kafka_service.get_topic_health()
```

Returns: `status`, `required_topics`, `existing_topics`, `missing_topics`

## Common Commands

### Test Kafka Service
```bash
python scripts/test_kafka_service.py
```

### View Current Configuration
Check environment variables or service logs on startup

## Troubleshooting

### Topics Not Created
- Check `KAFKA_TOPIC_AUTO_CREATE=true`
- Verify Kafka connection
- Check service logs for errors
- Verify permissions (CREATE, DESCRIBE)

### Timeout Errors
- Increase `KAFKA_TOPIC_CREATION_TIMEOUT`
- Check network connectivity
- Verify Kafka cluster health

### Permission Denied
- Grant CREATE permission
- Grant DESCRIBE permission
- Grant DESCRIBE_CONFIGS permission

## Error Types

| Type | Handling | Examples |
|------|----------|----------|
| **Expected** | Log INFO, continue | "already exists" |
| **Retriable** | Retry with delay | timeout, connection errors |
| **Fatal** | Log ERROR, fail | permission denied, invalid config |

## Best Practices

### Development
- Partition count: `1`
- Replication: `1`
- Auto-create: `true`

### Production
- Partition count: Match consumer instances
- Replication: `3` (high availability)
- Auto-create: `true` initially, consider `false` after stable
- Enable SSL/TLS

## Quick Validation

```bash
# Check configuration
echo $KAFKA_TOPIC_AUTO_CREATE
echo $KAFKA_TOPIC_REQUESTS_PARTITIONS

# Test connection
# Use kafka-console tools or python test script
```

## Documentation Links

- Full Guide: `docs/KAFKA_CONFIGURATION.md`
- Implementation Summary: `docs/KAFKA_IMPLEMENTATION_SUMMARY.md`
- Example Config: `.env.kafka.example`
- Test Script: `scripts/test_kafka_service.py`

## Support Checklist

Before asking for help:
1. ✅ Check environment variables are set
2. ✅ Verify Kafka connectivity
3. ✅ Review service logs
4. ✅ Test with `scripts/test_kafka_service.py`
5. ✅ Check topic health endpoint
6. ✅ Verify Kafka user permissions

## Performance Tips

| Goal | Configuration |
|------|---------------|
| **High Throughput** | More partitions, lz4 compression |
| **Low Latency** | Fewer partitions, no compression |
| **High Reliability** | Replication ≥ 3, acks=all |
| **Fast Startup** | Fewer retries, lower timeout |

## Security Checklist

- [ ] SSL/TLS enabled in production
- [ ] Certificates properly configured
- [ ] Private keys secured
- [ ] Permissions granted (CREATE, DESCRIBE)
- [ ] Network access restricted
- [ ] Authentication enabled (SASL)
