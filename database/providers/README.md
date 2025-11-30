# Data Providers

This directory contains data providers that extract data from various sources and return them in CSV format with semicolon delimiter.

## Overview

The provider-based architecture separates data extraction from database operations, following these principles:

- **Separation of Concerns**: Providers only extract and format data
- **Single Responsibility**: Each provider handles one specific data source
- **Standardized Output**: All providers return CSV format with semicolon delimiter
- **Testability**: Providers can be tested without database dependencies

## Providers

### 1. TableHeadersProvider

Extracts unique table header terms from CSV file.

**Data Source**: `database/embeddings/table_headers/table_headers.csv`

**Output Format**: Single column CSV
```
text
academic year
accept
access
...
```

**Usage**:
```python
from database.providers import TableHeadersProvider

provider = TableHeadersProvider()
csv_data = provider.get_data()
print(csv_data)
```

### 2. ClassificationPromptsProvider

Extracts prompt examples from classifier category YAML files.

**Data Source**: `resources/prompts/classifier/example_*.yaml`

**Output Format**: Two column CSV
```
text;response_json
Найди минимальное значение;{"category": "spreadsheet-analysis", ...}
Построй график продаж;{"category": "data-chart", ...}
...
```

**Usage**:
```python
from database.providers import ClassificationPromptsProvider

provider = ClassificationPromptsProvider()
csv_data = provider.get_data()
print(csv_data)
```

### 3. CategorizedPromptsProvider

Extracts prompt examples from all category YAML files.

**Data Source**: `resources/prompts/*/example_*.yaml`

**Output Format**: Four column CSV
```
category;text;request_json;response_json
classifier;Найди минимальное значение;;{"category": "spreadsheet-analysis", ...}
data-chart;Построй график продаж;{"data_range": "A1:B16", ...};{"chart_type": "lineNormal", ...}
...
```

**Usage**:
```python
from database.providers import CategorizedPromptsProvider

provider = CategorizedPromptsProvider()
csv_data = provider.get_data()
print(csv_data)
```

## Common Interface

All providers implement the `DataProvider` interface:

```python
class DataProvider(ABC):
    def get_data(self) -> str:
        """Returns complete CSV output as string (including header row)."""
        pass
    
    def get_column_names(self) -> List[str]:
        """Returns list of column names for this provider."""
        pass
    
    def get_source_info(self) -> Dict[str, Any]:
        """Returns metadata about data source."""
        pass
```

## Configuration

Providers can be configured via environment variables or constructor parameters:

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMPTS_DIRECTORY` | Base path to prompts directory | `"resources/prompts"` |
| `HEADERS_CSV_FILE` | Path to table headers CSV | `"database/embeddings/table_headers/table_headers.csv"` |
| `CSV_DELIMITER` | CSV field delimiter | `";"` |
| `CSV_ENCODING` | Output encoding | `"utf-8"` |
| `SKIP_INVALID_RECORDS` | Continue on record errors | `"true"` |

## Testing

Run the test script to validate all providers:

```bash
python database/providers/test_providers.py
```

This will:
1. Test each provider
2. Display source information and sample output
3. Save CSV output files for inspection

## CSV Format Specifications

All providers follow these CSV formatting rules:

- **Delimiter**: Semicolon (;)
- **Header Row**: Required - first row contains column names
- **Encoding**: UTF-8
- **Quoting**: Double quotes for fields containing delimiters, quotes, or newlines
- **Escape Character**: Double quote ("") to escape quotes within quoted fields
- **Empty Fields**: Empty string for null/missing optional values

## Error Handling

Providers handle errors gracefully:

- **Missing source file/directory**: Log error, return empty result or raise exception
- **Invalid YAML syntax**: Log warning with file name, skip file, continue processing
- **Missing required fields**: Log warning with file name and missing fields, skip record
- **Invalid JSON in fields**: Log error with file name, skip record
- **File encoding issues**: Attempt UTF-8, log error if fails, skip file

## Architecture Benefits

The provider-based architecture offers:

1. **Modularity**: Each provider is independent and can be used separately
2. **Testability**: Providers can be tested without database setup
3. **Reusability**: Same providers can be used for different purposes
4. **Maintainability**: Clear separation makes code easier to understand and modify
5. **Extensibility**: Easy to add new providers following the same pattern

## Future Extensibility

The architecture supports future providers such as:

- User Prompts Provider (from database)
- Synonym Provider (for semantic search)
- Metadata Provider (about prompt categories)
- Analytics Provider (usage statistics)
