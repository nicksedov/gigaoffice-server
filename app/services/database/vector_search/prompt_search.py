"""
Prompt Example Vector Search Service
Service for searching prompt examples using vector similarity
"""
from typing import List, Tuple, Dict
import psycopg2
from .base import BaseVectorSearchService


class ClassificationPromptSearch(BaseVectorSearchService):
    """Vector search service for classification_prompt_embeddings table"""

    def _execute_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Tuple[str, str, float]]:
        """
        Execute vector search on classification_prompt_embeddings table.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Additional parameters (unused for classification)
            
        Returns:
            List of tuples (text, response_json, score)
        """
        # Preprocess query
        preprocessed_query, _ = self._preprocess_text(query)
        
        # Generate embedding
        query_embedding = self._generate_embedding(preprocessed_query)
        
        with conn.cursor() as cur:
            sql = """
                SELECT text, response_json::text, 
                       1 - (embedding <=> %s::vector) AS score
                FROM classification_prompt_embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            cur.execute(sql, (query_embedding, query_embedding, limit))
            return cur.fetchall()

    def search_examples(
        self,
        query: str,
        limit: int = 3
    ) -> List[Dict[str, str]]:
        """
        Search for classification prompt examples and return them in the format expected by prompt builder.
        
        Args:
            query: User query text for relevance matching
            limit: Maximum number of examples to return
            
        Returns:
            List of dictionaries with keys: task, request_table, response_table
        """
        # Use the base search method
        results = self.search(query, limit=limit)
        
        # Transform results to the expected format
        examples = []
        for text, response_json, score in results:
            examples.append({
                'task': text,
                'request_table': '',  # No request_json for classification
                'response_table': response_json if response_json else ''
            })
        
        return examples


class CategorizedPromptSearch(BaseVectorSearchService):
    """Vector search service for categorized_prompt_embeddings table"""

    def _execute_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Tuple[str, str, str, float]]:
        """
        Execute vector search on categorized_prompt_embeddings table.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Must contain 'category' for filtering
            
        Returns:
            List of tuples (text, request_json, response_json, score)
        """
        category = kwargs.get('category')
        if not category:
            raise ValueError("Category parameter is required for categorized prompt search")
        
        # Preprocess query
        preprocessed_query, _ = self._preprocess_text(query)
        
        # Generate embedding
        query_embedding = self._generate_embedding(preprocessed_query)
        
        with conn.cursor() as cur:
            sql = """
                SELECT text, request_json::text, response_json::text, 
                       1 - (embedding <=> %s::vector) AS score
                FROM categorized_prompt_embeddings
                WHERE category = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            cur.execute(sql, (query_embedding, category, query_embedding, limit))
            return cur.fetchall()

    def search_examples(
        self,
        query: str,
        category: str,
        limit: int = 3
    ) -> List[Dict[str, str]]:
        """
        Search for categorized prompt examples and return them in the format expected by prompt builder.
        
        Args:
            query: User query text for relevance matching
            category: Prompt category to filter by
            limit: Maximum number of examples to return
            
        Returns:
            List of dictionaries with keys: task, request_table, response_table
        """
        # Use the base search method with category parameter
        results = self.search(query, limit=limit, category=category)
        
        # Transform results to the expected format
        examples = []
        for text, request_json, response_json, score in results:
            examples.append({
                'task': text,
                'request_table': request_json if request_json else '',
                'response_table': response_json if response_json else ''
            })
        
        return examples
