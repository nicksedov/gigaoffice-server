"""
Header Vector Search Service
Service for searching header embeddings using vector similarity
"""
from typing import List, Tuple
import psycopg2
from .base import BaseVectorSearchService


class HeaderVectorSearch(BaseVectorSearchService):
    """Vector search service for header_embeddings table"""

    def _execute_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Tuple[str, float]]:
        """
        Execute vector search on header_embeddings table.
        
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
