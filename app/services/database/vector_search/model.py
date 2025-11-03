"""
Vector Search Model Utilities
Shared model initialization and embedding generation for vector search services
"""
import os
from typing import List
from sentence_transformers import SentenceTransformer


# Model configuration from environment variables
MODEL_CACHE_PATH = os.getenv("MODEL_CACHE_PATH", "")
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "ai-forever/ru-en-RoSBERTa")
MODEL_PATH = f"{MODEL_CACHE_PATH}/{MODEL_NAME}"

# Initialize model once at module load time (singleton pattern)
# This is expensive, so we only do it once and share across all search services
_ru_model = SentenceTransformer(MODEL_PATH)


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for a text string.
    
    Args:
        text: Text to vectorize
        
    Returns:
        Vector representation as a list of floats
    """
    return _ru_model.encode([text])[0].tolist()
