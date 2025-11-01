# Prompt Examples Knowledge Base Script

## Overview

This script (`generate_prompt_examples.py`) creates and populates a PostgreSQL database table with few-shot prompt examples extracted from YAML files. The table supports semantic search through vector embeddings and enables efficient retrieval of relevant examples for prompt construction.

## Purpose

The knowledge base table stores categorized prompt examples with:
- Prompt text and lemmatized versions for text search
- Vector embeddings for semantic similarity search
- Request and response JSON structures
- Metadata including category, language, and source file

## Database Table Schema

### Table: `prompt_examples`

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Auto-incrementing identifier |
| category | VARCHAR(100) NOT NULL | Category name (e.g., "spreadsheet-generation") |
| prompt_text | TEXT NOT NULL | Original task description |
| lemmatized_prompt | TEXT | Lemmatized version for improved search |
| embedding | VECTOR(dimension) or INTEGER | Semantic embedding (conditional) |
| request_json | JSONB | Input data structure (nullable) |
| response_json | JSONB NOT NULL | Output data structure |
| language | VARCHAR(2) | Detected language ('ru' or 'en') |
| source_file | VARCHAR(255) | Original YAML filename |
| created_at | TIMESTAMP WITH TIME ZONE | Creation timestamp |

### Indexes

- `prompt_examples_idx_category`: B-tree index on category
- `prompt_examples_idx_lemmatized`: B-tree index on lemmatized_prompt
- `prompt_examples_idx_embedding_l2`: IVFFlat index for L2 distance (if vector support enabled)
- `prompt_examples_idx_embedding_cos`: IVFFlat index for cosine similarity (if vector support enabled)

## Prerequisites

### Python Dependencies

```bash
pip install psycopg2 pyyaml loguru numpy sentence-transformers pymystem3
```

### Required Dependencies:
- `psycopg2`: PostgreSQL database adapter
- `pyyaml`: YAML file parsing
- `loguru`: Enhanced logging
- `numpy`: Array operations

### Optional Dependencies:
- `sentence-transformers`: Embedding generation (required if DB_VECTOR_SUPPORT=true)
- `pymystem3`: Russian lemmatization (recommended for Russian text support)

### Database Requirements

- PostgreSQL database with appropriate permissions
- pgvector extension (if using vector support)
- Sufficient disk space for embeddings

## Environment Variables

Configure the script using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| DB_HOST | localhost | Database server hostname |
| DB_PORT | 5432 | Database server port |
| DB_NAME | gigaoffice | Database name |
| DB_USER | gigaoffice | Database username |
| DB_PASSWORD | (empty) | Database password |
| DB_SCHEMA | (empty) | Application schema name |
| DB_EXTENSIONS_SCHEMA | (empty) | Schema for vector extension |
| DB_VECTOR_SUPPORT | false | Enable/disable vector support |
| MODEL_CACHE_PATH | (empty) | Local path for cached models |
| EMBEDDING_MODEL_NAME | ai-forever/ru-en-RoSBERTa | Model identifier |
| PROMPTS_DIRECTORY | resources/prompts | Path to prompts directory |

## Usage

### Basic Usage (Without Vector Support)

```bash
python database/pgvector_init/generate_prompt_examples.py
```

### With Vector Support

```bash
export DB_VECTOR_SUPPORT=true
export MODEL_CACHE_PATH=/path/to/models
python database/pgvector_init/generate_prompt_examples.py
```

### Using Custom Configuration

```bash
export DB_HOST=your-db-host
export DB_PORT=5432
export DB_NAME=your-database
export DB_USER=your-user
export DB_PASSWORD=your-password
export DB_SCHEMA=your-schema
export DB_VECTOR_SUPPORT=true
export PROMPTS_DIRECTORY=resources/prompts
python database/pgvector_init/generate_prompt_examples.py
```

## Input Data Format

The script reads YAML files from subdirectories within the prompts directory. Each YAML file should follow this structure:

```yaml
task: "Description of the prompt"
request_table: |
  {
    "field1": "value1",
    "field2": "value2"
  }
response_table: |
  {
    "result_field1": "value1",
    "result_field2": "value2"
  }
```

### Fields:
- **task** (required): The prompt text describing the user's request
- **request_table** (optional): JSON string containing input data structure
- **response_table** (required): JSON string containing expected output structure

## Supported Categories

The script processes examples from these categories:
- classifier
- data-chart
- data-histogram
- spreadsheet-analysis
- spreadsheet-formatting
- spreadsheet-generation
- spreadsheet-search
- spreadsheet-transformation

## Script Workflow

1. **Load Configuration**: Read environment variables and set defaults
2. **Initialize Services**: Set up lemmatization and logging
3. **Discover Files**: Scan prompts directory for YAML files
4. **Parse Examples**: Extract and validate data from YAML files
5. **Detect Language**: Identify Russian or English text
6. **Lemmatize Text**: Apply lemmatization for improved search
7. **Generate Embeddings**: Create vector embeddings (if enabled)
8. **Connect to Database**: Establish database connection
9. **Create Table**: Drop existing table and create new schema
10. **Insert Data**: Populate table with parsed examples
11. **Create Indexes**: Build indexes for optimized queries
12. **Log Summary**: Display processing statistics

## Error Handling

### File Parsing Errors
- Invalid YAML files are logged and skipped
- Missing required fields generate warnings
- JSON parsing errors are logged with details
- Processing continues for remaining files

### Database Errors
- Connection failures halt execution with error message
- Insertion errors are logged per-example
- Transaction rollback on critical failures

### Model Loading Errors
- Missing dependencies disable vector features
- Model loading failures log warnings
- Script continues without embeddings if model unavailable

## Output and Logging

The script provides detailed logging:

```
INFO: Starting prompt examples knowledge base generation
INFO: Found 42 YAML example files
INFO: Successfully parsed 42 examples
INFO: Initializing embedding model: ai-forever/ru-en-RoSBERTa
INFO: Model dimension: 768
INFO: Generated 42 embeddings
INFO: Connecting to database: localhost:5432/gigaoffice
INFO: Set search_path to your_schema
INFO: Dropping table prompt_examples if exists...
INFO: Creating vector extension...
INFO: Creating table prompt_examples...
INFO: Table prompt_examples created successfully
INFO: Inserting 42 examples into prompt_examples...
INFO: Inserted 42 examples
INFO: Creating indexes for prompt_examples...
INFO: Creating vector indexes...
INFO: Indexes created successfully
============================================================
INFO: Knowledge base generation completed successfully!
INFO: Total examples processed: 42
INFO: Total examples inserted: 42
INFO: Vector support: enabled
============================================================
```

## Querying the Knowledge Base

### Example Queries

#### Get all examples by category:
```sql
SELECT category, prompt_text, source_file 
FROM prompt_examples 
WHERE category = 'spreadsheet-generation';
```

#### Search by lemmatized text:
```sql
SELECT prompt_text, response_json 
FROM prompt_examples 
WHERE lemmatized_prompt ILIKE '%создать таблица%';
```

#### Vector similarity search (requires vector support):
```sql
SELECT prompt_text, category, 
       embedding <=> '[0.1, 0.2, ...]'::vector AS distance
FROM prompt_examples 
ORDER BY distance 
LIMIT 5;
```

#### Get examples with request data:
```sql
SELECT category, prompt_text, request_json, response_json 
FROM prompt_examples 
WHERE request_json IS NOT NULL;
```

## Maintenance

### Updating Examples

To update the knowledge base:
1. Modify or add YAML files in the prompts directory
2. Run the script again (this will drop and recreate the table)
3. Verify the update with a query

**Warning**: Running the script drops the existing `prompt_examples` table. Back up any custom data before running.

### Incremental Updates

For production use, consider modifying the script to support incremental updates:
- Add a version field to track changes
- Implement upsert logic instead of drop-and-recreate
- Track modification timestamps

## Performance Considerations

- **Embedding Generation**: Can take several minutes for large datasets
- **Vector Index Creation**: Requires sufficient database memory
- **Batch Inserts**: Current implementation inserts one-by-one; batch inserts could improve performance

## Troubleshooting

### Issue: "pymystem3 not available"
**Solution**: Install pymystem3 or continue without Russian lemmatization

### Issue: "Failed to load embedding model"
**Solution**: Ensure sentence-transformers is installed and model is accessible

### Issue: "Prompts directory not found"
**Solution**: Verify PROMPTS_DIRECTORY path or set correct path via environment variable

### Issue: "Failed to connect to database"
**Solution**: Check database credentials and network connectivity

### Issue: "vector extension not found"
**Solution**: Install pgvector extension or disable vector support

## Security Considerations

- Store database credentials in environment variables, not in code
- Use strong passwords for database accounts
- Restrict database user permissions to necessary operations only
- Validate and sanitize all input data before database insertion

## Future Enhancements

- Support for incremental updates
- Version tracking for examples
- Usage statistics and analytics
- Multi-language support beyond Russian and English
- CLI arguments for runtime configuration
- Progress bars for long-running operations
- Automated testing and validation

## License

This script is part of the GigaOffice project. Refer to the project's main LICENSE file for details.
