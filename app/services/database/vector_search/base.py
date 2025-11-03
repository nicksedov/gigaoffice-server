"""
Base Vector Search Service
Abstract base class for all vector search implementations
"""
import re
from abc import ABC, abstractmethod
from typing import List, Tuple, Union, Any
from loguru import logger
import psycopg2
from app.services.database.manager import db_manager
from app.utils.lemmatization import lemmatization_service
from .model import generate_embedding


class BaseVectorSearchService(ABC):
    """Base class for vector similarity search services"""
    
    def __init__(self):
        """Initialize the base vector search service"""
        pass

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a text string.
        
        Args:
            text: Text to vectorize
            
        Returns:
            Vector representation as a list of floats
        """
        return generate_embedding(text)

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
