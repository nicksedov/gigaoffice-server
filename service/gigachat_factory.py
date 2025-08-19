"""
GigaChat Factory
Фабрика для создания экземпляров GigaChat сервисов в зависимости от режима работы
"""

import os
from loguru import logger
from gigachat_prompt_builder import prompt_builder
from gigachat_service_dryrun import DryRunGigaChatService
from gigachat_service_cloud import CloudGigaChatService
from gigachat_service_mtls import MtlsGigaChatService

SERVICE_MODES = {
    "dryrun": DryRunGigaChatService,
    "cloud": CloudGigaChatService,
    "mtls": MtlsGigaChatService
}

def create_gigachat_service():
    """
    Фабричная функция для создания экземпляра GigaChat сервиса
    на основе переменной окружения GIGACHAT_RUN_MODE
    """
    run_mode = os.getenv("GIGACHAT_RUN_MODE", "dryrun").lower()
    logger.info(f"Creating GigaChat service in {run_mode} mode")
    
    service_class = SERVICE_MODES.get(run_mode)
    if not service_class:
        logger.error(f"Unknown GIGACHAT_RUN_MODE: {run_mode}")
        raise ValueError(f"Unknown GIGACHAT_RUN_MODE: {run_mode}. Valid values: dryrun, cloud, mtls")
    return service_class(prompt_builder)    

# Создаем глобальный экземпляр сервиса
gigachat_service = create_gigachat_service()

