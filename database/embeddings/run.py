"""
Orchestration script for running embedding processors on all data providers.

This script processes all three data providers sequentially:
1. TableHeadersProvider -> header_embeddings
2. ClassificationPromptsProvider -> classification_prompt_embeddings
3. CategorizedPromptsProvider -> categorized_prompt_embeddings
"""

import os
import sys
from pathlib import Path
from loguru import logger

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.embeddings.providers import (
    TableHeadersProvider,
    ClassificationPromptsProvider,
    CategorizedPromptsProvider
)
from database.embeddings.processor import EmbeddingProcessor


# Configuration from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "gigaoffice")
DB_USER = os.getenv("DB_USER", "gigaoffice")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "")
DB_EXTENSIONS_SCHEMA = os.getenv("DB_EXTENSIONS_SCHEMA", "")
MODEL_CACHE_PATH = os.getenv("MODEL_CACHE_PATH", "")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "ai-forever/ru-en-RoSBERTa")


def get_db_config() -> dict:
    """
    Build database configuration dictionary.
    
    Returns:
        Database configuration dict
    """
    config = {
        'host': DB_HOST,
        'port': DB_PORT,
        'name': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD,
    }
    
    if DB_SCHEMA:
        config['schema'] = DB_SCHEMA
    
    if DB_EXTENSIONS_SCHEMA:
        config['extensions_schema'] = DB_EXTENSIONS_SCHEMA
    
    return config


def get_model_path() -> str:
    """
    Build model path with cache support.
    
    Returns:
        Model path or name
    """
    if MODEL_CACHE_PATH:
        return f"{MODEL_CACHE_PATH}/{EMBEDDING_MODEL_NAME}"
    return EMBEDDING_MODEL_NAME


def process_provider(provider, target_table: str, model_name: str, db_config: dict) -> dict:
    """
    Process a single data provider.
    
    Args:
        provider: Data provider instance
        target_table: Target database table name
        model_name: Embedding model name
        db_config: Database configuration
        
    Returns:
        Processing statistics dictionary
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Starting processing for {provider.__class__.__name__} -> {target_table}")
    logger.info(f"{'=' * 80}\n")
    
    try:
        processor = EmbeddingProcessor(
            provider=provider,
            target_table=target_table,
            model_name=model_name,
            db_config=db_config
        )
        
        stats = processor.process()
        logger.info(f"\n✅ Successfully processed {target_table}\n")
        return stats
        
    except Exception as e:
        logger.error(f"\n❌ Failed to process {target_table}: {e}\n")
        return {
            'total_records': 0,
            'new_records': 0,
            'successfully_inserted': 0,
            'failed_records': 0,
            'processing_time': 0.0,
            'error': str(e)
        }


def main():
    """Main orchestration function."""
    logger.info("=" * 80)
    logger.info("EMBEDDING PROCESSOR ORCHESTRATION")
    logger.info("=" * 80)
    logger.info(f"Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info(f"Model: {EMBEDDING_MODEL_NAME}")
    logger.info("=" * 80)
    
    # Get configuration
    db_config = get_db_config()
    model_name = get_model_path()
    
    # Track overall statistics
    all_stats = []
    
    # Provider 1: Table Headers
    try:
        logger.info("\n[1/3] Processing Table Headers...")
        provider = TableHeadersProvider()
        stats = process_provider(provider, "header_embeddings", model_name, db_config)
        all_stats.append(('header_embeddings', stats))
    except Exception as e:
        logger.error(f"Failed to initialize TableHeadersProvider: {e}")
        all_stats.append(('header_embeddings', {'error': str(e)}))
    
    # Provider 2: Classification Prompts
    try:
        logger.info("\n[2/3] Processing Classification Prompts...")
        provider = ClassificationPromptsProvider()
        stats = process_provider(provider, "classification_prompt_embeddings", model_name, db_config)
        all_stats.append(('classification_prompt_embeddings', stats))
    except Exception as e:
        logger.error(f"Failed to initialize ClassificationPromptsProvider: {e}")
        all_stats.append(('classification_prompt_embeddings', {'error': str(e)}))
    
    # Provider 3: Categorized Prompts
    try:
        logger.info("\n[3/3] Processing Categorized Prompts...")
        provider = CategorizedPromptsProvider()
        stats = process_provider(provider, "categorized_prompt_embeddings", model_name, db_config)
        all_stats.append(('categorized_prompt_embeddings', stats))
    except Exception as e:
        logger.error(f"Failed to initialize CategorizedPromptsProvider: {e}")
        all_stats.append(('categorized_prompt_embeddings', {'error': str(e)}))
    
    # Print overall summary
    logger.info("\n" + "=" * 80)
    logger.info("OVERALL PROCESSING SUMMARY")
    logger.info("=" * 80)
    
    total_inserted = 0
    total_failed = 0
    total_time = 0.0
    
    for table_name, stats in all_stats:
        if 'error' in stats:
            logger.error(f"❌ {table_name}: FAILED - {stats['error']}")
        else:
            logger.info(f"✅ {table_name}:")
            logger.info(f"   - Total records: {stats.get('total_records', 0)}")
            logger.info(f"   - New records: {stats.get('new_records', 0)}")
            logger.info(f"   - Inserted: {stats.get('successfully_inserted', 0)}")
            logger.info(f"   - Failed: {stats.get('failed_records', 0)}")
            logger.info(f"   - Time: {stats.get('processing_time', 0):.2f}s")
            
            total_inserted += stats.get('successfully_inserted', 0)
            total_failed += stats.get('failed_records', 0)
            total_time += stats.get('processing_time', 0)
    
    logger.info("-" * 80)
    logger.info(f"Total inserted: {total_inserted}")
    logger.info(f"Total failed: {total_failed}")
    logger.info(f"Total time: {total_time:.2f} seconds")
    logger.info("=" * 80)
    
    # Return exit code based on success
    errors = sum(1 for _, stats in all_stats if 'error' in stats)
    if errors > 0:
        logger.warning(f"{errors} provider(s) failed")
        return 1
    
    logger.info("All providers processed successfully!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
