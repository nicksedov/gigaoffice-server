"""
Embedding Processor Module.

This module provides universal embedding processing capabilities
for creating and populating database tables with vector embeddings.
"""

from .embedding_processor import EmbeddingProcessor
from .lemmatization_service import LemmatizationService, LemmatizationError
from .schema_validator import SchemaValidator

__all__ = [
    "EmbeddingProcessor",
    "LemmatizationService",
    "LemmatizationError",
    "SchemaValidator",
]
