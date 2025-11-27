"""
Histogram API Dependencies
Shared dependencies for histogram endpoints
"""

from typing import Dict, Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.fastapi_config import security

# Rate limiting
limiter = Limiter(key_func=get_remote_address)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict]:
    """
    Get current user from token (simplified implementation)
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User dictionary with id, username, and role, or None if not authenticated
    """
    if not credentials:
        return None
    return {"id": 1, "username": "demo_user", "role": "user"}
