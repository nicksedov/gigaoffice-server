# Embedding Processor

Universal embedding processor for creating and populating database tables with vector embeddings from various data providers.

## Overview

The Embedding Processor is a flexible, provider-based system that:
- Processes data from any `DataProvider` implementation
- Generates vector embeddings using SentenceTransformer models
- Applies Russian text lemmatization for improved search accuracy
- Creates and manages PostgreSQL tables with pgvector extension
- Performs incremental updates with duplicate detection
- Creates optimized indexes for vector similarity search

## Architecture

```
database/embeddings/
├── processor/
│   ├── __init__.py                  # Module exports
│   ├── embedding_processor.py       # Main processor class
│   ├── lemmatization_service.py     # Text lemmatization
│   └── schema_validator.py          # Database schema management
└── run_all_processors.py            # Orchestration script
```

## Components

### EmbeddingProcessor

Main class that orchestrates the complete workflow:
- Model loading and management
- CSV data parsing
- Schema validation and table creation
- Text processing with lemmatization
- Embedding generation
- Database operations
- Statistics reporting

### LemmatizationService

Handles text normalization:
- Automatic language detection (Russian/English)
- Russian lemmatization using pymystem3
- Fallback handling for errors

### SchemaValidator

Manages database schema:
- Table existence verification
- Column structure validation
- Table creation with proper types
- Index management (B-tree and IVFFlat)

## Usage

### Quick Start

Run all three processors sequentially:

```bash
python database/embeddings/run_all_processors.py
```

This will process:
1. `TableHeadersProvider` → `header_embeddings`
2. `ClassificationPromptsProvider` → `classification_prompt_embeddings`
3. `CategorizedPromptsProvider` → `categorized_prompt_embeddings`

### Programmatic Usage

Process a single provider:

```python
from database.providers import TableHeadersProvider
from database.embeddings.processor import EmbeddingProcessor

# Configure database
db_config = {
    'host': 'localhost',
    'port': 5432,
    'name': 'gigaoffice',
    'user': 'gigaoffice',
    'password': 'your_password',
    'schema': 'public',  # optional
    'extensions_schema': 'public'  # optional
}

# Initialize provider
provider = TableHeadersProvider()

# Create processor
processor = EmbeddingProcessor(
    provider=provider,
    target_table='header_embeddings',
    model_name='ai-forever/ru-en-RoSBERTa',
    db_config=db_config
)

# Execute processing
stats = processor.process()

# Check results
print(f"Inserted {stats['successfully_inserted']} records")
print(f"Processing time: {stats['processing_time']:.2f}s")
```

## Configuration

All configuration is done via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database server hostname | `localhost` |
| `DB_PORT` | Database server port | `5432` |
| `DB_NAME` | Database name | `gigaoffice` |
| `DB_USER` | Database username | `gigaoffice` |
| `DB_PASSWORD` | Database password | `` (empty) |
| `DB_SCHEMA` | Application schema | `` (public) |
| `DB_EXTENSIONS_SCHEMA` | Extensions schema | `` (public) |
| `MODEL_CACHE_PATH` | Local model cache directory | `` (download) |
| `EMBEDDING_MODEL_NAME` | SentenceTransformer model | `ai-forever/ru-en-RoSBERTa` |
| `PROMPTS_DIRECTORY` | Prompts base directory | `resources/prompts/category` |

### Example .env Configuration

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gigaoffice
DB_USER=gigaoffice
DB_PASSWORD=mysecretpassword
DB_SCHEMA=public
DB_EXTENSIONS_SCHEMA=public
MODEL_CACHE_PATH=/path/to/model/cache
EMBEDDING_MODEL_NAME=ai-forever/ru-en-RoSBERTa
```

## Table Schema

Each target table follows this structure:

```sql
CREATE TABLE {table_name} (
    id SERIAL PRIMARY KEY,
    
    -- CSV columns (dynamic based on provider)
    text TEXT NOT NULL,           -- Main content
    category VARCHAR(100),         -- Optional category
    request_json JSONB,            -- Optional request data
    response_json JSONB,           -- Optional response data
    
    -- Computed columns
    lemmatized_text TEXT,          -- Lemmatized version of text
    embedding VECTOR(768),         -- Vector embedding
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

Created automatically for performance:

- B-tree index on `lemmatized_text` for deduplication
- IVFFlat index on `embedding` with L2 distance
- IVFFlat index on `embedding` with cosine distance

## Processing Flow

1. **Initialization**
   - Load SentenceTransformer model
   - Connect to database
   - Initialize schema validator

2. **Data Acquisition**
   - Fetch CSV data from provider
   - Parse headers and records

3. **Schema Management**
   - Check if table exists
   - Validate schema structure
   - Drop/recreate if invalid
   - Load existing lemmatized texts

4. **Record Processing**
   - For each CSV record:
     - Extract text field
     - Apply lemmatization
     - Check for duplicates
     - Generate embedding (if new)
     - Insert into database

5. **Finalization**
   - Commit transaction
   - Create indexes
   - Report statistics

## Incremental Processing

The processor intelligently handles updates:

- **First Run**: Creates table and processes all records
- **Subsequent Runs**: Only processes new records
- **Duplicate Detection**: Uses lemmatized_text for comparison
- **Performance**: Skips embedding generation for duplicates

## Statistics Reporting

Each processing run reports detailed statistics:

```
========================================
Processing Statistics for header_embeddings
========================================
Provider: TableHeadersProvider
Target Table: header_embeddings
Model: ai-forever/ru-en-RoSBERTa (dimension: 768)
----------------------------------------
Total records from CSV: 2213
Existing records in DB: 2100
New records processed: 113
Successfully inserted: 113
Failed insertions: 0
Processing time: 45.2 seconds
========================================
```

## Error Handling

The processor handles errors gracefully:

- **Model Loading**: Fatal error, stops processing
- **Database Connection**: Fatal error, stops processing
- **CSV Parsing**: Logs error, skips malformed records
- **Lemmatization**: Falls back to original text
- **Embedding Generation**: Logs error, skips record
- **Database Insert**: Logs error, continues with next record

## Performance

Expected performance for reference data volumes:

| Provider | Records | Initial Load | Incremental |
|----------|---------|--------------|-------------|
| TableHeaders | ~2,200 | 30-60s | <5s |
| ClassificationPrompts | ~11 | <5s | <2s |
| CategorizedPrompts | ~73 | 10-20s | <5s |

**Total**: ~3-5 minutes for initial load, <30 seconds for incremental updates.

## Requirements

### Python Dependencies

- psycopg2: PostgreSQL adapter
- sentence-transformers: Embedding models
- pymystem3: Russian lemmatization
- numpy: Numerical operations
- loguru: Logging

### Database Requirements

- PostgreSQL 12+
- pgvector extension installed
- Sufficient permissions for table creation

### System Requirements

- Python 3.8+
- 2GB+ RAM (for model loading)
- 1GB+ disk space (for model cache)

## Troubleshooting

### "pymystem3 not available"

Install pymystem3:
```bash
pip install pymystem3
```

### "pgvector extension not found"

Install pgvector extension in PostgreSQL:
```sql
CREATE EXTENSION vector;
```

### "Model download fails"

Set `MODEL_CACHE_PATH` to a directory with sufficient space and write permissions.

### "Table already exists with wrong schema"

The processor automatically drops and recreates tables with invalid schemas. To force recreation:
1. Manually drop the table
2. Re-run the processor

## Extending

To add a new embedding table:

1. Create a new `DataProvider` implementation
2. Define the CSV structure (must include 'text' column)
3. Add processing call in orchestration script:

```python
provider = MyNewProvider()
stats = process_provider(provider, "my_embeddings", model_name, db_config)
```

## Testing

Test the processor with a single provider:

```python
from database.providers import TableHeadersProvider
from database.embeddings.processor import EmbeddingProcessor

provider = TableHeadersProvider()
processor = EmbeddingProcessor(
    provider=provider,
    target_table='test_embeddings',
    model_name='ai-forever/ru-en-RoSBERTa',
    db_config=your_db_config
)

stats = processor.process()
assert stats['successfully_inserted'] > 0
```

## Best Practices

1. **Initial Setup**: Run once with empty database to populate all tables
2. **Updates**: Re-run after adding new source data (YAML files, CSV files)
3. **Monitoring**: Check logs for warnings about failed records
4. **Backups**: Tables can be recreated from source data at any time
5. **Performance**: Consider running during off-peak hours for large datasets

## License

Part of the GigaOffice server project.
