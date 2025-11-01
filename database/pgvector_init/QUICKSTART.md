# Quick Start Guide: Prompt Examples Knowledge Base

## What This Does

Creates a PostgreSQL table containing all prompt examples from YAML files in `resources/prompts/`, enabling:
- Fast retrieval of few-shot examples by category
- Text-based search through prompts
- Semantic similarity search (with vector support)

## Prerequisites

```bash
# Install required Python packages
pip install psycopg2 pyyaml loguru numpy

# Optional: For vector embeddings
pip install sentence-transformers

# Optional: For Russian lemmatization
pip install pymystem3
```

## Quick Start (Basic Mode)

### 1. Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="gigaoffice"
$env:DB_USER="gigaoffice"
$env:DB_PASSWORD="your_password"
```

**Linux/Mac (Bash):**
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=gigaoffice
export DB_USER=gigaoffice
export DB_PASSWORD=your_password
```

### 2. Run the Script

```bash
cd database/pgvector_init
python generate_prompt_examples.py
```

### 3. Verify Success

Look for this in the output:
```
============================================================
INFO: Knowledge base generation completed successfully!
INFO: Total examples processed: XX
INFO: Total examples inserted: XX
============================================================
```

## Quick Start (With Vector Support)

### 1. Enable Vector Support

**Windows (PowerShell):**
```powershell
$env:DB_VECTOR_SUPPORT="true"
$env:EMBEDDING_MODEL_NAME="ai-forever/ru-en-RoSBERTa"
```

**Linux/Mac (Bash):**
```bash
export DB_VECTOR_SUPPORT=true
export EMBEDDING_MODEL_NAME=ai-forever/ru-en-RoSBERTa
```

### 2. Run the Script

```bash
python generate_prompt_examples.py
```

First run will download the embedding model (~500MB).

## Testing

### Test Without Database

```bash
python test_prompt_examples.py
```

This validates:
- YAML files can be found
- Files parse correctly
- JSON data is valid

### Test With Database

```bash
python example_queries.py
```

This shows:
- Statistics about loaded examples
- Example queries by category
- Text search examples
- Individual example retrieval

## Quick Query Examples

### Using Python

```python
import psycopg2

conn = psycopg2.connect(
    dbname="gigaoffice",
    user="gigaoffice",
    password="your_password",
    host="localhost"
)

with conn.cursor() as cur:
    # Get examples from a category
    cur.execute("""
        SELECT prompt_text, response_json 
        FROM prompt_examples 
        WHERE category = 'spreadsheet-generation'
        LIMIT 5
    """)
    
    for row in cur.fetchall():
        print(row[0])  # Prompt text
```

### Using SQL

```sql
-- Count examples by category
SELECT category, COUNT(*) 
FROM prompt_examples 
GROUP BY category;

-- Search for specific text
SELECT prompt_text 
FROM prompt_examples 
WHERE lemmatized_prompt ILIKE '%таблица%';

-- Get all data for one example
SELECT * 
FROM prompt_examples 
WHERE id = 1;
```

## Common Issues

### "Prompts directory not found"
**Fix**: Set `PROMPTS_DIRECTORY` environment variable to correct path
```bash
export PROMPTS_DIRECTORY=/path/to/resources/prompts
```

### "Failed to connect to database"
**Fix**: Check database is running and credentials are correct
```bash
psql -h localhost -U gigaoffice -d gigaoffice
```

### "pymystem3 not available"
**Not critical**: Script continues without Russian lemmatization
**Fix (optional)**: `pip install pymystem3`

### "Failed to load embedding model"
**Not critical**: Script continues without vector embeddings
**Fix (optional)**: `pip install sentence-transformers`

## What Gets Created

### Table: `prompt_examples`
- Stores all parsed YAML examples
- Indexed for fast queries
- Contains JSON request/response data

### Example Data
```json
{
  "id": 1,
  "category": "spreadsheet-generation",
  "prompt_text": "Создай таблицу с данными о сотрудниках...",
  "request_json": null,
  "response_json": { "metadata": {...}, "data": {...} },
  "language": "ru",
  "source_file": "example_01.yaml"
}
```

## Next Steps

1. **Integrate into application**: Use `example_queries.py` as reference
2. **Build prompt service**: Retrieve relevant examples based on user queries
3. **Implement caching**: Cache frequently accessed examples
4. **Add monitoring**: Track which examples are most useful

## Need More Help?

- **Full documentation**: See `README_PROMPT_EXAMPLES.md`
- **Implementation details**: See `IMPLEMENTATION_SUMMARY.md`
- **Query examples**: See `example_queries.py`
- **Test suite**: See `test_prompt_examples.py`

## Summary

```
Install Dependencies → Set Environment Variables → Run Script → Verify → Query
       ↓                        ↓                       ↓           ↓        ↓
   pip install            DB_HOST, DB_NAME         python gen..  Test it  Use it
```

**Estimated time**: 5-10 minutes (first run with model download: 15-20 minutes)
