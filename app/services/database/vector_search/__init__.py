"""
Vector Search Module
Provides vector similarity search services for headers and prompt examples
"""
from .header_search import HeaderVectorSearch
from .prompt_search import (
    ClassificationPromptSearch,
    CategorizedPromptSearch,
    PromptExampleVectorSearch  # Deprecated, kept for backward compatibility
)

# Create singleton instances for use throughout the application
header_vector_search = HeaderVectorSearch()
classification_prompt_search = ClassificationPromptSearch()
categorized_prompt_search = CategorizedPromptSearch()
prompt_example_search = PromptExampleVectorSearch()  # Deprecated, kept for backward compatibility

__all__ = [
    "header_vector_search",
    "classification_prompt_search",
    "categorized_prompt_search",
    "prompt_example_search",  # Deprecated
    "HeaderVectorSearch",
    "ClassificationPromptSearch",
    "CategorizedPromptSearch",
    "PromptExampleVectorSearch"  # Deprecated
]
