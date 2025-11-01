"""
Vector Search Module
Provides vector similarity search services for headers and prompt examples
"""
from .header_search import HeaderVectorSearch
from .prompt_search import PromptExampleVectorSearch

# Create singleton instances for use throughout the application
header_vector_search = HeaderVectorSearch()
prompt_example_search = PromptExampleVectorSearch()

__all__ = [
    "header_vector_search",
    "prompt_example_search",
    "HeaderVectorSearch",
    "PromptExampleVectorSearch"
]
