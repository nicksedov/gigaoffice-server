"""
Lemmatization Service for Embedding Processor.

Provides text lemmatization capabilities with language detection
for Russian and English text processing.
"""

import re
from typing import Optional
from loguru import logger

try:
    from pymystem3 import Mystem
    MYSTEM_AVAILABLE = True
except ImportError:
    MYSTEM_AVAILABLE = False
    logger.warning("pymystem3 not available, Russian lemmatization will be disabled")


class LemmatizationError(Exception):
    """Exception raised for errors in the lemmatization process"""
    pass


class MystemLemmatizer:
    """Implementation using pymystem3 for Russian text lemmatization"""
    
    def __init__(self):
        """Initialize the Russian lemmatizer"""
        if not MYSTEM_AVAILABLE:
            raise LemmatizationError("pymystem3 not available")
        self.mystem = Mystem()
    
    def lemmatize(self, text: str) -> str:
        """
        Lemmatize Russian text.
        
        Args:
            text: Text to lemmatize
            
        Returns:
            Lemmatized text
            
        Raises:
            LemmatizationError: If lemmatization fails
        """
        try:
            # Mystem returns a list, we join it back to a string
            lemmatized = self.mystem.lemmatize(text)
            # Remove newline characters and extra whitespace
            result = ''.join(lemmatized).strip()
            return result
        except Exception as e:
            logger.error(f"Error during Russian lemmatization: {e}")
            raise LemmatizationError(f"Failed to lemmatize Russian text: {e}")


class LemmatizationService:
    """
    Service for text lemmatization with language detection.
    
    Automatically detects language and applies appropriate lemmatization:
    - Russian: Uses pymystem3 for morphological analysis
    - English: Returns original text (no lemmatization needed)
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the lemmatization service.
        
        Args:
            config: Configuration dictionary with lemmatization settings (optional)
        """
        self._lemmatizer = None
        
        try:
            if MYSTEM_AVAILABLE:
                self._lemmatizer = MystemLemmatizer()
                logger.info("Lemmatization service initialized with pymystem3")
            else:
                logger.warning("Lemmatization service initialized without pymystem3 support")
        except Exception as e:
            logger.warning(f"Failed to initialize Russian lemmatizer: {e}")
    
    def detect_language(self, text: str) -> str:
        """
        Detect if text contains Russian characters.
        
        Args:
            text: Text to analyze
            
        Returns:
            'ru' if Russian characters detected, 'en' otherwise
        """
        return 'ru' if re.search(r'[а-яё]', text.lower()) else 'en'
    
    def lemmatize(self, text: str) -> str:
        """
        Lemmatize text with automatic language detection.
        
        Args:
            text: Text to lemmatize
            
        Returns:
            Lemmatized text (or original if English or error occurred)
        """
        # Return early if text is empty
        if not text.strip():
            return text
        
        # Detect language
        language = self.detect_language(text)
        
        # Only lemmatize Russian text
        if language == 'ru':
            if self._lemmatizer is None:
                logger.warning("Russian lemmatizer not available, returning original text")
                return text
            
            try:
                return self._lemmatizer.lemmatize(text)
            except Exception as e:
                logger.error(f"Error during lemmatization: {e}")
                # Fallback to original text in case of error
                return text
        
        # For English text, return as-is
        return text


# Create singleton instance
lemmatization_service = LemmatizationService()
