"""Health API Models"""

from typing import Optional
from pydantic import BaseModel

class PingResponse(BaseModel):
    """Response model for ping endpoint"""
    status: str