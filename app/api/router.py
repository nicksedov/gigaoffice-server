"""
Main API Router
Aggregates all domain-specific endpoint routers
"""

from fastapi import APIRouter
from app.api.endpoints import health, ai, prompts, metrics

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router)
api_router.include_router(ai.router)
api_router.include_router(prompts.router)
api_router.include_router(metrics.router)

# Optional: Add middleware or global dependencies here if needed
# api_router.middleware("http")(some_middleware)

__all__ = ["api_router"]