"""
User API Models
Pydantic models for user management and authentication
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, validator

from ..db.models import UserRole


class UserCreate(BaseModel):
    """Schema for creating user"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    role: UserRole = Field(UserRole.USER, description="User role")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v and '-' not in v:
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john.doe@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe",
                "role": "user"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    daily_request_limit: Optional[int] = Field(None, ge=0, le=10000)
    monthly_token_limit: Optional[int] = Field(None, ge=0, le=1000000)


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    total_requests: int
    total_tokens_used: int
    monthly_requests: int
    monthly_tokens_used: int
    daily_request_limit: int
    monthly_token_limit: int
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "john_doe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "role": "user",
                "is_active": True,
                "created_at": "2024-08-01T10:00:00Z",
                "last_login": "2024-08-25T09:30:00Z",
                "total_requests": 150,
                "total_tokens_used": 15000,
                "monthly_requests": 45,
                "monthly_tokens_used": 4500,
                "daily_request_limit": 100,
                "monthly_token_limit": 10000
            }
        }


class UserPublic(BaseModel):
    """Schema for public user information"""
    id: int
    username: str
    full_name: Optional[str]
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(False, description="Keep user logged in")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "SecurePass123",
                "remember_me": False
            }
        }


class UserAuth(BaseModel):
    """Schema for user authentication response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": 1,
                    "username": "john_doe",
                    "role": "user"
                }
            }
        }


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class PasswordReset(BaseModel):
    """Schema for password reset"""
    email: EmailStr = Field(..., description="User email for password reset")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com"
            }
        }


class UserUsageStats(BaseModel):
    """Schema for user usage statistics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens_used: int
    avg_tokens_per_request: float
    monthly_requests: int
    monthly_tokens_used: int
    request_limit_remaining: int
    token_limit_remaining: int
    most_used_categories: List[dict]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_requests": 150,
                "successful_requests": 145,
                "failed_requests": 5,
                "total_tokens_used": 15000,
                "avg_tokens_per_request": 100.0,
                "monthly_requests": 45,
                "monthly_tokens_used": 4500,
                "request_limit_remaining": 55,
                "token_limit_remaining": 5500,
                "most_used_categories": [
                    {"category": "analysis", "count": 30},
                    {"category": "generation", "count": 15}
                ]
            }
        }


class UserPreferences(BaseModel):
    """Schema for user preferences"""
    language: str = Field("en", description="Preferred language")
    timezone: str = Field("UTC", description="User timezone")
    notifications_enabled: bool = Field(True, description="Enable notifications")
    email_notifications: bool = Field(True, description="Enable email notifications")
    default_category: Optional[str] = Field(None, description="Default request category")
    
    class Config:
        json_schema_extra = {
            "example": {
                "language": "en",
                "timezone": "Europe/Moscow",
                "notifications_enabled": True,
                "email_notifications": False,
                "default_category": "analysis"
            }
        }


class UserActivity(BaseModel):
    """Schema for user activity tracking"""
    action: str = Field(..., description="Action performed")
    resource: Optional[str] = Field(None, description="Resource accessed")
    timestamp: datetime = Field(..., description="When action occurred")
    ip_address: Optional[str] = Field(None, description="User IP address")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")
    
    class Config:
        from_attributes = True


class UsersListResponse(BaseModel):
    """Schema for users list response"""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    total_pages: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": 1,
                        "username": "john_doe",
                        "email": "john.doe@example.com",
                        "role": "user",
                        "is_active": True,
                        "total_requests": 150
                    }
                ],
                "total": 100,
                "page": 1,
                "size": 20,
                "total_pages": 5
            }
        }