"""
Header Vector Search Service
Service for searching header embeddings using vector similarity and lemmatization
"""
from typing import List, Tuple
import psycopg2
from .base import BaseVectorSearchService


class HeaderVectorSearch(BaseVectorSearchService):
    """Vector search service for header_embeddings table"""

    def _execute_fulltext_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Tuple[str, float]]:
        """
        Execute fulltext vector search on header_embeddings table.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Additional parameters (unused)
            
        Returns:
            List of tuples (text, score)
        """
        # Preprocess query
        preprocessed_query, _ = self._preprocess_text(query)
        
        # Generate embedding
        query_embedding = self._generate_embedding(preprocessed_query)
        
        with conn.cursor() as cur:
            sql = """
                SELECT text, 1 - (embedding <=> %s::vector) AS score
                FROM header_embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            cur.execute(sql, (query_embedding, query_embedding, limit))
            return cur.fetchall()

    def _execute_fast_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Tuple[str, float]]:
        """
        Execute fast search on header_embeddings table using lemmatization.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Additional parameters (unused)
            
        Returns:
            List of tuples (text, score)
        """
        # Preprocess query
        preprocessed_query, _ = self._preprocess_text(query)
        
        with conn.cursor() as cur:
            sql = """
                SELECT text, 
                       CASE WHEN lemmatized_text = %s THEN 1.0 ELSE 0.0 END AS score
                FROM header_embeddings
                WHERE lemmatized_text = %s
                ORDER BY score DESC
                LIMIT %s
            """
            cur.execute(sql, (preprocessed_query, preprocessed_query, limit))
            results = cur.fetchall()
            
            # If no exact matches found, return empty list
            if not results:
                return []
            
            return results
