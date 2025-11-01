import os
import re
import json
from abc import ABC, abstractmethod
from typing import List, Tuple, Union, Dict, Any
from loguru import logger
import psycopg2
from sentence_transformers import SentenceTransformer
from app.services.database.manager import db_manager
from app.utils.lemmatization import lemmatization_service


MODEL_CACHE_PATH = os.getenv("MODEL_CACHE_PATH", "")
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "ai-forever/ru-en-RoSBERTa")
MODEL_PATH = f"{MODEL_CACHE_PATH}/{MODEL_NAME}"

# Инициализация модели один раз при старте приложения
_ru_model = SentenceTransformer(MODEL_PATH)


class BaseVectorSearchService(ABC):
    """Base class for vector similarity search services"""
    
    def __init__(self):
        """Initialize the base vector search service"""
        pass

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Получает эмбеддинг для строки.
        
        Args:
            text: Текст для векторизации
            
        Returns:
            Векторное представление текста как список чисел с плавающей точкой
        """
        return _ru_model.encode([text])[0].tolist()

    def _preprocess_text(self, text: str) -> Tuple[str, str]:
        """
        Preprocess text for search: lowercase and lemmatize if Russian.
        
        Args:
            text: Text to preprocess
            
        Returns:
            Tuple of (preprocessed_text, language)
        """
        preprocessed = text.lower()
        language = 'ru' if re.search(r'[а-яё]', preprocessed) else 'en'
        if language == 'ru':
            preprocessed = lemmatization_service.lemmatize(preprocessed)
        return preprocessed, language

    @abstractmethod
    def _execute_fulltext_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Any]:
        """
        Execute fulltext vector search. Must be implemented by subclasses.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Additional search parameters
            
        Returns:
            List of search results (format depends on subclass)
        """
        pass

    @abstractmethod
    def _execute_fast_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Any]:
        """
        Execute fast lemmatization-based search. Must be implemented by subclasses.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Additional search parameters
            
        Returns:
            List of search results (format depends on subclass)
        """
        pass

    def search(
        self,
        query: Union[str, List[str]],
        search_mode: str = "fulltext",
        limit: int = 3,
        **kwargs
    ) -> List[Any]:
        """
        Unified search method that supports both fulltext and fast modes.
        
        Args:
            query: Search string or list of search strings
            search_mode: 'fulltext' for vector-based search, 'fast' for lemmatization-based search
            limit: Maximum number of results to return per search string
            **kwargs: Additional search parameters passed to subclass methods
            
        Returns:
            List of search results (format depends on subclass)
        """
        if search_mode not in ["fulltext", "fast"]:
            raise ValueError(f"Invalid search_mode: {search_mode}. Must be 'fulltext' or 'fast'")
        
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
                    if search_mode == "fast":
                        results = self._execute_fast_search(search_string, conn, limit, **kwargs)
                    else:  # fulltext
                        results = self._execute_fulltext_search(search_string, conn, limit, **kwargs)
                    all_results.extend(results)
                
                return all_results
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error performing {search_mode} search: {e}")
            raise


class HeaderVectorSearch(BaseVectorSearchService):
    """Vector search service for header_embeddings table"""

    def _execute_fulltext_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Tuple[str, str, float]]:
        """
        Execute fulltext vector search on header_embeddings table.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Additional parameters (unused)
            
        Returns:
            List of tuples (header, language, score)
        """
        # Preprocess query
        preprocessed_query, _ = self._preprocess_text(query)
        
        # Generate embedding
        query_embedding = self._generate_embedding(preprocessed_query)
        
        with conn.cursor() as cur:
            sql = """
                SELECT header, language, 1 - (embedding <=> %s::vector) AS score
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
    ) -> List[Tuple[str, str, float]]:
        """
        Execute fast search on header_embeddings table using lemmatization.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Additional parameters (unused)
            
        Returns:
            List of tuples (header, language, score)
        """
        # Preprocess query
        preprocessed_query, _ = self._preprocess_text(query)
        
        with conn.cursor() as cur:
            sql = """
                SELECT header, language, 
                       CASE WHEN lemmatized_header = %s THEN 1.0 ELSE 0.0 END AS score
                FROM header_embeddings
                WHERE lemmatized_header = %s
                ORDER BY score DESC
                LIMIT %s
            """
            cur.execute(sql, (preprocessed_query, preprocessed_query, limit))
            results = cur.fetchall()
            
            # If no exact matches found, return empty list
            if not results:
                return []
            
            return results


class PromptExampleVectorSearch(BaseVectorSearchService):
    """Vector search service for prompt_examples table"""

    def _execute_fulltext_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Tuple[str, str, str, str, float]]:
        """
        Execute fulltext vector search on prompt_examples table.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Must contain 'category' for filtering
            
        Returns:
            List of tuples (prompt_text, request_json, response_json, language, score)
        """
        category = kwargs.get('category')
        if not category:
            raise ValueError("Category parameter is required for prompt example search")
        
        # Preprocess query
        preprocessed_query, _ = self._preprocess_text(query)
        
        # Generate embedding
        query_embedding = self._generate_embedding(preprocessed_query)
        
        with conn.cursor() as cur:
            sql = """
                SELECT prompt_text, request_json::text, response_json::text, language, 
                       1 - (embedding <=> %s::vector) AS score
                FROM prompt_examples
                WHERE category = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            cur.execute(sql, (query_embedding, category, query_embedding, limit))
            return cur.fetchall()

    def _execute_fast_search(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        limit: int,
        **kwargs
    ) -> List[Tuple[str, str, str, str, float]]:
        """
        Execute fast search on prompt_examples table using lemmatization.
        
        Args:
            query: Search query string
            conn: Database connection
            limit: Maximum number of results
            **kwargs: Must contain 'category' for filtering
            
        Returns:
            List of tuples (prompt_text, request_json, response_json, language, score)
        """
        category = kwargs.get('category')
        if not category:
            raise ValueError("Category parameter is required for prompt example search")
        
        # Preprocess query
        preprocessed_query, _ = self._preprocess_text(query)
        
        with conn.cursor() as cur:
            sql = """
                SELECT prompt_text, request_json::text, response_json::text, language,
                       CASE WHEN lemmatized_prompt = %s THEN 1.0 ELSE 0.0 END AS score
                FROM prompt_examples
                WHERE category = %s AND lemmatized_prompt = %s
                ORDER BY score DESC
                LIMIT %s
            """
            cur.execute(sql, (preprocessed_query, category, preprocessed_query, limit))
            results = cur.fetchall()
            
            # If no exact matches found, return empty list
            if not results:
                return []
            
            return results

    def search_examples(
        self,
        query: str,
        category: str,
        search_mode: str = "fulltext",
        limit: int = 3
    ) -> List[Dict[str, str]]:
        """
        Search for prompt examples and return them in the format expected by prompt builder.
        
        Args:
            query: User query text for relevance matching
            category: Prompt category to filter by
            search_mode: 'fulltext' for vector-based search, 'fast' for lemmatization-based search
            limit: Maximum number of examples to return
            
        Returns:
            List of dictionaries with keys: task, request_table, response_table
        """
        # Use the base search method with category parameter
        results = self.search(query, search_mode=search_mode, limit=limit, category=category)
        
        # Transform results to the expected format
        examples = []
        for prompt_text, request_json, response_json, language, score in results:
            examples.append({
                'task': prompt_text,
                'request_table': request_json if request_json else '',
                'response_table': response_json if response_json else ''
            })
        
        return examples


# Legacy compatibility class
class VectorSearchService(HeaderVectorSearch):
    """
    Legacy compatibility class for existing code.
    Inherits from HeaderVectorSearch to maintain backward compatibility.
    """
    
    def fast_search(
        self, 
        query: Union[str, List[str]], 
        embedding_table: str,
        limit: int = 3
    ) -> List[Tuple[str, str, float]]:
        """
        Backward compatible fast_search method.
        
        Args:
            query: Search string or list of search strings
            embedding_table: Name of the table with embeddings (for compatibility, not used)
            limit: Maximum number of results to return per search string
            
        Returns:
            List of tuples containing (header_text, language, similarity_score)
        """
        return self.search(query, search_mode="fast", limit=limit)
    
    def fulltext_search(
        self, 
        query: Union[str, List[str]], 
        embedding_table: str,
        limit: int = 3
    ) -> List[Tuple[str, str, float]]:
        """
        Backward compatible fulltext_search method.
        
        Args:
            query: Search string or list of search strings
            embedding_table: Name of the table with embeddings (for compatibility, not used)
            limit: Maximum number of results to return per search string
            
        Returns:
            List of tuples containing (header_text, language, similarity_score)
        """
        return self.search(query, search_mode="fulltext", limit=limit)


# Create singleton instances
vector_search_service = VectorSearchService()
header_vector_search = HeaderVectorSearch()
prompt_example_search = PromptExampleVectorSearch()
