"""
GigaChat Service Factory
Enhanced factory for creating GigaChat service instances based on configuration
"""

from typing import Optional, Dict, Any
from loguru import logger

from ...core.config import get_settings
from ...utils.logger import structured_logger
from .base import BaseGigaChatService
from .dryrun import DryrunGigaChatService
from .cloud import CloudGigaChatService
from .mtls import MtlsGigaChatService


class GigaChatServiceFactory:
    """Factory for creating GigaChat service instances"""
    
    SERVICE_MODES = {
        "dryrun": DryrunGigaChatService,
        "cloud": CloudGigaChatService,
        "mtls": MtlsGigaChatService
    }
    
    @classmethod
    def create_service(cls, 
                      mode: Optional[str] = None,
                      model: Optional[str] = None,
                      **kwargs) -> BaseGigaChatService:
        """
        Create GigaChat service instance
        
        Args:
            mode: Service mode (dryrun, cloud, mtls)
            model: Model name
            **kwargs: Additional service configuration
            
        Returns:
            Configured GigaChat service instance
        """
        settings = get_settings()
        
        # Determine service mode
        run_mode = mode or settings.gigachat_run_mode
        if run_mode not in cls.SERVICE_MODES:
            logger.error(f"Unknown GigaChat mode: {run_mode}")
            raise ValueError(f"Unknown GigaChat mode: {run_mode}. Valid modes: {list(cls.SERVICE_MODES.keys())}")
        
        # Get service class
        service_class = cls.SERVICE_MODES[run_mode]
        
        # Determine model
        model_name = model or settings.gigachat_credentials or "GigaChat"
        
        logger.info(f"Creating GigaChat service: mode={run_mode}, model={model_name}")
        
        try:
            # Create service instance
            service = service_class(model=model_name, **kwargs)
            
            structured_logger.log_service_call(
                "GigaChatServiceFactory", "create_service",
                0, True,
                mode=run_mode, model=model_name
            )
            
            return service
            
        except Exception as e:
            structured_logger.log_error(e, {
                "operation": "create_service",
                "mode": run_mode,
                "model": model_name
            })
            logger.error(f"Failed to create GigaChat service: {e}")
            raise
    
    @classmethod
    def create_classifier_service(cls, **kwargs) -> BaseGigaChatService:
        """Create service optimized for classification tasks"""
        settings = get_settings()
        
        # Use lighter model for classification if available
        classify_model = getattr(settings, 'gigachat_classify_model', None) or settings.gigachat_credentials
        
        return cls.create_service(
            model=classify_model,
            **kwargs
        )
    
    @classmethod
    def create_generator_service(cls, **kwargs) -> BaseGigaChatService:
        """Create service optimized for text generation tasks"""
        settings = get_settings()
        
        # Use more powerful model for generation if available
        generate_model = getattr(settings, 'gigachat_generate_model', None) or settings.gigachat_credentials
        
        return cls.create_service(
            model=generate_model,
            **kwargs
        )
    
    @classmethod
    def get_available_modes(cls) -> list:
        """Get list of available service modes"""
        return list(cls.SERVICE_MODES.keys())
    
    @classmethod
    def validate_mode(cls, mode: str) -> bool:
        """Validate if service mode is supported"""
        return mode in cls.SERVICE_MODES


# Global service instances
_classifier_service: Optional[BaseGigaChatService] = None
_generator_service: Optional[BaseGigaChatService] = None


def get_classifier_service() -> BaseGigaChatService:
    """Get global classifier service instance (singleton)"""
    global _classifier_service
    
    if _classifier_service is None:
        _classifier_service = GigaChatServiceFactory.create_classifier_service()
        logger.info("Created global classifier service")
    
    return _classifier_service


def get_generator_service() -> BaseGigaChatService:
    """Get global generator service instance (singleton)"""
    global _generator_service
    
    if _generator_service is None:
        _generator_service = GigaChatServiceFactory.create_generator_service()
        logger.info("Created global generator service")
    
    return _generator_service


def recreate_services():
    """Recreate service instances (useful for configuration changes)"""
    global _classifier_service, _generator_service
    
    logger.info("Recreating GigaChat services...")
    
    _classifier_service = None
    _generator_service = None
    
    # Force recreation on next access
    get_classifier_service()
    get_generator_service()
    
    logger.info("GigaChat services recreated")


def get_service_health() -> Dict[str, Any]:
    """Get health status of all services"""
    try:
        classifier_health = get_classifier_service().check_service_health()
        generator_health = get_generator_service().check_service_health()
        
        return {
            "classifier": classifier_health,
            "generator": generator_health,
            "overall_status": "healthy" if all(
                service["status"] == "healthy" 
                for service in [classifier_health, generator_health]
            ) else "unhealthy"
        }
    except Exception as e:
        structured_logger.log_error(e, {"operation": "get_service_health"})
        return {
            "classifier": {"status": "error", "error": str(e)},
            "generator": {"status": "error", "error": str(e)},
            "overall_status": "error"
        }


def get_service_statistics() -> Dict[str, Any]:
    """Get usage statistics for all services"""
    try:
        classifier_stats = get_classifier_service().get_usage_statistics()
        generator_stats = get_generator_service().get_usage_statistics()
        
        return {
            "classifier": classifier_stats,
            "generator": generator_stats,
            "combined": {
                "total_requests": classifier_stats["total_requests"] + generator_stats["total_requests"],
                "total_tokens": classifier_stats["total_tokens_used"] + generator_stats["total_tokens_used"],
                "avg_success_rate": (classifier_stats["success_rate_percent"] + generator_stats["success_rate_percent"]) / 2
            }
        }
    except Exception as e:
        structured_logger.log_error(e, {"operation": "get_service_statistics"})
        return {
            "classifier": {"error": str(e)},
            "generator": {"error": str(e)},
            "combined": {"error": str(e)}
        }