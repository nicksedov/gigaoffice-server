from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class ProcessDataRequest(BaseModel):
    input_range: Optional[str] = Field(None, max_length=50)
    output_range: str = Field(..., max_length=50)
    query_text: str = Field(..., min_length=1)
    preset_prompt: Optional[str] = None
    input_data: Optional[List[Dict[str, Any]]] = None

class ProcessDataResponse(BaseModel):
    status: str
    message: str
    request_id: str
    result_data: List[List[Any]]
    processing_time: float

class PromptModel(BaseModel):
    id: str
    name: str
    description: str
    template: str
    category: str
    is_active: bool

class PromptsResponse(BaseModel):
    status: str
    prompts: List[PromptModel]
    total: int

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]

class UserInfo(BaseModel):
    user_id: str
    username: str
    email: str
    role: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserInfo

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
