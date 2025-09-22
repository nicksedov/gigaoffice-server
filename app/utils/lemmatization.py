"""
Lemmatization Service
Service for text lemmatization for Russian and English languages
"""

import re
from typing import Optional
from loguru import logger
from app.resource_loader import resource_loader

try:
    from pymystem3 import Mystem
    MYSTEM_AVAILABLE = True
except ImportError:
    MYSTEM_AVAILABLE = False
    logger.warning("pymystem3 not available, Russian lemmatization will be disabled")

try:
    import nltk
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("nltk not available, English lemmatization will be disabled")

class LemmatizationError(Exception):
    """Exception raised for errors in the lemmatization process"""
    pass

class LemmatizerFactory:
    """Factory class to create language-specific lemmatizers"""
    
    @staticmethod
    def create_lemmatizer(language: str):
        """
        Create a lemmatizer for the specified language
        
        Args:
            language: Language code ('ru' for Russian, 'en' for English)
            
        Returns:
            Language-specific lemmatizer instance
            
        Raises:
            LemmatizationError: If lemmatizer is not available for the language
        """
        if language == 'ru':
            if not MYSTEM_AVAILABLE:
                raise LemmatizationError("pymystem3 not available for Russian lemmatization")
            return RussianLemmatizer()
        elif language == 'en':
            if not NLTK_AVAILABLE:
                raise LemmatizationError("nltk not available for English lemmatization")
            return EnglishLemmatizer()
        else:
            raise LemmatizationError(f"Lemmatizer not available for language: {language}")

class RussianLemmatizer:
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

class EnglishLemmatizer:
    """Implementation using NLTK for English text lemmatization"""
    
    def __init__(self):
        """Initialize the English lemmatizer"""
        if not NLTK_AVAILABLE:
            raise LemmatizationError("nltk not available")
        self.lemmatizer = WordNetLemmatizer()
    
    def lemmatize(self, text: str) -> str:
        """
        Lemmatize English text
        
        Args:
            text: Text to lemmatize
            
        Returns:
            Lemmatized text
        """
        try:
            # Tokenize the text
            tokens = word_tokenize(text)
            # Lemmatize each token and join back
            lemmatized_tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
            return ' '.join(lemmatized_tokens)
        except Exception as e:
            logger.error(f"Error during English lemmatization: {e}")
            raise LemmatizationError(f"Failed to lemmatize English text: {e}")

class LemmatizationService:
    """Unified interface for lemmatizing text with language detection"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the lemmatization service
        
        Args:
            config: Configuration dictionary with lemmatization settings
        """
        # Load configuration if not provided
        if config is None:
            try:
                config_data = resource_loader.get_config('lemmatization_config')
                self.config = config_data.get('lemmatization', {})
            except Exception as e:
                logger.warning(f"Failed to load lemmatization config: {e}")
                self.config = {}
        else:
            self.config = config
            
        self.enabled = self.config.get('enabled', True)
        self.russian_backend = self.config.get('russian_backend', 'pymystem3')
        self.english_backend = self.config.get('english_backend', 'nltk')
        
        # Initialize lemmatizers
        self._russian_lemmatizer = None
        self._english_lemmatizer = None
        
        if self.enabled:
            self._initialize_lemmatizers()
    
    def _initialize_lemmatizers(self):
        """Initialize language-specific lemmatizers"""
        try:
            if MYSTEM_AVAILABLE:
                self._russian_lemmatizer = RussianLemmatizer()
        except Exception as e:
            logger.warning(f"Failed to initialize Russian lemmatizer: {e}")
            
        try:
            if NLTK_AVAILABLE:
                self._english_lemmatizer = EnglishLemmatizer()
        except Exception as e:
            logger.warning(f"Failed to initialize English lemmatizer: {e}")
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of the text (simple implementation)
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code ('ru' for Russian, 'en' for English)
        """
        # Simple detection based on Cyrillic characters
        if re.search(r'[а-яё]', text.lower()):
            return 'ru'
        else:
            return 'en'
    
    def lemmatize(self, text: str, language: Optional[str] = None) -> dict:
        """
        Lemmatize text with language detection
        
        Args:
            text: Text to lemmatize
            language: Optional language code, if not provided will be detected
            
        Returns:
            Dictionary with original_text, lemmatized_text, and language
        """
        if not self.enabled:
            return {
                'original_text': text,
                'lemmatized_text': text,
                'language': language or 'unknown'
            }
        
        # Detect language if not provided
        if language is None:
            language = self.detect_language(text)
        
        # Return early if text is empty
        if not text.strip():
            return {
                'original_text': text,
                'lemmatized_text': text,
                'language': language
            }
        
        try:
            # Apply appropriate lemmatizer
            if language == 'ru' and self._russian_lemmatizer:
                lemmatized_text = self._russian_lemmatizer.lemmatize(text)
            elif language == 'en' and self._english_lemmatizer:
                lemmatized_text = self._english_lemmatizer.lemmatize(text)
            else:
                # Fallback to original text if lemmatizer is not available
                logger.warning(f"No lemmatizer available for language {language}, returning original text")
                lemmatized_text = text
            
            return {
                'original_text': text,
                'lemmatized_text': lemmatized_text,
                'language': language
            }
            
        except Exception as e:
            logger.error(f"Error during lemmatization: {e}")
            # Fallback to original text in case of error
            return {
                'original_text': text,
                'lemmatized_text': text,
                'language': language
            }

# Create singleton instance
lemmatization_service = LemmatizationService()