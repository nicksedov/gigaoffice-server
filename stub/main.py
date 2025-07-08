from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import time
from datetime import datetime
import logging
import asyncio

from models import (
    ProcessDataRequest, ProcessDataResponse, PromptModel, PromptsResponse,
    HealthResponse, AuthResponse, ErrorResponse, UserInfo
)
from mock_data import MOCK_PROMPTS, get_mock_user, generate_request_id, get_processing_result
from config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Сервис-заглушка для тестирования GigaOffice без авторизации",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Проверка работоспособности сервиса"""
    logger.info("Health check requested")
    return HealthResponse(
        status="healthy",
        version=settings.version,
        timestamp=datetime.now(),
        services={
            "gigaoffice_stub": "healthy",
            "mock_ai": "healthy",
            "static_data": "healthy"
        }
    )

@app.get("/api/prompts/presets", response_model=PromptsResponse)
async def get_prompts(
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    active_only: bool = Query(True, description="Только активные промпты")
):
    """Получение списка предустановленных промптов"""
    logger.info(f"Prompts requested: category={category}, active_only={active_only}")
    
    prompts = MOCK_PROMPTS.copy()
    
    if active_only:
        prompts = [p for p in prompts if p["is_active"]]
    
    if category:
        prompts = [p for p in prompts if p["category"].lower() == category.lower()]
    
    prompt_models = [PromptModel(**prompt) for prompt in prompts]
    
    return PromptsResponse(
        status="success",
        prompts=prompt_models,
        total=len(prompt_models)
    )

@app.post("/api/ai/process", response_model=ProcessDataResponse)
async def process_data(request: ProcessDataRequest):
    """Основной эндпоинт для обработки данных ИИ"""
    logger.info(f"AI processing requested: query='{request.query_text[:50]}...'")
    
    # Симуляция времени обработки
    start_time = time.time()
    await asyncio.sleep(0.5)  # Имитация работы ИИ
    processing_time = time.time() - start_time
    
    # Получение мок-результата
    result_data = get_processing_result(request.query_text, request.input_data)
    
    request_id = generate_request_id()
    
    logger.info(f"AI processing completed: request_id={request_id}, rows={len(result_data)}")
    
    return ProcessDataResponse(
        status="success",
        message="Данные успешно обработаны ИИ (тестовый режим)",
        request_id=request_id,
        result_data=result_data,
        processing_time=round(processing_time, 3)
    )

@app.get("/api/prompts/{prompt_id}", response_model=PromptModel)
async def get_prompt(prompt_id: str = Path(..., description="ID промпта")):
    """Получение конкретного промпта по ID"""
    logger.info(f"Prompt requested: id={prompt_id}")
    
    prompt = next((p for p in MOCK_PROMPTS if p["id"] == prompt_id), None)
    
    if not prompt:
        raise HTTPException(
            status_code=404,
            detail=f"Промпт с ID {prompt_id} не найден"
        )
    
    return PromptModel(**prompt)

@app.post("/api/auth/token", response_model=AuthResponse)
async def mock_login(username: str = "test_user", password: str = "test_password"):
    """Мок-эндпоинт авторизации (для совместимости)"""
    logger.info(f"Mock login requested: username={username}")
    
    # В реальной системе здесь была бы проверка логина/пароля
    user_data = get_mock_user()
    
    return AuthResponse(
        access_token="mock_jwt_token_12345",
        token_type="bearer",
        expires_in=3600,
        user=UserInfo(**user_data)
    )

@app.get("/api/user/me", response_model=UserInfo)
async def get_current_user():
    """Получение информации о текущем пользователе"""
    logger.info("Current user info requested")
    
    user_data = get_mock_user()
    return UserInfo(**user_data)

@app.get("/api/requests/{request_id}")
async def get_request_status(request_id: str = Path(..., description="ID запроса")):
    """Получение статуса обработки запроса"""
    logger.info(f"Request status requested: id={request_id}")
    
    # Мок-статус для любого запроса
    return {
        "status": "completed",
        "request_id": request_id,
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "processing_time": 0.5,
        "result_ready": True
    }

@app.post("/api/ai/validate")
async def validate_query(query: str):
    """Валидация запроса к ИИ"""
    logger.info(f"Query validation requested: '{query[:50]}...'")
    
    if len(query.strip()) < 10:
        return {
            "valid": False,
            "message": "Запрос слишком короткий. Минимум 10 символов.",
            "suggestions": ["Добавьте больше деталей в запрос", "Укажите желаемый формат результата"]
        }
    
    return {
        "valid": True,
        "message": "Запрос корректен",
        "estimated_processing_time": 0.5,
        "complexity": "medium"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик ошибок"""
    logger.error(f"Global exception: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Внутренняя ошибка сервера (тестовый режим)",
            error_code="INTERNAL_ERROR",
            details={"error": str(exc)}
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    logger.info(f"Debug mode: {settings.debug}")
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
