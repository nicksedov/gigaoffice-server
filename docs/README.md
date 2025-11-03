# Chart Generation API Documentation

## Overview

The Chart Generation API provides intelligent chart creation capabilities for the GigaOffice system, enabling R7-Office plugins to generate data visualizations using AI-powered analysis. The API supports multiple chart types, data pattern recognition, and R7-Office compatibility validation.

## Features

- 🤖 **AI-Powered Chart Recommendations**: Analyzes data patterns to suggest optimal chart types
- 📊 **Multiple Chart Types**: Supports column, line, pie, area, scatter, bar, histogram, doughnut, box plot, and radar charts
- ⚡ **Asynchronous Processing**: Handles complex chart generation through Kafka queuing
- ✅ **Comprehensive Validation**: Validates chart configurations and R7-Office compatibility
- 🎨 **Configuration Optimization**: AI-powered optimization for better visualization
- 📈 **Performance Monitoring**: Built-in metrics collection and monitoring
- 🔄 **Error Handling**: Comprehensive error handling with retry mechanisms and fallbacks

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Apache Kafka 3.5+
- Redis 7+
- GigaChat API credentials

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd gigaoffice-server
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run with Docker Compose:**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

### Basic Usage

```python
import requests

# Generate a chart
response = requests.post(
    "http://localhost:8000/api/v1/charts/generate",
    json={
        "data_source": {
            "worksheet_name": "Sheet1",
            "data_range": "A1:B4",
            "headers": ["Month", "Sales"],
            "data_rows": [
                ["Jan", 1000],
                ["Feb", 1200],
                ["Mar", 1100]
            ]
        },
        "chart_instruction": "Create a column chart showing monthly sales"
    },
    headers={"Authorization": "Bearer your-token"}
)

chart_config = response.json()["chart_config"]
```

## API Endpoints

### Chart Generation

#### `POST /api/v1/charts/generate`
Generate chart with immediate or queued processing based on data complexity.

**Request Body:**
```json
{
    "data_source": {
        "worksheet_name": "Sheet1",
        "data_range": "A1:B4",
        "headers": ["Month", "Sales"],
        "data_rows": [
            ["Jan", 1000],
            ["Feb", 1200],
            ["Mar", 1100]
        ],
        "column_types": {"0": "string", "1": "number"}
    },
    "chart_instruction": "Create a column chart showing monthly sales",
    "chart_preferences": {
        "preferred_chart_types": ["column", "bar"],
        "color_preference": "modern",
        "size_preference": "medium"
    },
    "r7_office_config": {
        "api_version": "1.2",
        "compatibility_mode": true
    }
}
```

**Response:**
```json
{
    "success": true,
    "request_id": "uuid-string",
    "status": "completed",
    "chart_config": {
        "chart_type": "column",
        "title": "Monthly Sales",
        "data_range": "A1:B4",
        "series_config": {
            "x_axis_column": 0,
            "y_axis_columns": [1],
            "series_names": ["Sales"],
            "show_data_labels": false
        },
        "position": {
            "x": 450,
            "y": 50,
            "width": 600,
            "height": 400
        },
        "styling": {
            "color_scheme": "office",
            "font_family": "Arial",
            "font_size": 12,
            "legend_position": "bottom"
        },
        "r7_office_properties": {
            "api_version": "1.2",
            "enable_animation": true
        }
    },
    "tokens_used": 150,
    "processing_time": 1.2
}
```

#### `POST /api/v1/charts/process`
Queue chart generation for asynchronous processing.

#### `GET /api/v1/charts/status/{request_id}`
Get processing status of a chart generation request.

#### `GET /api/v1/charts/result/{request_id}`
Retrieve completed chart configuration.

### Validation

#### `POST /api/v1/charts/validate`
Validate chart configuration and R7-Office compatibility.

**Request Body:**
```json
{
    "chart_config": {
        // Complete chart configuration object
    }
}
```

**Response:**
```json
{
    "success": true,
    "is_valid": true,
    "is_r7_office_compatible": true,
    "validation_errors": [],
    "compatibility_warnings": [],
    "message": "Validation completed. Quality score: 0.95"
}
```

### Optimization

#### `POST /api/v1/charts/optimize`
Optimize chart configuration for better visualization.

**Parameters:**
- `optimization_goals`: Array of optimization goals
  - `visual_clarity`: Improve readability and visual appeal
  - `data_presentation`: Maximize data comprehension
  - `r7_office_performance`: Optimize for R7-Office rendering
  - `user_experience`: Enhance accessibility and usability

### Utility Endpoints

#### `GET /api/v1/charts/types`
Get supported chart types with descriptions and requirements.

#### `GET /api/v1/charts/examples`
Get example chart configurations for different use cases.

#### `GET /api/v1/charts/queue/status`
Get Kafka queue status and processing metrics.

#### `GET /api/v1/charts/metrics`
Get performance metrics and system health.

**Parameters:**
- `time_range`: Time range in minutes (default: 60)

#### `GET /api/v1/charts/metrics/trends`
Get performance trends over time.

**Parameters:**
- `hours`: Number of hours for trend analysis (default: 24)

## Data Models

### Chart Types

| Type | Description | Use Cases | R7-Office Support |
|------|-------------|-----------|-------------------|
| `column` | Column chart for categorical comparisons | Sales by region, survey responses | Full |
| `line` | Line chart for trends over time | Stock prices, temperature changes | Full |
| `pie` | Pie chart for parts of a whole | Market share, budget allocation | Full |
| `area` | Area chart for trends and proportions | Resource usage, population growth | Full |
| `scatter` | Scatter plot for correlations | Height vs weight, performance analysis | Full |
| `bar` | Horizontal bar chart | Rankings, survey responses | Full |
| `histogram` | Distribution of numerical data | Age distribution, test scores | Full |
| `doughnut` | Modern alternative to pie chart | Resource allocation, progress indicators | Full |
| `box_plot` | Statistical distribution with quartiles | Outlier detection, data analysis | Limited |
| `radar` | Multi-dimensional comparison | Performance comparison, skills assessment | Limited |

### Data Source Structure

```json
{
    "worksheet_name": "string",
    "data_range": "string (R7-Office format: A1:B10)",
    "headers": ["string array"],
    "data_rows": [["mixed array"]],
    "column_types": {"index": "type"}
}
```

### Chart Configuration Structure

```json
{
    "chart_type": "enum",
    "title": "string",
    "subtitle": "string (optional)",
    "data_range": "string",
    "series_config": {
        "x_axis_column": "integer",
        "y_axis_columns": ["integer array"],
        "series_names": ["string array"],
        "show_data_labels": "boolean",
        "smooth_lines": "boolean"
    },
    "position": {
        "x": "integer",
        "y": "integer", 
        "width": "integer",
        "height": "integer",
        "anchor_cell": "string (optional)"
    },
    "styling": {
        "color_scheme": "enum",
        "font_family": "string",
        "font_size": "integer",
        "background_color": "string (hex)",
        "border_style": "enum",
        "legend_position": "enum",
        "custom_colors": ["string array (hex)"]
    },
    "r7_office_properties": {
        "api_version": "string",
        "enable_animation": "boolean",
        "enable_3d": "boolean"
    }
}
```

## Authentication

The API uses Bearer token authentication:

```bash
curl -H "Authorization: Bearer your-token" \
     -X POST http://localhost:8000/api/v1/charts/generate \
     -d @chart_request.json
```

## Rate Limiting

- **Chart Generation**: 10 requests per minute per user
- **Validation**: 100 requests per minute per user
- **Utility Endpoints**: No rate limiting

## Error Handling

### Error Response Format

```json
{
    "success": false,
    "error_code": "VALIDATION_ERROR",
    "message": "Human-readable error description",
    "details": "Technical error information",
    "suggestions": ["Recommended resolution steps"]
}
```

### Error Categories

- `VALIDATION_ERROR`: Input validation failures
- `AI_SERVICE_ERROR`: GigaChat service issues
- `DATABASE_ERROR`: Database connection problems
- `KAFKA_ERROR`: Message queue issues
- `TIMEOUT_ERROR`: Request timeout
- `RESOURCE_ERROR`: Resource limitations

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses | localhost:9092 | Yes |
| `GIGACHAT_CLIENT_ID` | GigaChat API client ID | - | Yes |
| `GIGACHAT_CLIENT_SECRET` | GigaChat API client secret | - | Yes |
| `PORT` | API server port | 8000 | No |
| `LOG_LEVEL` | Logging level | INFO | No |
| `RATE_LIMIT_REQUESTS` | Rate limit per window | 100 | No |
| `MAX_REQUEST_SIZE` | Maximum request size | 10MB | No |

### GigaChat Configuration

The API integrates with GigaChat for AI-powered chart analysis:

```bash
export GIGACHAT_CLIENT_ID="your_client_id"
export GIGACHAT_CLIENT_SECRET="your_client_secret"
export GIGACHAT_SCOPE="GIGACHAT_API_PERS"
```

## Deployment

### Development

```bash
# Using Docker Compose
./scripts/deploy.sh

# Manual setup
python -m uvicorn app.main:app --reload --port 8000
```

### Production

```bash
# Production deployment
chmod +x scripts/deploy_production.sh
sudo ./scripts/deploy_production.sh
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chart-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chart-api
  template:
    metadata:
      labels:
        app: chart-api
    spec:
      containers:
      - name: chart-api
        image: gigaoffice/chart-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
```

## Monitoring

### Health Checks

```bash
curl http://localhost:8000/api/v1/health
```

### Metrics

```bash
# Get performance metrics
curl "http://localhost:8000/api/v1/charts/metrics?time_range=60"

# Get trends
curl "http://localhost:8000/api/v1/charts/metrics/trends?hours=24"
```

### Logging

Logs are structured and include:
- Request ID tracking
- Performance metrics
- Error categorization
- User context

### Grafana Dashboards

Access monitoring dashboards at `http://localhost:3000`:
- API performance metrics
- Chart generation statistics
- Error rates and categories
- System resource usage

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m "unit"
pytest -m "integration"
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/
mypy app/
```

### Adding New Chart Types

1. Update `ChartType` enum in `app/models/api/chart.py`
2. Add validation logic in `app/services/chart/validation.py`
3. Update intelligence service pattern detection
4. Add tests for the new chart type
5. Update documentation

## Troubleshooting

### Common Issues

**Issue**: Chart generation fails with "AI service timeout"
**Solution**: Check GigaChat credentials and network connectivity

**Issue**: High error rates in production
**Solution**: Check database connections and Kafka broker health

**Issue**: Slow chart generation
**Solution**: Review data complexity and consider async processing

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

### Support

For technical support:
1. Check the logs: `docker-compose logs chart-api`
2. Review metrics: `curl http://localhost:8000/api/v1/charts/metrics`
3. Validate configuration: `curl http://localhost:8000/api/v1/health`

## API Reference

Complete API reference with interactive documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`