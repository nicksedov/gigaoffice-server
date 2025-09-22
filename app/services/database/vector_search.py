"""
Vector Search Service
Service for performing vector similarity searches in the database
"""

from typing import List, Tuple, Union
from sqlalchemy.orm import Session
from loguru import logger
import psycopg2

from app.services.database.manager import db_manager
from resources.vector.embeddings_search import search_common_headers, ru_embedder

class VectorSearchService:
    """Service for performing vector similarity searches in the database"""
    
    def __init__(self):
        """Initialize the vector search service"""
        pass
    
    def search_headers(
        self, 
        query: Union[str, List[str]], 
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Search for headers using vector embeddings
        
        Args:
            query: Search string or list of search strings
            limit: Maximum number of results to return per search string
            
        Returns:
            List of tuples containing (header_text, similarity_score)
        """
        try:
            # Get database connection
            engine = db_manager.engine
            conn = engine.raw_connection()
            
            try:
                # Prepare search strings
                search_strings = query if isinstance(query, list) else [query]
                
                # Collect all results
                all_results = []
                
                # Search for each string
                for search_string in search_strings:
                    # Perform vector search
                    results = search_common_headers(search_string, conn, "header_embeddings", limit)
                    all_results.extend(results)
                
                return all_results
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get vector embedding for a text string
        
        Args:
            text: Text to embed
            
        Returns:
            Vector embedding as list of floats
        """
        return ru_embedder(text)

# Create singleton instance
vector_search_service = VectorSearchService()