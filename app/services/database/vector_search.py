"""
Vector Search Service
Service for performing vector similarity searches in the database
"""
import re
from typing import List, Tuple, Union
from sqlalchemy.orm import Session
from loguru import logger
import psycopg2
from typing import List, Tuple, Union
from sentence_transformers import SentenceTransformer
from app.services.database.manager import db_manager
from app.utils.lemmatization import lemmatization_service


MODEL_NAME = "ai-forever/FRIDA"

# Инициализация модели один раз при старте приложения
_ru_model = SentenceTransformer(MODEL_NAME)

class VectorSearchService:
    """Service for performing vector similarity searches in the database"""
    
    def __init__(self):
        """Initialize the vector search service"""
        pass
    

    def _embedder(self, text: str) -> List[float]:
        """
        Получает эмбеддинг для строки.
        
        Args:
            text: Текст для векторизации
            
        Returns:
            Векторное представление текста как список чисел с плавающей точкой
        """
        return _ru_model.encode([text])[0].tolist()

    def _single_fast_search_query(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        embedding_table: str,
        limit: int = 3
    ) -> List[Tuple[str, str, float]]:
        """
        Выполняет быстрый поиск по заголовкам с использованием прямого сравнения лемматизированных строк.

        Args:
            query: Строка для поиска.
            conn: psycopg2 подключение к PostgreSQL.
            embedding_table: Имя таблицы с эмбеддингами (например, 'header_embeddings').
            limit: Максимальное количество результатов.
            
        Returns:
            Список кортежей (header, language, score) отсортированный по релевантности.
        """
        # Preprocess query using lemmatization
        preprocessed_query = query.lower()
        language = 'ru' if re.search(r'[а-яё]', preprocessed_query) else 'en'
        if language == 'ru':
            preprocessed_query = lemmatization_service.lemmatize(preprocessed_query)
        
        with conn.cursor() as cur:
            # Search for exact matches in lemmatized_header column
            sql = f"""
                SELECT header, language, 
                       CASE WHEN lemmatized_header = %s THEN 1.0 ELSE 0.0 END AS score
                FROM {embedding_table}
                WHERE lemmatized_header = %s
                ORDER BY score DESC
                LIMIT %s
            """
            cur.execute(sql, (preprocessed_query, preprocessed_query, limit))
            exact_results = cur.fetchall()
            
            # If no exact matches found, return empty results with score 0.0
            if not exact_results:
                return []
            
            return exact_results

    def _single_search_query(
        self,
        query: str,
        conn: psycopg2.extensions.connection,
        embedding_table: str,
        limit: int = 3
    ) -> List[Tuple[str, str, float]]:
        """
        Выполняет полнотекстовый поиск по заголовкам с использованием векторного поиска pgvector.

        Args:
            query: Строка для поиска.
            conn: psycopg2 подключение к PostgreSQL.
            embedding_table: Имя таблицы с эмбеддингами (например, 'header_embeddings').
            limit: Максимальное количество результатов.
            
        Returns:
            Список кортежей (header, score) отсортированный по релевантности.
        """

        # Lemmatize Russian queries before generating embedding
        preprocessed_query = query.lower()
        language = 'ru' if re.search(r'[а-яё]', preprocessed_query) else 'en'
        if language == 'ru':
            preprocessed_query = lemmatization_service.lemmatize(preprocessed_query)
        
        query_embedding =self._embedder(preprocessed_query)
        with conn.cursor() as cur:
            sql = f"""
                SELECT header, language, 1 - (embedding <=> %s::vector) AS score
                FROM {embedding_table}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            cur.execute(sql, (query_embedding, query_embedding, limit))
            results = cur.fetchall()
            # Return only header and score, ignoring language for compatibility
            return results

    def fast_search(
        self, 
        query: Union[str, List[str]], 
        embedding_table: str,
        limit: int = 3
    ) -> List[Tuple[str, str, float]]:
        """
        Search for headers using fast lemmatization-based exact matching
        
        Args:
            query: Search string or list of search strings
            embedding_table: Name of the table with embeddings
            limit: Maximum number of results to return per search string
            
        Returns:
            List of tuples containing (header_text, language, similarity_score)
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
                    # Perform fast search
                    results = self._single_fast_search_query(search_string, conn, embedding_table, limit)
                    all_results.extend(results)
                
                return all_results
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error performing fast search: {e}")
            raise
    def fulltext_search(
        self, 
        query: Union[str, List[str]], 
        embedding_table: str,
        limit: int = 3
    ) -> List[Tuple[str, str, float]]:
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
                    results = self._single_search_query(search_string, conn, embedding_table, limit)
                    all_results.extend(results)
                
                return all_results
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            raise

    def search(
        self,
        query: Union[str, List[str]],
        embedding_table: str,
        search_mode: str = "fulltext",
        limit: int = 3
    ) -> List[Tuple[str, str, float]]:
        """
        Unified search method that supports both fulltext and fast modes
        
        Args:
            query: Search string or list of search strings
            embedding_table: Name of the table with embeddings
            search_mode: 'fulltext' for vector-based search, 'fast' for lemmatization-based search
            limit: Maximum number of results to return per search string
            
        Returns:
            List of tuples containing (header_text, language, similarity_score)
        """
        if search_mode == "fast":
            return self.fast_search(query, embedding_table, limit)
        elif search_mode == "fulltext":
            return self.fulltext_search(query, embedding_table, limit)
        else:
            raise ValueError(f"Invalid search_mode: {search_mode}. Must be 'fulltext' or 'fast'")

# Create singleton instance
vector_search_service = VectorSearchService()