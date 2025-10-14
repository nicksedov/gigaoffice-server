"""
Shared Processing Logic for Chart and Spreadsheet Processors
Common functionality for prompt preparation, token counting, rate limiting, and metadata creation
"""

from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from loguru import logger
from app.services.gigachat.base import BaseGigaChatService


def check_rate_limit(gigachat_service: BaseGigaChatService) -> bool:
    """
    Verify request rate limits are not exceeded
    
    Args:
        gigachat_service: Instance of GigaChat service
        
    Returns:
        bool: True if rate limit is OK, False if exceeded
    """
    return gigachat_service._check_rate_limit()


def prepare_prompts(
    query: str,
    category: str,
    data: Dict[str, Any],
    gigachat_service: BaseGigaChatService
) -> Tuple[str, str]:
    """
    Generate system and user prompts using prompt builder
    
    Args:
        query: User instruction for processing
        category: Category type (e.g., data-chart, spreadsheet-analysis)
        data: Input data for processing
        gigachat_service: Instance of GigaChat service
        
    Returns:
        Tuple[str, str]: (system_prompt, user_prompt)
    """
    system_prompt = gigachat_service.prompt_builder.prepare_system_prompt(category)
    user_prompt = gigachat_service.prompt_builder.prepare_user_prompt(query, data)
    
    return system_prompt, user_prompt


def count_tokens(
    system_prompt: str,
    user_prompt: str,
    gigachat_service: BaseGigaChatService
) -> int:
    """
    Calculate total token count for request
    
    Args:
        system_prompt: System prompt text
        user_prompt: User prompt text
        gigachat_service: Instance of GigaChat service
        
    Returns:
        int: Total token count
    """
    return gigachat_service._count_tokens(system_prompt + user_prompt)


def validate_token_limit(
    token_count: int,
    gigachat_service: BaseGigaChatService
) -> None:
    """
    Raise exception if token limit exceeded
    
    Args:
        token_count: Number of tokens to validate
        gigachat_service: Instance of GigaChat service
        
    Raises:
        Exception: If token limit is exceeded
    """
    if token_count > gigachat_service.max_tokens_per_request:
        raise Exception(
            f"Input too long: {token_count} tokens "
            f"(max: {gigachat_service.max_tokens_per_request})"
        )


def add_request_time(gigachat_service: BaseGigaChatService) -> None:
    """
    Record request timestamp for rate limiting
    
    Args:
        gigachat_service: Instance of GigaChat service
    """
    gigachat_service._add_request_time()


def create_metadata(
    processing_time: float,
    input_tokens: int,
    output_tokens: int,
    model: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Construct response metadata dictionary
    
    Args:
        processing_time: Time taken to process request in seconds
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model identifier used for processing
        request_id: Optional request ID from GigaChat response
        
    Returns:
        Dict[str, Any]: Metadata dictionary with processing information
    """
    total_tokens = input_tokens + output_tokens
    
    return {
        "processing_time": processing_time,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "success": True
    }
