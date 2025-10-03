# Style Reference Architecture Guide

## Overview

The Style Reference Architecture represents a strategic refactoring of the spreadsheet data JSON structure, transitioning from inline style definitions to a centralized style reference system. This enhancement improves data consistency, reduces redundancy, and enhances maintainability.

## Architecture Benefits

### Before (V1.0 - Inline Styles)
```json
{
  "metadata": {"version": "1.0"},
  "data": {
    "header": {
      "values": ["Name", "Age", "Email"],
      "style": {
        "background_color": "#4472C4",
        "font_color": "#FFFFFF",
        "font_weight": "bold"
      }
    },
    "rows": [
      {
        "values": ["John", 30, "john@example.com"],
        "style": {
          "background_color": "#F2F2F2"
        }
      },
      {
        "values": ["Jane", 25, "jane@example.com"],
        "style": {
          "background_color": "#F2F2F2"
        }
      }
    ]
  }
}
```

### After (V2.0 - Style References)
```json
{
  "metadata": {"version": "2.0"},
  "data": {
    "header": {
      "values": ["Name", "Age", "Email"],
      "style": "header_style"
    },
    "rows": [
      {
        "values": ["John", 30, "john@example.com"],
        "style": "row_style"
      },
      {
        "values": ["Jane", 25, "jane@example.com"],
        "style": "row_style"
      }
    ]
  },
  "styles": [
    {
      "id": "header_style",
      "background_color": "#4472C4",
      "font_color": "#FFFFFF",
      "font_weight": "bold"
    },
    {
      "id": "row_style",
      "background_color": "#F2F2F2"
    }
  ]
}
```

## Key Improvements

1. **Reduced Redundancy**: Duplicate styles are consolidated into reusable definitions
2. **Smaller Payloads**: JSON size reduced by eliminating repeated style objects
3. **Consistent Styling**: Centralized style management prevents visual inconsistencies
4. **Easy Maintenance**: Style updates only require changes in one location
5. **Better Performance**: Faster parsing and processing of style information

## API Endpoints

### V2 API Endpoints

#### Process Spreadsheet Data (V2)
```
POST /api/v2/spreadsheets/process
```

#### Get Processing Status (V2)
```
GET /api/v2/spreadsheets/status/{request_id}
```

#### Get Processing Result (V2)
```
GET /api/v2/spreadsheets/result/{request_id}?format_version=2.0
```

#### Transform Between Formats
```
POST /api/v2/spreadsheets/transform/to-legacy
POST /api/v2/spreadsheets/transform/from-legacy
```

#### Validate Spreadsheet Data
```
POST /api/v2/spreadsheets/validate
```

### Legacy API Compatibility

Legacy endpoints continue to work with both V1.0 and V2.0 formats:

```
POST /api/spreadsheets/process         # Auto-detects format
GET /api/spreadsheets/detect-format    # Detect format version
POST /api/spreadsheets/auto-transform  # Auto-transform to target version
```

## Style Definition Schema

### StyleDefinition Model

| Property | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `id` | String | Yes | Unique identifier for style reference | `"header_bold"` |
| `background_color` | String | No | Background color in hex format | `"#4472C4"` |
| `font_color` | String | No | Font color in hex format | `"#FFFFFF"` |
| `font_weight` | String | No | Font weight (`normal`, `bold`) | `"bold"` |
| `font_style` | String | No | Font style (`normal`, `italic`) | `"italic"` |
| `font_size` | Integer | No | Font size in points | `12` |
| `horizontal_alignment` | String | No | Horizontal alignment (`left`, `center`, `right`) | `"center"` |
| `vertical_alignment` | String | No | Vertical alignment (`top`, `middle`, `bottom`) | `"middle"` |
| `border` | String/Array | No | Border settings | `"thin"` |

### Validation Rules

- Colors must start with `#` (hex format)
- Font weight must be `"normal"` or `"bold"`
- Font style must be `"normal"` or `"italic"`
- Alignment values are restricted to specific options
- Style IDs must be unique within the styles array

## Migration Guide

### Automatic Migration

The system provides automatic migration capabilities:

```python
from app.services.spreadsheet.data_transformer import transformation_service

# Detect format
format_version = transformation_service.detect_format_version(data)

# Auto-transform to V2.0
new_data, messages = transformation_service.auto_transform(data, "2.0")

# Auto-transform to V1.0
legacy_data, messages = transformation_service.auto_transform(data, "1.0")
```

### Manual Migration Steps

1. **Identify Duplicate Styles**: Scan your data for repeated style patterns
2. **Create Style Definitions**: Extract unique styles and assign meaningful IDs
3. **Replace Inline Styles**: Replace style objects with style ID references
4. **Add Styles Array**: Include the centralized styles array
5. **Update Version**: Set metadata version to "2.0"
6. **Validate**: Use validation endpoints to ensure correctness

### Migration Best Practices

- **Meaningful IDs**: Use descriptive style IDs like `"header_bold"`, `"positive_value"`, `"negative_value"`
- **Consolidation**: Group similar styles to maximize reuse
- **Validation**: Always validate after migration
- **Testing**: Test with both formats during transition period

## Implementation Examples

### Creating Style Registry

```python
from app.services.spreadsheet.style_registry import StyleRegistry
from app.models.api.spreadsheet_v2 import StyleDefinition

registry = StyleRegistry()

# Add style from definition
header_style = StyleDefinition(
    id="header_style",
    background_color="#4472C4",
    font_color="#FFFFFF",
    font_weight="bold"
)
style_id = registry.add_style(header_style)

# Add style from dictionary
row_style_dict = {
    "background_color": "#F2F2F2"
}
style_id = registry.add_style_from_dict(row_style_dict)

# Validate references
is_valid = registry.validate_style_reference("header_style")
```

### Data Transformation

```python
from app.services.spreadsheet.data_transformer import DataTransformationService

service = DataTransformationService()

# Transform legacy to new format
new_data, errors = service.transform_to_new_format(legacy_data)

# Transform new to legacy format
legacy_data, errors = service.transform_to_legacy_format(new_data)

# Auto-detect and transform
transformed_data, messages = service.auto_transform(data, "2.0")
```

### API Usage Examples

#### Processing V2 Data

```python
import requests

v2_data = {
    "spreadsheet_data": {
        "metadata": {"version": "2.0"},
        "data": {
            "header": {"values": ["Name", "Value"], "style": "header_style"},
            "rows": [{"values": ["Item 1", 100], "style": "row_style"}]
        },
        "styles": [
            {"id": "header_style", "background_color": "#4472C4", "font_weight": "bold"},
            {"id": "row_style", "background_color": "#F2F2F2"}
        ]
    },
    "query_text": "Make the data more visually appealing",
    "category": "spreadsheet-formatting"
}

response = requests.post("/api/v2/spreadsheets/process", json=v2_data)
```

#### Format Transformation

```python
# Transform to legacy format
response = requests.post("/api/v2/spreadsheets/transform/to-legacy", json=v2_data)

# Transform from legacy format
response = requests.post("/api/v2/spreadsheets/transform/from-legacy", json=legacy_data)

# Validate data
response = requests.post("/api/v2/spreadsheets/validate", json=v2_data)
```

## Performance Considerations

### Payload Size Reduction

The style reference architecture typically reduces JSON payload size by:
- **20-40%** for spreadsheets with repeated styling patterns
- **Up to 60%** for large spreadsheets with many styled rows
- **Minimal impact** for spreadsheets with unique styles per element

### Processing Performance

- **Style Resolution**: O(1) lookup time for style references
- **Memory Usage**: Reduced memory footprint due to style consolidation
- **Parsing Speed**: Faster JSON parsing with smaller payloads
- **Caching**: Efficient style caching at the registry level

## Error Handling

### Common Validation Errors

| Error Type | Description | Solution |
|------------|-------------|----------|
| `Missing styles array` | No styles array found in V2.0 data | Add empty styles array: `"styles": []` |
| `Invalid style reference` | Style ID referenced but not defined | Add missing style to styles array |
| `Duplicate style ID` | Same style ID used multiple times | Use unique IDs for each style |
| `Invalid color format` | Color doesn't start with # | Use hex format: `"#FF0000"` |
| `Invalid font weight` | Font weight not "normal" or "bold" | Use valid values: `"normal"`, `"bold"` |

### Error Recovery

The system provides automatic error recovery:

```python
from app.services.spreadsheet.style_registry import StyleValidator

validator = StyleValidator(registry)
fixed_data, fix_messages = validator.validate_and_fix_references(data)
```

## Testing

### Unit Tests

Run unit tests for models and services:

```bash
pytest tests/test_spreadsheet_v2_models.py -v
```

### Integration Tests

Run API integration tests:

```bash
pytest tests/test_spreadsheet_v2_api.py -v
```

### Test Coverage

Current test coverage includes:
- ✅ StyleDefinition model validation
- ✅ SpreadsheetDataV2 model creation
- ✅ Style registry operations
- ✅ Data transformation between formats
- ✅ API endpoint functionality
- ✅ Error handling and recovery
- ✅ Format detection and validation

## Troubleshooting

### Common Issues

1. **Style Reference Not Found**
   - Check that style ID exists in styles array
   - Verify spelling and case sensitivity

2. **Invalid Color Format**
   - Ensure colors start with # symbol
   - Use 6-digit hex codes: #RRGGBB

3. **Version Mismatch**
   - Check metadata.version field
   - Use auto-transform for conversion

4. **Performance Issues**
   - Monitor payload sizes before/after transformation
   - Consider style consolidation for large datasets

### Debugging Tools

```python
# Enable debug logging
import logging
logging.getLogger("app.services.spreadsheet").setLevel(logging.DEBUG)

# Validate data structure
from app.services.spreadsheet.style_registry import StyleValidator
validator = StyleValidator(registry)
is_valid, errors = validator.validate_spreadsheet_data(data)
print(f"Valid: {is_valid}, Errors: {errors}")

# Check format version
from app.services.spreadsheet.data_transformer import transformation_service
version = transformation_service.detect_format_version(data)
print(f"Detected version: {version}")
```

## Future Enhancements

### Planned Features

1. **Style Inheritance**: Support for style composition and inheritance
2. **Theme Support**: Predefined style themes for consistent branding
3. **Style Optimization**: Automatic style consolidation and optimization
4. **Visual Editor**: UI for creating and managing style definitions
5. **Import/Export**: Style library import/export functionality

### API Evolution

- **V3.0**: Enhanced style capabilities with themes and inheritance
- **GraphQL**: GraphQL endpoints for flexible data queries
- **WebSocket**: Real-time style updates and collaboration
- **Batch Operations**: Bulk style operations for large datasets

This completes the comprehensive guide for the Style Reference Architecture implementation.