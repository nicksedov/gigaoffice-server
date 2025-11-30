# Quick Start Guide - Embedding Processor

This guide will help you quickly set up and run the Embedding Processor to populate your database with vector embeddings.

## Prerequisites

1. **PostgreSQL with pgvector extension**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **Python dependencies** (already in requirements.txt)
   - psycopg2
   - sentence-transformers
   - pymystem3
   - numpy
   - loguru
   - pyyaml

3. **Source data files** (should already be in repository)
   - `database/embeddings/table_headers/table_headers.csv`
   - `resources/prompts/classifier/example_*.yaml`
   - `resources/prompts/category/*/example_*.yaml`

## Step 1: Configure Environment

Create a `.env` file or set environment variables:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gigaoffice
DB_USER=gigaoffice
DB_PASSWORD=your_password_here

# Optional: Schema Configuration
DB_SCHEMA=public
DB_EXTENSIONS_SCHEMA=public

# Optional: Model Configuration
MODEL_CACHE_PATH=./models
EMBEDDING_MODEL_NAME=ai-forever/ru-en-RoSBERTa
```

## Step 2: Run the Processor

### Option A: Process All Tables (Recommended)

```bash
python database/embeddings/run_all_processors.py
```

This will:
1. Process TableHeadersProvider → `header_embeddings` (~2,213 records)
2. Process ClassificationPromptsProvider → `classification_prompt_embeddings` (~11 records)
3. Process CategorizedPromptsProvider → `categorized_prompt_embeddings` (~73 records)

### Option B: Process Individual Table

```python
from database.providers import TableHeadersProvider
from database.embeddings.processor import EmbeddingProcessor

db_config = {
    'host': 'localhost',
    'port': 5432,
    'name': 'gigaoffice',
    'user': 'gigaoffice',
    'password': 'your_password'
}

provider = TableHeadersProvider()
processor = EmbeddingProcessor(
    provider=provider,
    target_table='header_embeddings',
    model_name='ai-forever/ru-en-RoSBERTa',
    db_config=db_config
)

stats = processor.process()
print(f"Inserted {stats['successfully_inserted']} records in {stats['processing_time']:.2f}s")
```

## Step 3: Verify Results

Check the created tables in PostgreSQL:

```sql
-- Check header_embeddings
SELECT COUNT(*) FROM header_embeddings;
SELECT text, lemmatized_text FROM header_embeddings LIMIT 5;

-- Check classification_prompt_embeddings
SELECT COUNT(*) FROM classification_prompt_embeddings;
SELECT text FROM classification_prompt_embeddings LIMIT 5;

-- Check categorized_prompt_embeddings
SELECT COUNT(*) FROM categorized_prompt_embeddings;
SELECT category, text FROM categorized_prompt_embeddings LIMIT 5;
```

## Step 4: Test Vector Search

Try a similarity search:

```sql
-- Find similar headers (requires an embedding to compare against)
SELECT text, lemmatized_text
FROM header_embeddings
ORDER BY embedding <-> (SELECT embedding FROM header_embeddings WHERE text = 'date' LIMIT 1)
LIMIT 5;
```

## Expected Output

When you run the processor, you should see output like:

```
================================================================================
EMBEDDING PROCESSOR ORCHESTRATION
================================================================================
Database: localhost:5432/gigaoffice
Model: ai-forever/ru-en-RoSBERTa
================================================================================

[1/3] Processing Table Headers...
================================================================================
Starting processing for TableHeadersProvider -> header_embeddings
================================================================================

2025-11-30 20:00:00.000 | INFO | Loading embedding model: ai-forever/ru-en-RoSBERTa
2025-11-30 20:00:05.000 | INFO | Model loaded successfully (dimension: 768)
2025-11-30 20:00:05.100 | INFO | Connecting to database: localhost:5432/gigaoffice
2025-11-30 20:00:05.200 | INFO | Database connection established
2025-11-30 20:00:05.300 | INFO | Fetching data from provider...
2025-11-30 20:00:05.400 | INFO | Parsed CSV: 1 columns, 2213 records
2025-11-30 20:00:05.500 | INFO | Table header_embeddings does not exist or has invalid schema
2025-11-30 20:00:05.600 | INFO | Creating table header_embeddings...
2025-11-30 20:00:05.700 | INFO | Table header_embeddings created successfully
2025-11-30 20:00:05.800 | INFO | Processing records...
2025-11-30 20:00:10.000 | INFO | Processed 10 new records...
2025-11-30 20:00:15.000 | INFO | Processed 20 new records...
...
2025-11-30 20:00:50.000 | INFO | Committed 2213 new records to database
2025-11-30 20:00:50.100 | INFO | Creating indexes for header_embeddings...
2025-11-30 20:00:55.000 | INFO | Indexes created successfully for header_embeddings

============================================================
Processing Statistics for header_embeddings
============================================================
Provider: TableHeadersProvider
Target Table: header_embeddings
Model: ai-forever/ru-en-RoSBERTa (dimension: 768)
------------------------------------------------------------
Total records from CSV: 2213
Existing records in DB: 0
New records processed: 2213
Successfully inserted: 2213
Failed insertions: 0
Processing time: 45.23 seconds
============================================================

✅ Successfully processed header_embeddings

[2/3] Processing Classification Prompts...
...
```

## Troubleshooting

### Issue: "pymystem3 not available"
**Solution**: Install pymystem3
```bash
pip install pymystem3
```
Note: The processor will still work without it, but Russian text won't be lemmatized.

### Issue: "Model download fails"
**Solution**: 
1. Ensure you have internet connection
2. Set `MODEL_CACHE_PATH` to a directory with write permissions
3. Ensure enough disk space (~1GB for the model)

### Issue: "Database connection failed"
**Solution**:
1. Verify PostgreSQL is running
2. Check database credentials
3. Ensure the database exists
4. Verify network connectivity to database server

### Issue: "pgvector extension not found"
**Solution**: Install pgvector in PostgreSQL
```sql
CREATE EXTENSION vector;
```

### Issue: "Table already exists with wrong schema"
**Solution**: The processor automatically drops and recreates tables with invalid schemas. If you want to force recreation:
```sql
DROP TABLE IF EXISTS header_embeddings;
DROP TABLE IF EXISTS classification_prompt_embeddings;
DROP TABLE IF EXISTS categorized_prompt_embeddings;
```
Then re-run the processor.

## Incremental Updates

To add new data:

1. Add new rows to `table_headers.csv` or new `example_*.yaml` files
2. Re-run the processor
3. Only new records will be processed (existing ones are skipped)

Example:
```bash
# After adding new YAML files
python database/embeddings/run_all_processors.py
```

The processor will:
- Detect existing records via lemmatized_text comparison
- Skip duplicate records
- Process only new records
- Update indexes if needed

## Performance Tips

1. **First Run**: Will take 3-5 minutes (model download + embedding generation)
2. **Subsequent Runs**: Only processes new records (<30 seconds typically)
3. **Model Caching**: Set `MODEL_CACHE_PATH` to avoid re-downloading the model
4. **Batch Processing**: The processor handles batching automatically

## Next Steps

After successful processing:

1. **Test Vector Search**: Use the vector search services in `app/services/database/vector_search/`
2. **Monitor Performance**: Check query execution plans to verify index usage
3. **Regular Updates**: Re-run processor when source data changes
4. **Backup**: Consider backing up the embedding tables (though they can be recreated from source data)

## Need Help?

- Check logs for detailed error messages
- Review `database/embeddings/processor/README.md` for comprehensive documentation
- See `database/embeddings/IMPLEMENTATION_SUMMARY.md` for implementation details
- Run tests: `python database/embeddings/test_processor_components.py`

## Summary

The Embedding Processor provides an automated, maintainable way to:
- ✅ Generate vector embeddings from text data
- ✅ Populate PostgreSQL tables with pgvector support
- ✅ Enable semantic similarity search
- ✅ Handle incremental updates efficiently
- ✅ Maintain data consistency and quality

Happy processing! 🚀
