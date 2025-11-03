# Chart Generation API Documentation

## Overview

The Chart Generation API provides intelligent chart creation capabilities for the GigaOffice server. It leverages AI-powered analysis to recommend optimal chart types and generates R7-Office compatible chart configurations.

## Key Features

- **AI-Powered Chart Recommendations**: Uses GigaChat to analyze data patterns and suggest optimal chart types
- **R7-Office Compatibility**: Generates chart configurations compatible with R7-Office API standards
- **Intelligent Data Analysis**: Automatically detects time series, categorical, correlation, and part-to-whole patterns
- **Comprehensive Validation**: Validates chart configurations for errors and compatibility issues
- **Asynchronous Processing**: Supports both immediate and queued processing for complex datasets
- **Multiple Chart Types**: Supports column, line, pie, area, scatter, histogram, bar, and doughnut charts

## API Endpoints

### Base URL
```
/api/v1/charts
```

## Endpoints Reference

### 1. Generate Chart (Immediate/Queued)

**POST** `/generate`

Generates chart with AI assistance. Simple charts are processed immediately, complex charts are queued.

#### Request Body
```json
{
  "data_source": {
    "worksheet_name": "Sheet1",
    "data_range": "A1:B10",
    "headers": ["Month", "Sales"],
    "data_rows": [
      ["Jan", 15000],
      ["Feb", 18000],
      ["Mar", 22000]
    ],
    "column_types": {
      "0": "string",
      "1": "number"
    }
  },
  "chart_instruction": "Create a line chart showing sales trends over time",
  "chart_preferences": {
    "preferred_chart_types": ["line", "column"],
    "color_preference": "modern",
    "size_preference": "medium",
    "style_preference": "standard"
  },
  "r7_office_config": {
    "api_version": "1.0",
    "compatibility_mode": true,
    "custom_properties": {}
  }
}
```

#### Response (Immediate)
```json
{
  "success": true,
  "request_id": "uuid-string",
  "status": "completed",
  "chart_config": {
    "chart_type": "line",
    "title": "Sales Trends Over Time",
    "subtitle": null,
    "data_range": "A1:B10",
    "series_config": {
      "x_axis_column": 0,
      "y_axis_columns": [1],
      "series_names": ["Sales"],
      "show_data_labels": false,
      "smooth_lines": true
    },
    "position": {
      "x": 450,
      "y": 50,
      "width": 600,
      "height": 400,
      "anchor_cell": null
    },
    "styling": {
      "color_scheme": "modern",
      "font_family": "Arial",
      "font_size": 12,
      "background_color": null,
      "border_style": "none",
      "legend_position": "bottom",
      "custom_colors": null
    },
    "r7_office_properties": {
      "api_version": "1.0",
      "chart_object_name": "Chart1",
      "enable_animation": true,
      "enable_3d": false
    }
  },
  "message": "Chart generated successfully",
  "error_message": null,
  "tokens_used": 150,
  "processing_time": 1.2
}
```

#### Response (Queued)
```json
{
  "success": true,
  "request_id": "uuid-string",
  "status": "queued",
  "chart_config": null,
  "message": "Chart generation request queued for processing",
  "error_message": null,
  "tokens_used": null,
  "processing_time": null
}
```

---

### 2. Process Chart Request (Always Queued)

**POST** `/process`

Always processes chart generation asynchronously through the queue system.

#### Request Body
Same as `/generate` endpoint.

#### Response
```json
{
  "success": true,
  "request_id": "uuid-string",
  "status": "queued",
  "chart_config": null,
  "message": "Chart generation request queued for processing",
  "error_message": null
}
```

---

### 3. Get Chart Generation Status

**GET** `/status/{request_id}`

Retrieves the current status of a chart generation request.

#### Parameters
- `request_id` (path): UUID of the chart generation request

#### Response
```json
{
  "success": true,
  "request_id": "uuid-string",
  "status": "processing",
  "message": "Chart generation in progress",
  "error_message": null
}
```

#### Status Values
- `pending`: Request is queued but not started
- `processing`: Chart generation in progress
- `completed`: Chart generation completed successfully
- `failed`: Chart generation failed

---

### 4. Get Chart Generation Result

**GET** `/result/{request_id}`

Retrieves the completed chart configuration.

#### Parameters
- `request_id` (path): UUID of the chart generation request

#### Response (Completed)
```json
{
  "success": true,
  "status": "completed",
  "message": "Chart generated successfully",
  "chart_config": {
    // Complete ChartConfig object
  },
  "tokens_used": 200,
  "processing_time": 3.5
}
```

#### Response (Pending/Failed)
```json
{
  "success": false,
  "status": "processing",
  "message": "Chart generation is still in progress",
  "chart_config": null,
  "tokens_used": null,
  "processing_time": null
}
```

---

### 5. Validate Chart Configuration

**POST** `/validate`

Validates a chart configuration for errors and R7-Office compatibility.

#### Request Body
```json
{
  "chart_config": {
    "chart_type": "column",
    "title": "Sales Analysis",
    "data_range": "A1:B10",
    "series_config": {
      "x_axis_column": 0,
      "y_axis_columns": [1],
      "series_names": ["Sales"],
      "show_data_labels": false,
      "smooth_lines": false
    },
    "position": {
      "x": 100,
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
    "r7_office_properties": {}
  }
}
```

#### Response
```json
{
  "success": true,
  "is_valid": true,
  "is_r7_office_compatible": true,
  "validation_errors": [],
  "compatibility_warnings": [
    "Font 'Comic Sans' may not be available in R7-Office"
  ],
  "message": "Validation completed. Quality score: 0.95"
}
```

---

### 6. Get Supported Chart Types

**GET** `/types`

Returns information about supported chart types.

#### Response
```json
{
  "success": true,
  "supported_types": {
    "column": {
      "name": "Column Chart",
      "description": "Best for comparing values across categories",
      "use_cases": ["Categorical comparisons", "Sales by region", "Survey responses"]
    },
    "line": {
      "name": "Line Chart",
      "description": "Ideal for showing trends over time",
      "use_cases": ["Time series data", "Stock prices", "Temperature changes"]
    },
    "pie": {
      "name": "Pie Chart",
      "description": "Perfect for showing parts of a whole",
      "use_cases": ["Market share", "Budget allocation", "Survey results"]
    }
  },
  "total_count": 8
}
```

---

### 7. Get Chart Examples

**GET** `/examples`

Returns example chart configurations and usage tips.

#### Response
```json
{
  "success": true,
  "examples": {
    "sales_by_month": {
      "description": "Monthly sales data visualization",
      "chart_type": "line",
      "sample_data": {
        "headers": ["Month", "Sales"],
        "data_rows": [
          ["Jan", 15000],
          ["Feb", 18000],
          ["Mar", 22000]
        ]
      },
      "recommended_instruction": "Create a line chart showing sales trends over the first half of the year"
    }
  },
  "usage_tips": [
    "Use clear, descriptive instructions for better AI recommendations",
    "Ensure data has proper headers and consistent formatting",
    "Consider your audience when choosing chart types"
  ]
}
```

---

## Data Models

### DataSource
```json
{
  "worksheet_name": "Sheet1",           // Worksheet name
  "data_range": "A1:B10",             // R7-Office cell range
  "headers": ["Month", "Sales"],       // Column headers
  "data_rows": [                       // Data rows
    ["Jan", 1000],
    ["Feb", 1200]
  ],
  "column_types": {                    // Column type mapping
    "0": "string",
    "1": "number"
  }
}
```

### ChartConfig
```json
{
  "chart_type": "column",              // Chart type enum
  "title": "Chart Title",             // Main title
  "subtitle": "Optional subtitle",     // Optional subtitle
  "data_range": "A1:B10",             // Data range
  "series_config": {                   // Series configuration
    "x_axis_column": 0,
    "y_axis_columns": [1],
    "series_names": ["Sales"],
    "show_data_labels": false,
    "smooth_lines": false
  },
  "position": {                        // Chart position
    "x": 100,
    "y": 50,
    "width": 600,
    "height": 400,
    "anchor_cell": "D5"
  },
  "styling": {                         // Chart styling
    "color_scheme": "office",
    "font_family": "Arial",
    "font_size": 12,
    "background_color": "#FFFFFF",
    "border_style": "solid",
    "legend_position": "bottom",
    "custom_colors": ["#FF0000", "#00FF00"]
  },
  "r7_office_properties": {            // R7-Office specific
    "api_version": "1.0",
    "enable_animation": true,
    "enable_3d": false
  }
}
```

### ChartPreferences
```json
{
  "preferred_chart_types": ["line", "column"],  // Preferred types
  "color_preference": "modern",                 // Color scheme preference
  "size_preference": "medium",                  // Size preference
  "style_preference": "standard"                // Style preference
}
```

---

## Chart Type Recommendations

The AI analyzes your data to recommend the most appropriate chart type:

### Time Series Data
- **Recommended**: Line Chart, Area Chart
- **Indicators**: Date/time columns, temporal progression
- **Use Cases**: Stock prices, temperature over time, website traffic

### Categorical Comparisons
- **Recommended**: Column Chart, Bar Chart
- **Indicators**: Text categories with numerical values
- **Use Cases**: Sales by region, survey responses, performance metrics

### Part-to-Whole Relationships
- **Recommended**: Pie Chart, Doughnut Chart
- **Indicators**: 2-8 categories with positive values
- **Use Cases**: Market share, budget allocation, demographics

### Correlations
- **Recommended**: Scatter Plot
- **Indicators**: Two numerical variables
- **Use Cases**: Height vs weight, price vs quality, performance analysis

### Distribution Analysis
- **Recommended**: Histogram
- **Indicators**: Single numerical variable
- **Use Cases**: Age distribution, test scores, quality measurements

---

## Best Practices

### Data Preparation
1. **Clean Headers**: Use clear, descriptive column headers
2. **Consistent Data Types**: Ensure consistent data formatting within columns
3. **Complete Data**: Minimize missing values for better chart quality
4. **Appropriate Size**: 3-1000 rows for optimal performance

### Chart Instructions
1. **Be Specific**: "Create a line chart showing sales trends" vs "Make a chart"
2. **Include Context**: Mention the purpose and audience
3. **Specify Preferences**: Include color schemes, styling preferences
4. **Consider R7-Office**: Mention if specific R7-Office features are needed

### Performance Optimization
1. **Batch Processing**: Use `/process` endpoint for multiple complex charts
2. **Data Limits**: Keep datasets under 1000 rows for immediate processing
3. **Simple Charts**: Use basic chart types for faster generation
4. **Caching**: Cache frequently used chart configurations

---

## Error Handling

### Common Error Codes

#### 400 - Bad Request
```json
{
  "detail": "Invalid data source: Data range cannot be empty"
}
```

#### 404 - Not Found
```json
{
  "detail": "Chart request not found"
}
```

#### 422 - Validation Error
```json
{
  "detail": [
    {
      "loc": ["data_source", "data_range"],
      "msg": "Data range must be in format 'A1:B10'",
      "type": "value_error"
    }
  ]
}
```

#### 429 - Rate Limited
```json
{
  "detail": "Rate limit exceeded: 10 requests per minute"
}
```

#### 500 - Internal Server Error
```json
{
  "detail": "Chart generation failed: AI service unavailable"
}
```

---

## Integration Examples

### Python Client
```python
import requests

# Generate a chart
response = requests.post(
    "https://api.gigaoffice.com/api/v1/charts/generate",
    json={
        "data_source": {
            "worksheet_name": "Sales Data",
            "data_range": "A1:B12",
            "headers": ["Month", "Revenue"],
            "data_rows": [
                ["Jan", 50000], ["Feb", 55000], ["Mar", 48000]
            ]
        },
        "chart_instruction": "Create a line chart showing monthly revenue trends"
    }
)

if response.status_code == 200:
    chart_data = response.json()
    if chart_data["status"] == "completed":
        chart_config = chart_data["chart_config"]
        print(f"Chart generated: {chart_config['title']}")
    else:
        request_id = chart_data["request_id"]
        print(f"Chart queued with ID: {request_id}")
```

### JavaScript Client
```javascript
const generateChart = async (dataSource, instruction) => {
  const response = await fetch('/api/v1/charts/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      data_source: dataSource,
      chart_instruction: instruction
    })
  });

  const result = await response.json();
  
  if (result.status === 'completed') {
    return result.chart_config;
  } else {
    // Poll for completion
    return await pollForCompletion(result.request_id);
  }
};
```

---

## R7-Office Integration

### Chart Configuration Mapping

The generated chart configurations map directly to R7-Office API calls:

```javascript
// Apply generated configuration to R7-Office
const applyChartConfig = (chartConfig) => {
  const chart = oWorksheet.AddChart();
  
  // Basic properties
  chart.SetChartType(chartConfig.chart_type);
  chart.SetTitle(chartConfig.title);
  chart.SetChartData(chartConfig.data_range);
  
  // Position and size
  chart.SetPosition(
    chartConfig.position.x,
    chartConfig.position.y
  );
  chart.SetSize(
    chartConfig.position.width,
    chartConfig.position.height
  );
  
  // Styling
  chart.SetColorScheme(chartConfig.styling.color_scheme);
  chart.SetLegendPos(chartConfig.styling.legend_position);
  
  // R7-Office specific properties
  Object.entries(chartConfig.r7_office_properties).forEach(([key, value]) => {
    chart.SetProperty(key, value);
  });
};
```

### Compatibility Notes

1. **Chart Types**: All supported chart types are compatible with R7-Office
2. **Colors**: Custom colors use hex format supported by R7-Office
3. **Fonts**: Recommended fonts are available in standard R7-Office installations
4. **Positioning**: Coordinates use R7-Office pixel-based positioning
5. **Data Ranges**: Cell ranges use R7-Office format (A1:B10)

---

## Support and Troubleshooting

### Common Issues

1. **Validation Errors**: Check data format and chart configuration structure
2. **Long Processing Times**: Large datasets may take several minutes to process
3. **Rate Limiting**: Implement exponential backoff for repeated requests
4. **AI Service Unavailable**: Use fallback chart type recommendations

### Getting Help

- Check the `/examples` endpoint for sample configurations
- Use the `/validate` endpoint to debug chart configurations
- Monitor request status using the `/status/{request_id}` endpoint
- Review error messages for specific validation issues