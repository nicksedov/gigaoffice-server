"""
Processor Factory
Creates appropriate spreadsheet processor based on category
"""

from typing import Dict, Type
from loguru import logger

from app.services.gigachat.base import BaseGigaChatService
from app.services.spreadsheet.base_processor import BaseSpreadsheetProcessor
from app.services.spreadsheet.formatting_processor import FormattingProcessor
from app.services.spreadsheet.analysis_processor import AnalysisProcessor
from app.services.spreadsheet.search_processor import SearchProcessor
from app.services.spreadsheet.generation_processor import GenerationProcessor
from app.services.spreadsheet.transformation_processor import TransformationProcessor
from app.services.spreadsheet.assistance_processor import AssistanceProcessor


# Category to processor class mapping
PROCESSOR_MAPPING: Dict[str, Type[BaseSpreadsheetProcessor]] = {
    'spreadsheet-formatting': FormattingProcessor,
    'spreadsheet-analysis': AnalysisProcessor,
    'spreadsheet-search': SearchProcessor,
    'spreadsheet-generation': GenerationProcessor,
    'spreadsheet-transformation': TransformationProcessor,
    'spreadsheet-assistance': AssistanceProcessor
}

# Default processor for unknown categories (most complete data)
DEFAULT_PROCESSOR = TransformationProcessor


def create_spreadsheet_processor(
    category: str,
    gigachat_service: BaseGigaChatService
) -> BaseSpreadsheetProcessor:
    """
    Create appropriate spreadsheet processor based on category.
    
    This factory method instantiates the correct processor class based on
    the request category, ensuring that data preprocessing matches the
    category's requirements.
    
    Args:
        category: Category name (e.g., 'spreadsheet-formatting')
        gigachat_service: Initialized GigaChat service instance
        
    Returns:
        Initialized processor instance for the specified category
        
    Examples:
        >>> processor = create_processor('spreadsheet-formatting', gigachat_service)
        >>> isinstance(processor, FormattingProcessor)
        True
    """
    processor_class = PROCESSOR_MAPPING.get(category, DEFAULT_PROCESSOR)
    
    if category not in PROCESSOR_MAPPING:
        logger.warning(
            f"Unknown category '{category}', using default processor "
            f"({DEFAULT_PROCESSOR.__name__})"
        )
    else:
        logger.debug(f"Creating {processor_class.__name__} for category '{category}'")
    
    return processor_class(gigachat_service)