"""Optimization Info API Model"""

from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class OptimizationInfo(BaseModel):
    """Информация об оптимизации входных данных для LLM"""
    
    id: str = Field(..., description="Optimization record ID")
    original_size_bytes: int = Field(..., description="Size before optimization in bytes")
    optimized_size_bytes: int = Field(..., description="Size after optimization in bytes")
    reduction_percentage: float = Field(..., description="Percentage of size reduction")
    optimizations_applied: List[Dict[str, Any]] = Field(..., description="List of optimization operations")
    created_at: datetime = Field(..., description="When optimization was performed")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "original_size_bytes": 150000,
                "optimized_size_bytes": 45000,
                "reduction_percentage": 70.0,
                "optimizations_applied": [
                    {
                        "type": "filter_by_requirements",
                        "details": {
                            "needs_column_headers": True,
                            "needs_header_styles": False,
                            "needs_cell_values": True,
                            "needs_cell_styles": False,
                            "needs_column_metadata": False
                        }
                    }
                ],
                "created_at": "2025-11-29T10:30:00Z"
            }
        }
