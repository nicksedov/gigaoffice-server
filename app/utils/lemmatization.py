"""
Lemmatization Service
Service for text lemmatization for Russian language
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
        Lemmatize Russian text
        
        Args:
            text: Text to lemmatize
            
        Returns:
            Lemmatized text
        """
        try:
            # Mystem returns a list, we join it back to a string
            lemmatized = self.mystem.lemmatize(text)
            # Remove newline characters that Mystem sometimes adds
            result = ''.join(lemmatized).strip()
            return result
        except Exception as e:
            logger.error(f"Error during Russian lemmatization: {e}")
            raise LemmatizationError(f"Failed to lemmatize Russian text: {e}")

class LemmatizationService:
    """Unified interface for lemmatizing text with language detection"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the lemmatization service
        
        Args:
            config: Configuration dictionary with lemmatization settings
        """
        # Initialize lemmatizers
        self._lemmatizer = None

        try:
            if MYSTEM_AVAILABLE:
                self._lemmatizer = MystemLemmatizer()
        except Exception as e:
            logger.warning(f"Failed to initialize Russian lemmatizer: {e}")
    
    def lemmatize(self, text: str) -> str:
        """
        Lemmatize text
        
        Args:
            text: Text to lemmatize
            
        Returns:
            lemmatized_text
        """
     
        # Return early if text is empty
        if not text.strip():
            return text
        
        try:
            return self._lemmatizer.lemmatize(text)
            
        except Exception as e:
            logger.error(f"Error during lemmatization: {e}")
            # Fallback to original text in case of error
            return text

# Create singleton instance
lemmatization_service = LemmatizationService()