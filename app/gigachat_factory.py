"""
GigaChat Factory
Фабрика для создания экземпляров GigaChat сервисов в зависимости от режима работы
"""

import os
from loguru import logger
from app.services.gigachat.prompt_builder import prompt_builder
from app.services.gigachat.factory import create_gigachat_services

# Create both services
gigachat_classify_service, gigachat_generate_service = create_gigachat_services(prompt_builder)
