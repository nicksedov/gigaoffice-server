"""
Histogram Processing Service
Service for processing histogram analysis requests with GigaChat AI
"""

from app.services.histogram.processor import HistogramProcessorService
from app.services.gigachat.base import BaseGigaChatService

def create_histogram_processor(gigachat_service: BaseGigaChatService) -> HistogramProcessorService:
    """
    Create a histogram processor with the given GigaChat service.
    
    This factory function is used in fastapi_config.py to create the histogram processor
    that is used by the Kafka message handler to process histogram analysis requests.
    
    Args:
        gigachat_service: An instance of a GigaChat service (cloud, mtls, or dryrun)
        
    Returns:
        HistogramProcessorService: An instance of the histogram processor service
    """
    return HistogramProcessorService(gigachat_service)

__all__ = ['HistogramProcessorService', 'create_histogram_processor']
