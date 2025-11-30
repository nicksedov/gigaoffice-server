import os
import psycopg2
import yaml
import json
import re
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger

# Read environment variables with default values
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "gigaoffice")
DB_USER = os.getenv("DB_USER", "gigaoffice")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "")
DB_EXTENSIONS_SCHEMA = os.getenv("DB_EXTENSIONS_SCHEMA", "")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
MODEL_CACHE_PATH = os.getenv("MODEL_CACHE_PATH", "")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "ai-forever/ru-en-RoSBERTa")
PROMPTS_DIRECTORY = os.getenv("PROMPTS_DIRECTORY", "resources/prompts")

TARGET_TABLE = "prompt_examples"

try:
    from pymystem3 import Mystem
    MYSTEM_AVAILABLE = True
except ImportError:
    MYSTEM_AVAILABLE = False
    logger.warning("pymystem3 not available, Russian lemmatization will be disabled")


class LemmatizationError(Exception):
    pass


class MystemLemmatizer:
    def __init__(self):
        if not MYSTEM_AVAILABLE:
            raise LemmatizationError("pymystem3 not available")
        self.mystem = Mystem()

    def lemmatize(self, text: str) -> str:
        try:
            lemmatized = self.mystem.lemmatize(text)
            result = ''.join(lemmatized).strip()
            return result
        except Exception as e:
            logger.error(f"Error during Russian lemmatization: {e}")
            raise LemmatizationError(f"Failed to lemmatize Russian text: {e}")


class LemmatizationService:
    def __init__(self, config: Optional[dict] = None):
        self._lemmatizer = None
        try:
            if MYSTEM_AVAILABLE:
                self._lemmatizer = MystemLemmatizer()
        except Exception as e:
            logger.warning(f"Failed to initialize Russian lemmatizer: {e}")

    def lemmatize(self, text: str) -> str:
        if not text.strip():
            return text
        try:
            return self._lemmatizer.lemmatize(text)
        except Exception as e:
            logger.error(f"Error during lemmatization: {e}")
            return text


lemmatization_service = LemmatizationService()


class PromptExample:
    """Data class for storing parsed prompt example"""
    def __init__(
        self,
        category: str,
        prompt_text: str,
        request_json: Optional[Dict[str, Any]],
        response_json: Dict[str, Any],
        source_file: str
    ):
        self.category = category
        self.prompt_text = prompt_text
        self.request_json = request_json
        self.response_json = response_json
        self.source_file = source_file
        self.language = self._detect_language(prompt_text)
        self.lemmatized_prompt = self._lemmatize_text(prompt_text)

    def _detect_language(self, text: str) -> str:
        """Detect if text contains Russian characters"""
        return 'ru' if re.search(r'[а-яё]', text.lower()) else 'en'

    def _lemmatize_text(self, text: str) -> str:
        """Lemmatize text if Russian, otherwise return original"""
        if self.language == 'ru':
            return lemmatization_service.lemmatize(text)
        return text


def discover_yaml_files(prompts_dir: str) -> List[Tuple[str, Path]]:
    """
    Discover all YAML example files in the prompts directory structure.
    
    Returns:
        List of tuples (category_name, file_path)
    """
    yaml_files = []
    prompts_path = Path(prompts_dir)
    
    if not prompts_path.exists():
        logger.error(f"Prompts directory not found: {prompts_dir}")
        return yaml_files
    
    # Iterate through subdirectories (categories)
    for category_dir in prompts_path.iterdir():
        if not category_dir.is_dir():
            continue
        
        category_name = category_dir.name
        
        # Skip if directory name doesn't match expected categories
        valid_categories = [
            'classifier', 'data-chart', 'data-histogram',
            'spreadsheet-analysis', 'spreadsheet-formatting',
            'spreadsheet-generation', 'spreadsheet-search',
            'spreadsheet-transformation', 'spreadsheet-assistance'
        ]
        
        if category_name not in valid_categories:
            logger.warning(f"Skipping unexpected directory: {category_name}")
            continue
        
        # Find all YAML files (exclude system_prompt.txt)
        for yaml_file in category_dir.glob("example_*.yaml"):
            yaml_files.append((category_name, yaml_file))
        
        for yaml_file in category_dir.glob("example_*.yml"):
            yaml_files.append((category_name, yaml_file))
    
    return yaml_files


def parse_yaml_example(category: str, file_path: Path) -> Optional[PromptExample]:
    """
    Parse a single YAML example file.
    
    Args:
        category: Category name
        file_path: Path to YAML file
        
    Returns:
        PromptExample object or None if parsing fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            logger.warning(f"Empty YAML file: {file_path}")
            return None
        
        # Extract required fields
        task = data.get('task')
        if not task:
            logger.warning(f"Missing 'task' field in {file_path}")
            return None
        
        response_table = data.get('response_table')
        if not response_table:
            logger.warning(f"Missing 'response_table' field in {file_path}")
            return None
        
        # Parse JSON strings
        request_json = None
        request_table = data.get('request_table')
        if request_table:
            try:
                request_json = json.loads(request_table)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in 'request_table' of {file_path}: {e}")
        
        try:
            response_json = json.loads(response_table)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in 'response_table' of {file_path}: {e}")
            return None
        
        return PromptExample(
            category=category,
            prompt_text=task,
            request_json=request_json,
            response_json=response_json,
            source_file=file_path.name
        )
        
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
        return None


def parse_all_examples(prompts_dir: str) -> List[PromptExample]:
    """
    Discover and parse all YAML example files.
    
    Returns:
        List of PromptExample objects
    """
    yaml_files = discover_yaml_files(prompts_dir)
    logger.info(f"Found {len(yaml_files)} YAML example files")
    
    examples = []
    errors = 0
    
    for category, file_path in yaml_files:
        example = parse_yaml_example(category, file_path)
        if example:
            examples.append(example)
        else:
            errors += 1
    
    logger.info(f"Successfully parsed {len(examples)} examples")
    if errors > 0:
        logger.warning(f"Failed to parse {errors} files")
    
    return examples


def main():
    logger.info("Starting prompt examples knowledge base generation")
    
    # Parse all examples
    examples = parse_all_examples(PROMPTS_DIRECTORY)
    if not examples:
        logger.error("No examples found or parsed. Exiting.")
        return
    
    # Generate embeddings if vector support is enabled
    MODEL_DIMENSION = 0
    embeddings = np.zeros(len(examples))
    
    model_path = f"{MODEL_CACHE_PATH}/{EMBEDDING_MODEL_NAME}" if MODEL_CACHE_PATH else EMBEDDING_MODEL_NAME
    logger.info(f"Initializing embedding model: {model_path}")
    
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_path)
        MODEL_DIMENSION = model.get_sentence_embedding_dimension()
        logger.info(f"Model dimension: {MODEL_DIMENSION}")
        
        # Generate embeddings from lemmatized prompts
        lemmatized_prompts = [ex.lemmatized_prompt for ex in examples]
        embeddings = model.encode(lemmatized_prompts, normalize_embeddings=True)
        logger.info(f"Generated {len(embeddings)} embeddings")
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return
    
    # Connect to database
    logger.info(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return
    
    with conn, conn.cursor() as cur:
        # Set search path if schema is configured
        if DB_SCHEMA:
            cur.execute(f"SET search_path TO {DB_SCHEMA};")
            logger.info(f"Set search_path to {DB_SCHEMA}")
        
        # Drop existing table
        logger.info(f"Dropping table {TARGET_TABLE} if exists...")
        cur.execute(f"DROP TABLE IF EXISTS {TARGET_TABLE};")
        
        # Create vector extension if needed
        logger.info("Creating vector extension...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create table
        logger.info(f"Creating table {TARGET_TABLE}...")
        vector_prefix = ""
        if DB_EXTENSIONS_SCHEMA:
            vector_prefix = f"{DB_EXTENSIONS_SCHEMA}."
        
        embedding_type = f"{vector_prefix}VECTOR({MODEL_DIMENSION})"
        
        cur.execute(f"""
            CREATE TABLE {TARGET_TABLE} (
                id SERIAL PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                prompt_text TEXT NOT NULL,
                lemmatized_prompt TEXT,
                embedding {embedding_type},
                request_json JSONB,
                response_json JSONB NOT NULL,
                language VARCHAR(2),
                source_file VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        logger.info(f"Table {TARGET_TABLE} created successfully")
        
        # Insert data
        logger.info(f"Inserting {len(examples)} examples into {TARGET_TABLE}...")
        inserted_count = 0
        
        for example, emb in zip(examples, embeddings):
            try:
                cur.execute(
                    f"""
                    INSERT INTO {TARGET_TABLE} 
                    (category, prompt_text, lemmatized_prompt, embedding, request_json, response_json, language, source_file)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        example.category,
                        example.prompt_text,
                        example.lemmatized_prompt,
                        emb.tolist(),
                        json.dumps(example.request_json) if example.request_json else None,
                        json.dumps(example.response_json),
                        example.language,
                        example.source_file
                    )
                )
                inserted_count += 1
            except Exception as e:
                logger.error(f"Failed to insert example from {example.source_file}: {e}")
        
        logger.info(f"Inserted {inserted_count} examples")
        
        # Create indexes
        logger.info(f"Creating indexes for {TARGET_TABLE}...")
        cur.execute(f"CREATE INDEX {TARGET_TABLE}_idx_category ON {TARGET_TABLE} (category);")
        cur.execute(f"CREATE INDEX {TARGET_TABLE}_idx_lemmatized ON {TARGET_TABLE} (lemmatized_prompt);")
        
        logger.info("Creating vector indexes...")
        cur.execute(f"""
            CREATE INDEX {TARGET_TABLE}_idx_embedding_l2 
            ON {TARGET_TABLE} USING ivfflat (embedding {vector_prefix}vector_l2_ops);
        """)
        cur.execute(f"""
            CREATE INDEX {TARGET_TABLE}_idx_embedding_cos 
            ON {TARGET_TABLE} USING ivfflat (embedding {vector_prefix}vector_cosine_ops);
        """)
        
        logger.info("Indexes created successfully")
    
    logger.info("=" * 60)
    logger.info("Knowledge base generation completed successfully!")
    logger.info(f"Total examples processed: {len(examples)}")
    logger.info(f"Total examples inserted: {inserted_count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
