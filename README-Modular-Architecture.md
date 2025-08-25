# GigaOffice Server - Modular Architecture

## Overview

The GigaOffice server has been refactored from a flat file structure to a hierarchical, domain-driven architecture. This modular approach improves maintainability, scalability, and follows Python best practices.

## Architecture Overview

### Directory Structure

```
app/
├── __init__.py
├── main.py                 # Main FastAPI application
├── lifespan.py            # Application lifecycle management
├── api/                   # API layer
│   ├── __init__.py
│   ├── router.py          # Main API router
│   └── endpoints/         # Domain-specific endpoints
│       ├── __init__.py
│       ├── health.py      # Health check endpoints
│       ├── ai.py          # AI processing endpoints
│       ├── prompts.py     # Prompts management
│       └── metrics.py     # Metrics and analytics
├── core/                  # Core configuration and utilities
│   ├── __init__.py
│   ├── config.py          # Application configuration
│   └── security.py        # Security utilities
├── db/                    # Database layer
│   ├── __init__.py
│   ├── session.py         # Database session management
│   ├── models.py          # SQLAlchemy ORM models
│   └── repositories/      # Repository pattern implementation
│       ├── __init__.py
│       ├── base.py        # Base repository
│       ├── ai_requests.py # AI requests repository
│       ├── prompts.py     # Prompts repository
│       └── users.py       # Users repository
├── services/              # Business logic layer
│   ├── __init__.py
│   ├── ai/                # AI service components
│   │   ├── __init__.py
│   │   ├── factory.py     # Service factory
│   │   ├── base.py        # Base service
│   │   ├── dryrun.py      # Dry-run implementation
│   │   ├── cloud.py       # Cloud implementation
│   │   └── mtls.py        # mTLS implementation
│   ├── kafka/             # Message queue services
│   │   ├── __init__.py
│   │   └── service.py     # Kafka service
│   └── prompts/           # Prompt management services
│       ├── __init__.py
│       └── manager.py     # Prompt manager
├── models/                # Data models
│   ├── __init__.py
│   ├── types.py           # Shared type definitions
│   ├── ai_requests.py     # AI request models
│   ├── users.py           # User models
│   ├── prompts.py         # Prompt models
│   └── health.py          # Health check models
└── utils/                 # Utility modules
    ├── __init__.py
    ├── logger.py          # Structured logging
    └── resource_loader.py # Resource loading utilities
```

## Key Features

### 1. Domain-Driven Design (DDD)
- **Separation of Concerns**: Each layer has a specific responsibility
- **Domain Models**: Clear separation between API models and database models
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation

### 2. Dependency Injection
- **Factory Pattern**: AI service instantiation based on configuration
- **Repository Dependencies**: Clean separation of data access
- **Configuration Management**: Centralized settings with environment variables

### 3. Modern FastAPI Practices
- **Lifespan Management**: Proper startup and shutdown handling
- **Structured Logging**: Comprehensive request and service logging
- **Rate Limiting**: Built-in API rate limiting
- **Error Handling**: Global exception handling with context

### 4. Scalability Features
- **Multi-Service Support**: Pluggable AI service backends
- **Caching**: Multi-level caching strategies
- **Queue Management**: Kafka integration for async processing
- **Performance Monitoring**: Built-in metrics and analytics

## Core Components

### Configuration (`app/core/config.py`)
Centralized configuration management using Pydantic settings:
- Environment variable support
- Type validation
- Application state tracking

### Database Layer (`app/db/`)
- **Session Management**: Enhanced connection pooling and health monitoring
- **ORM Models**: Improved relationships and validation
- **Repository Pattern**: Generic CRUD operations with domain-specific extensions

### Service Layer (`app/services/`)
- **AI Services**: Factory pattern for multiple deployment modes (dryrun, cloud, mTLS)
- **Kafka Service**: Enhanced message queuing with retry logic
- **Prompt Manager**: Cached prompt management with analytics

### API Layer (`app/api/`)
- **Domain-Specific Endpoints**: Organized by functional areas
- **Request/Response Models**: Type-safe API contracts
- **Authentication**: Integrated security management

## Configuration

### Environment Variables

```bash
# Application Settings
APP_NAME="GigaOffice AI Service"
APP_VERSION="1.0.0"
ENVIRONMENT="development"  # development, staging, production

# Database Configuration
DATABASE_URL="postgresql://user:password@localhost:5432/gigaoffice"

# GigaChat Configuration
GIGACHAT_RUN_MODE="dryrun"  # dryrun, cloud, mtls
GIGACHAT_GENERATE_MODEL="GigaChat"
GIGACHAT_CLASSIFY_MODEL="GigaChat"

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
KAFKA_CONSUMER_GROUP="gigaoffice"

# Security Settings
SECRET_KEY="your-secret-key"
ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8080"

# Logging
LOG_LEVEL="info"
LOG_FILE="logs/gigaoffice.log"
```

## Installation and Setup

### 1. Install Dependencies

```bash
pip install -r requirements-modular.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root with the configuration variables above.

### 3. Run Database Migrations

```bash
# Generate migration if using Alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 4. Start the Application

```bash
# Development
python -m app.main

# Production with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Testing

### Architecture Validation

Run the provided test script to validate the modular architecture:

```bash
python test_modular_architecture.py
```

This will test:
- Module imports
- Configuration loading
- FastAPI application creation
- Model instantiation
- Service integration

### Manual Testing

1. **Health Check**: `GET /api/health`
2. **API Documentation**: `GET /api/docs` (development only)
3. **Prompt Categories**: `GET /api/prompts/categories`
4. **Metrics**: `GET /api/metrics` (admin only)

## Migration from Legacy Structure

### What Was Changed

1. **File Organization**: Moved from flat structure to hierarchical modules
2. **Import Paths**: Updated all imports to use the new `app.*` namespace
3. **Configuration**: Centralized settings management
4. **Database Models**: Enhanced with better relationships and validation
5. **API Endpoints**: Split into domain-specific modules
6. **Service Layer**: Improved factory patterns and dependency injection

### Backward Compatibility

The API endpoints remain the same, ensuring backward compatibility for clients:
- `/api/health` - Health checks
- `/api/ai/*` - AI processing endpoints
- `/api/prompts/*` - Prompt management
- `/api/metrics` - Service metrics

## Development Guidelines

### Adding New Features

1. **Domain Identification**: Determine which domain the feature belongs to
2. **Model Definition**: Add Pydantic models in `app/models/`
3. **Database Models**: Update ORM models in `app/db/models.py`
4. **Repository**: Add repository methods in `app/db/repositories/`
5. **Service Logic**: Implement business logic in `app/services/`
6. **API Endpoints**: Add endpoints in appropriate `app/api/endpoints/`

### Code Quality

- Follow PEP 8 style guidelines
- Use type hints throughout
- Add docstrings to all public functions and classes
- Write unit tests for new features
- Use structured logging for debugging

## Performance Considerations

### Caching Strategy
- **TTL Cache**: Used for prompt categories and configurations
- **Service Cache**: AI service response caching
- **Database Cache**: SQLAlchemy query result caching

### Async Processing
- **Kafka Integration**: Async message processing
- **Background Tasks**: Non-blocking AI request processing
- **Connection Pooling**: Optimized database connections

### Monitoring
- **Structured Logging**: Comprehensive request tracking
- **Metrics Collection**: Performance and usage analytics
- **Health Checks**: Component-level health monitoring

## Security Features

### Authentication
- JWT token-based authentication
- Role-based access control (User, Admin, Premium)
- API key authentication for service endpoints

### Rate Limiting
- IP-based rate limiting
- User-based request quotas
- Endpoint-specific limits

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- CORS configuration

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all `__init__.py` files are present
2. **Configuration Issues**: Check environment variables and `.env` file
3. **Database Connection**: Verify DATABASE_URL and database availability
4. **Service Dependencies**: Ensure Kafka and other services are running

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=debug
python -m app.main
```

### Health Checks

Use the health endpoint to diagnose issues:
```bash
curl http://localhost:8000/api/health
```

## Future Enhancements

- **Microservices**: Split into separate services
- **API Versioning**: Support for multiple API versions
- **Advanced Caching**: Redis integration
- **Container Support**: Docker containerization
- **CI/CD Pipeline**: Automated testing and deployment

## Contributing

1. Follow the modular architecture principles
2. Add appropriate tests for new features
3. Update documentation for significant changes
4. Use the repository pattern for data access
5. Implement proper error handling and logging