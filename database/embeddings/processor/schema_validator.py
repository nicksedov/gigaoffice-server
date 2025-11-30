"""
Schema Validator for Embedding Processor.

Handles database schema validation, table creation, and index management
for embedding tables.
"""

from typing import List, Set, Optional
import psycopg2
from loguru import logger


class SchemaValidator:
    """
    Validates and manages database schema for embedding tables.
    
    Responsibilities:
    - Check table existence
    - Validate column structure
    - Create tables with proper schema
    - Manage indexes for performance
    """
    
    def __init__(
        self,
        conn: psycopg2.extensions.connection,
        schema: Optional[str] = None,
        extensions_schema: Optional[str] = None
    ):
        """
        Initialize the schema validator.
        
        Args:
            conn: Database connection
            schema: Application schema name (None for public schema)
            extensions_schema: Schema where pgvector extension is installed (None for public)
        """
        self.conn = conn
        self.schema = schema
        self.extensions_schema = extensions_schema
        
        # Set search path if schema is configured
        if self.schema:
            with self.conn.cursor() as cur:
                cur.execute(f"SET search_path TO {self.schema};")
                logger.info(f"Set search_path to {self.schema}")
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists in the database.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists, False otherwise
        """
        with self.conn.cursor() as cur:
            if self.schema:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    );
                """, (self.schema, table_name))
            else:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table_name,))
            
            return cur.fetchone()[0]
    
    def get_table_columns(self, table_name: str) -> Set[str]:
        """
        Get set of column names for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Set of column names
        """
        with self.conn.cursor() as cur:
            if self.schema:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = %s;
                """, (self.schema, table_name))
            else:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s;
                """, (table_name,))
            
            return {row[0] for row in cur.fetchall()}
    
    def validate_schema(
        self,
        table_name: str,
        csv_columns: List[str]
    ) -> bool:
        """
        Validate that table has correct schema.
        
        Args:
            table_name: Name of the table
            csv_columns: List of column names from CSV
            
        Returns:
            True if schema is valid, False otherwise
        """
        if not self.table_exists(table_name):
            return False
        
        existing_columns = self.get_table_columns(table_name)
        
        # Required columns: id, all CSV columns, lemmatized_text, embedding, created_at
        required_columns = {'id', 'lemmatized_text', 'embedding', 'created_at'}
        required_columns.update(csv_columns)
        
        # Check if all required columns exist
        missing_columns = required_columns - existing_columns
        if missing_columns:
            logger.warning(f"Table {table_name} is missing columns: {missing_columns}")
            return False
        
        logger.info(f"Table {table_name} has valid schema")
        return True
    
    def drop_table(self, table_name: str):
        """
        Drop table if it exists.
        
        Args:
            table_name: Name of the table to drop
        """
        logger.info(f"Dropping table {table_name} if exists...")
        with self.conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table_name};")
        self.conn.commit()
        logger.info(f"Table {table_name} dropped")
    
    def create_table(
        self,
        table_name: str,
        csv_columns: List[str],
        embedding_dimension: int
    ):
        """
        Create table with proper schema for embeddings.
        
        Args:
            table_name: Name of the table to create
            csv_columns: List of column names from CSV
            embedding_dimension: Dimension of the embedding vectors
        """
        logger.info(f"Creating table {table_name}...")
        
        # Build column definitions
        column_defs = ["id SERIAL PRIMARY KEY"]
        
        # Add CSV columns with appropriate types
        for col in csv_columns:
            if col == 'text':
                column_defs.append("text TEXT NOT NULL")
            elif col == 'category':
                column_defs.append("category VARCHAR(100) NOT NULL")
            elif col.endswith('_json'):
                column_defs.append(f"{col} JSONB")
            else:
                column_defs.append(f"{col} TEXT")
        
        # Add computed columns
        column_defs.append("lemmatized_text TEXT")
        
        # Add vector column with schema prefix if needed
        vector_prefix = f"{self.extensions_schema}." if self.extensions_schema else ""
        embedding_type = f"{vector_prefix}VECTOR({embedding_dimension})"
        column_defs.append(f"embedding {embedding_type}")
        
        # Add metadata column
        column_defs.append("created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP")
        
        # Create table
        create_sql = f"""
            CREATE TABLE {table_name} (
                {', '.join(column_defs)}
            );
        """
        
        with self.conn.cursor() as cur:
            # Ensure vector extension exists
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(create_sql)
        
        self.conn.commit()
        logger.info(f"Table {table_name} created successfully")
    
    def create_indexes(self, table_name: str):
        """
        Create indexes for performance.
        
        Args:
            table_name: Name of the table
        """
        logger.info(f"Creating indexes for {table_name}...")
        
        vector_prefix = f"{self.extensions_schema}." if self.extensions_schema else ""
        
        with self.conn.cursor() as cur:
            # Index on lemmatized_text for deduplication
            cur.execute(f"CREATE INDEX {table_name}_idx_lemmatized ON {table_name} (lemmatized_text);")
            
            # Vector indexes for similarity search
            cur.execute(f"""
                CREATE INDEX {table_name}_idx_embedding_l2 
                ON {table_name} USING ivfflat (embedding {vector_prefix}vector_l2_ops);
            """)
            
            cur.execute(f"""
                CREATE INDEX {table_name}_idx_embedding_cos 
                ON {table_name} USING ivfflat (embedding {vector_prefix}vector_cosine_ops);
            """)
        
        self.conn.commit()
        logger.info(f"Indexes created successfully for {table_name}")
    
    def get_existing_lemmatized_texts(self, table_name: str) -> Set[str]:
        """
        Get all existing lemmatized_text values from table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Set of lemmatized text values
        """
        if not self.table_exists(table_name):
            return set()
        
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT lemmatized_text FROM {table_name} WHERE lemmatized_text IS NOT NULL;")
            return {row[0] for row in cur.fetchall()}
