"""
GigaChat Factory
Фабрика для создания экземпляров GigaChat сервисов в зависимости от режима работы
"""

import os
from loguru import logger
from app.services.gigachat.dryrun import DryRunGigaChatService
from app.services.gigachat.cloud import CloudGigaChatService
from app.services.gigachat.mtls import MtlsGigaChatService

SERVICE_MODES = {
    "dryrun": DryRunGigaChatService,
    "cloud": CloudGigaChatService,
    "mtls": MtlsGigaChatService
}

def create_gigachat_service(prompt_builder, model_env_var, service_description):
    """
    Возвращает экземпляр GigaChat-сервиса, использующий указанную модель
    """
    run_mode = os.getenv("GIGACHAT_RUN_MODE", "dryrun").lower()
    model_name = os.getenv(model_env_var, "GigaChat")
    logger.info(f"Initializing {service_description} with model={model_name}")

    service_class = SERVICE_MODES.get(run_mode)
    if not service_class:
        logger.error(f"Unknown GIGACHAT_RUN_MODE: {run_mode}")
        raise ValueError(f"Unknown GIGACHAT_RUN_MODE: {run_mode}. Valid values: dryrun, cloud, mtls")

    # Передаем имя модели через конструктор
    return service_class(prompt_builder, model=model_name)