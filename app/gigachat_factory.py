"""
GigaChat Factory
Фабрика для создания экземпляров GigaChat сервисов в зависимости от режима работы
"""

import os
from loguru import logger
from app.gigachat_prompt_builder import prompt_builder
from app.gigachat_service_dryrun import DryRunGigaChatService
from app.gigachat_service_cloud import CloudGigaChatService
from app.gigachat_service_mtls import MtlsGigaChatService

SERVICE_MODES = {
    "dryrun": DryRunGigaChatService,
    "cloud": CloudGigaChatService,
    "mtls": MtlsGigaChatService
}

def create_gigachat_service(model_env_var):
    """
    Возвращает экземпляр GigaChat-сервиса, использующий указанную модель
    """
    run_mode = os.getenv("GIGACHAT_RUN_MODE", "dryrun").lower()
    model_name = os.getenv(model_env_var, "GigaChat")
    logger.info(f"Creating GigaChat service in {run_mode} mode with model={model_name}")

    service_class = SERVICE_MODES.get(run_mode)
    if not service_class:
        logger.error(f"Unknown GIGACHAT_RUN_MODE: {run_mode}")
        raise ValueError(f"Unknown GIGACHAT_RUN_MODE: {run_mode}. Valid values: dryrun, cloud, mtls")

    # Передаем имя модели через конструктор
    return service_class(prompt_builder, model=model_name)

# Создаем два глобальных экземпляра
gigachat_classify_service = create_gigachat_service("GIGACHAT_CLASSIFY_MODEL")
gigachat_generate_service = create_gigachat_service("GIGACHAT_GENERATE_MODEL")
