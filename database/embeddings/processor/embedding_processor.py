"""
Universal Embedding Processor.

Processes data from providers and creates/populates database tables
with vector embeddings for similarity search.
"""

import csv
import json
import time
from io import StringIO
from typing import Dict, List, Any, Set, Optional
import psycopg2
import numpy as np
from loguru import logger

from database.providers.base import DataProvider
from .lemmatization_service import lemmatization_service
from .schema_validator import SchemaValidator


class EmbeddingProcessor:
    """
    Universal processor for creating embedding tables from data providers.
    
    Handles the complete workflow:
    - Model loading and embedding generation
    - CSV data parsing
    - Schema validation and table creation
    - Incremental processing with duplicate detection
    - Index creation for performance
    """
    
    def __init__(
        self,
        provider: DataProvider,
        target_table: str,
        model_name: str,
        db_config: Dict[str, Any]
    ):
        """
        Initialize the embedding processor.
        
        Args:
            provider: Data provider instance
            target_table: Name of the target database table
            model_name: SentenceTransformer model identifier
            db_config: Database configuration dict with keys:
                - host: Database host
                - port: Database port
                - name: Database name
                - user: Database user
                - password: Database password
                - schema: Application schema (optional)
                - extensions_schema: Extensions schema (optional)
        """
        self.provider = provider
        self.target_table = target_table
        self.model_name = model_name
        self.db_config = db_config
        
        # Will be initialized during processing
        self.model = None
        self.model_dimension = 0
        self.conn = None
        self.schema_validator = None
        
        # Statistics
        self.stats = {
            'total_records': 0,
            'existing_records': 0,
            'new_records': 0,
            'successfully_inserted': 0,
            'failed_records': 0,
            'processing_time': 0.0
        }
        
        logger.info(f"EmbeddingProcessor initialized for table '{target_table}'")
    
    def _load_model(self):
        """Load the SentenceTransformer model and get its dimension."""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.model_dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully (dimension: {self.model_dimension})")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _connect_database(self):
        """Establish database connection."""
        try:
            logger.info(f"Connecting to database: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['name']}")
            
            self.conn = psycopg2.connect(
                dbname=self.db_config['name'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                host=self.db_config['host'],
                port=self.db_config['port']
            )
            
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def _parse_csv_data(self, csv_string: str) -> tuple[List[str], List[Dict[str, str]]]:
        """
        Parse CSV string into headers and records.
        
        Args:
            csv_string: CSV data as string
            
        Returns:
            Tuple of (column_names, records)
        """
        reader = csv.DictReader(StringIO(csv_string), delimiter=';')
        
        # Get column names from first row (header)
        column_names = reader.fieldnames
        if not column_names:
            raise ValueError("CSV has no headers")
        
        # Read all records
        records = list(reader)
        
        logger.info(f"Parsed CSV: {len(column_names)} columns, {len(records)} records")
        
        return column_names, records
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding as list of floats
        """
        try:
            embedding = self.model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def _prepare_value_for_db(self, value: str, column_name: str) -> Any:
        """
        Prepare a value for database insertion based on column type.
        
        Args:
            value: String value from CSV
            column_name: Name of the column
            
        Returns:
            Processed value appropriate for database
        """
        # Handle empty values
        if not value or value.strip() == '':
            if column_name.endswith('_json'):
                return None
            return value
        
        # Handle JSON columns
        if column_name.endswith('_json'):
            try:
                # Parse and return as JSON string for JSONB column
                json_obj = json.loads(value)
                return json.dumps(json_obj)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in column '{column_name}': {e}")
                return None
        
        return value
    
    def _insert_record(
        self,
        cur: psycopg2.extensions.cursor,
        record: Dict[str, str],
        csv_columns: List[str],
        lemmatized_text: str,
        embedding: List[float]
    ):
        """
        Insert a single record into the database.
        
        Args:
            cur: Database cursor
            record: CSV record as dict
            csv_columns: List of CSV column names
            lemmatized_text: Lemmatized version of text
            embedding: Vector embedding
        """
        # Prepare column names and values
        columns = list(csv_columns) + ['lemmatized_text', 'embedding']
        
        # Prepare values
        values = []
        for col in csv_columns:
            value = record.get(col, '')
            processed_value = self._prepare_value_for_db(value, col)
            values.append(processed_value)
        
        # Add lemmatized_text and embedding
        values.append(lemmatized_text)
        values.append(embedding)
        
        # Build INSERT query
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)
        
        insert_sql = f"""
            INSERT INTO {self.target_table} ({columns_str})
            VALUES ({placeholders})
        """
        
        cur.execute(insert_sql, values)
    
    def process(self):
        """
        Execute the complete embedding processing workflow.
        
        Returns:
            Statistics dictionary with processing results
        """
        start_time = time.time()
        
        try:
            # Step 1: Load model
            self._load_model()
            
            # Step 2: Connect to database
            self._connect_database()
            
            # Step 3: Initialize schema validator
            self.schema_validator = SchemaValidator(
                self.conn,
                schema=self.db_config.get('schema'),
                extensions_schema=self.db_config.get('extensions_schema')
            )
            
            # Step 4: Get CSV data from provider
            logger.info("Fetching data from provider...")
            csv_data = self.provider.get_data()
            
            # Step 5: Parse CSV
            csv_columns, records = self._parse_csv_data(csv_data)
            self.stats['total_records'] = len(records)
            
            # Verify 'text' column exists
            if 'text' not in csv_columns:
                raise ValueError("CSV must contain a 'text' column")
            
            # Step 6: Validate or create table schema
            if self.schema_validator.validate_schema(self.target_table, csv_columns):
                logger.info(f"Table {self.target_table} exists with valid schema")
                # Load existing lemmatized texts for deduplication
                existing_texts = self.schema_validator.get_existing_lemmatized_texts(self.target_table)
                self.stats['existing_records'] = len(existing_texts)
                logger.info(f"Found {len(existing_texts)} existing records in database")
            else:
                logger.info(f"Table {self.target_table} does not exist or has invalid schema")
                # Drop and recreate table
                self.schema_validator.drop_table(self.target_table)
                self.schema_validator.create_table(
                    self.target_table,
                    csv_columns,
                    self.model_dimension
                )
                existing_texts = set()
            
            # Step 7: Process records
            logger.info("Processing records...")
            inserted_count = 0
            failed_count = 0
            
            with self.conn.cursor() as cur:
                for idx, record in enumerate(records, 1):
                    try:
                        # Get text value
                        text = record.get('text', '').strip()
                        if not text:
                            logger.warning(f"Record {idx}: Empty text field, skipping")
                            failed_count += 1
                            continue
                        
                        # Compute lemmatized_text
                        lemmatized_text = lemmatization_service.lemmatize(text)
                        
                        # Check if already exists
                        if lemmatized_text in existing_texts:
                            logger.debug(f"Record {idx}: Already exists, skipping")
                            continue
                        
                        # Generate embedding
                        embedding = self._generate_embedding(lemmatized_text)
                        
                        # Insert into database
                        self._insert_record(cur, record, csv_columns, lemmatized_text, embedding)
                        
                        # Add to existing set
                        existing_texts.add(lemmatized_text)
                        inserted_count += 1
                        
                        if inserted_count % 10 == 0:
                            logger.info(f"Processed {inserted_count} new records...")
                        
                    except Exception as e:
                        logger.error(f"Failed to process record {idx}: {e}")
                        failed_count += 1
                        continue
                
                # Commit transaction
                self.conn.commit()
                logger.info(f"Committed {inserted_count} new records to database")
            
            self.stats['new_records'] = inserted_count
            self.stats['successfully_inserted'] = inserted_count
            self.stats['failed_records'] = failed_count
            
            # Step 8: Create indexes (only if we inserted new records)
            if inserted_count > 0:
                self.schema_validator.create_indexes(self.target_table)
            
            # Calculate processing time
            self.stats['processing_time'] = time.time() - start_time
            
            # Step 9: Log statistics
            self._log_statistics()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            if self.conn:
                self.conn.rollback()
            raise
            
        finally:
            # Cleanup
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")
    
    def _log_statistics(self):
        """Log processing statistics."""
        provider_info = self.provider.get_source_info()
        provider_name = provider_info.get('source_type', 'Unknown')
        
        logger.info("=" * 60)
        logger.info(f"Processing Statistics for {self.target_table}")
        logger.info("=" * 60)
        logger.info(f"Provider: {self.provider.__class__.__name__}")
        logger.info(f"Target Table: {self.target_table}")
        logger.info(f"Model: {self.model_name} (dimension: {self.model_dimension})")
        logger.info("-" * 60)
        logger.info(f"Total records from CSV: {self.stats['total_records']}")
        logger.info(f"Existing records in DB: {self.stats['existing_records']}")
        logger.info(f"New records processed: {self.stats['new_records']}")
        logger.info(f"Successfully inserted: {self.stats['successfully_inserted']}")
        logger.info(f"Failed insertions: {self.stats['failed_records']}")
        logger.info(f"Processing time: {self.stats['processing_time']:.2f} seconds")
        logger.info("=" * 60)
