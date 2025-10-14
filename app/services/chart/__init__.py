"""
Chart Processing Service
Service for processing chart generation requests with GigaChat AI
"""

from app.services.chart.processor import ChartProcessorService
from app.services.gigachat.base import BaseGigaChatService

def create_chart_processor(gigachat_service: BaseGigaChatService) -> ChartProcessorService:
    """
    Create a chart processor with the given GigaChat service.
    
    This factory function is used in fastapi_config.py to create the chart processor
    that is used by the Kafka message handler to process chart generation requests.
    
    Args:
        gigachat_service: An instance of a GigaChat service (cloud, mtls, or dryrun)
        
    Returns:
        ChartProcessorService: An instance of the chart processor service
    """
    return ChartProcessorService(gigachat_service)

__all__ = ['ChartProcessorService', 'create_chart_processor']
