# Histogram API Quick Reference

## Endpoints

### 1. Submit Histogram Analysis Request
```http
POST /api/v1/histograms/process
Content-Type: application/json
Authorization: Bearer <token>

{
  "spreadsheet_data": {
    "metadata": {"version": "1.0"},
    "worksheet": {"name": "Data", "range": "A1:B100"},
    "data": {
      "header": {"values": ["Product", "Price"], "range": "A1:B1"},
      "rows": []
    },
    "columns": [
      {
        "index": 0,
        "format": "General",
        "range": "A2:A100"
      },
      {
        "index": 1,
        "format": "#,##0.00",
        "range": "B2:B100",
        "min": 50.0,
        "max": 5000.0,
        "median": 850.0,
        "count": 99
      }
    ]
  },
  "query_text": "Построй гистограмму распределения цен",
  "category": "data-histogram"
}
```

**Response:**
```json
{
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Histogram analysis request queued for processing",
  "error_message": null
}
```

### 2. Check Processing Status
```http
GET /api/v1/histograms/status/550e8400-e29b-41d4-a716-446655440000
```

**Response (Processing):**
```json
{
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Histogram analysis in progress",
  "error_message": null
}
```

**Response (Completed):**
```json
{
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Histogram analysis completed successfully",
  "error_message": null
}
```

### 3. Get Analysis Result
```http
GET /api/v1/histograms/result/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "success": true,
  "status": "completed",
  "message": "Histogram analysis completed successfully",
  "histogram_config": {
    "source_columns": [1],
    "recommended_bins": 12,
    "range_column_name": "Диапазон цен (руб.)",
    "count_column_name": "Количество товаров"
  },
  "tokens_used": 523,
  "processing_time": 2.14
}
```

## Statistical Metadata Fields

For numerical columns, include these optional fields:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `range` | string | Cell range (e.g., "B2:B50") | **Yes** |
| `min` | float | Minimum value | No |
| `max` | float | Maximum value | No |
| `median` | float | Median value | No |
| `count` | integer | Number of values | No |

### Validation Rules:
- `min <= max`
- `min <= median <= max`
- `count > 0`

## Histogram Configuration Response

The `histogram_config` object contains:

| Field | Type | Description |
|-------|------|-------------|
| `source_columns` | int[] | Indices of columns to use for histogram |
| `recommended_bins` | int | Optimal number of bins (typically 5-20) |
| `range_column_name` | string | Russian name for bin range column |
| `count_column_name` | string | Russian name for frequency column |

## Status Values

| Status | Meaning |
|--------|---------|
| `queued` | Request submitted, waiting for processing |
| `pending` | Request in queue |
| `processing` | Currently being analyzed by GigaChat |
| `completed` | Analysis finished, result available |
| `failed` | Analysis failed, check error_message |

## Error Handling

### 400 Bad Request
```json
{
  "detail": "Column 1: min must be <= max"
}
```

Common validation errors:
- Invalid statistical metadata (min > max)
- Missing required fields
- Invalid range format

### 404 Not Found
```json
{
  "detail": "Histogram request not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to queue histogram analysis request"
}
```

## Rate Limiting

- **Limit:** 10 requests per minute per IP address
- **Header:** Returns rate limit information in response headers

## Example Use Cases

### 1. Price Distribution
```json
{
  "query_text": "Построй гистограмму распределения цен товаров",
  "columns": [{
    "index": 1,
    "range": "B2:B100",
    "min": 50.0,
    "max": 5000.0,
    "median": 850.0,
    "count": 99
  }]
}
```

### 2. Temperature Analysis
```json
{
  "query_text": "Покажи распределение температуры за месяц",
  "columns": [{
    "index": 1,
    "range": "B2:B32",
    "min": 18.5,
    "max": 23.8,
    "median": 21.2,
    "count": 31
  }]
}
```

### 3. Multi-Column Comparison
```json
{
  "query_text": "Сравни распределение продаж в двух регионах",
  "columns": [
    {
      "index": 1,
      "range": "B2:B200",
      "min": 15000.0,
      "max": 98000.0,
      "median": 45000.0,
      "count": 199
    },
    {
      "index": 2,
      "range": "C2:C200",
      "min": 12000.0,
      "max": 105000.0,
      "median": 48000.0,
      "count": 199
    }
  ]
}
```

## Bin Calculation Methods

GigaChat uses these formulas to determine optimal bin count:

**Sturges' Rule (normal distributions):**
```
bins ≈ 1 + log₂(n)
```

**Rice Rule (skewed distributions):**
```
bins ≈ 2 × n^(1/3)
```

The AI considers:
- Data range (max - min)
- Data count
- User query context
- Practical limits (5-20 bins)

## Integration Notes

1. **Asynchronous Processing:** Results are not immediate. Poll status endpoint until "completed"
2. **Kafka Queue:** Requests processed through existing Kafka infrastructure
3. **Database Persistence:** All requests stored in AIRequest table
4. **GigaChat Integration:** Requires prompt configuration in `/resources/prompts/data-histogram/`
