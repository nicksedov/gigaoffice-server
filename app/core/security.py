"""
Security Module
Authentication, authorization, and security utilities
"""

import time
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address
from loguru import logger

from .config import get_settings


class SecurityManager:
    """Centralized security management"""
    
    def __init__(self):
        self.settings = get_settings()
        self.bearer_scheme = HTTPBearer(auto_error=False)
        self.limiter = Limiter(key_func=get_remote_address)
    
    def verify_api_key(self, credentials: Optional[HTTPAuthorizationCredentials]) -> bool:
        """
        Verify API key from Bearer token
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            True if valid, False otherwise
        """
        if not credentials:
            return False
        
        # In production, implement proper API key validation
        # For now, accept any non-empty token
        return bool(credentials.credentials)
    
    def get_rate_limit_key(self, request) -> str:
        """
        Get rate limiting key for request
        
        Args:
            request: FastAPI request object
            
        Returns:
            Rate limiting key
        """
        # Use IP address as default key
        client_ip = get_remote_address(request)
        
        # If authenticated, use user-specific key
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            return f"user:{token}"
        
        return f"ip:{client_ip}"
    
    def create_audit_log(self, action: str, user_id: Optional[str] = None, 
                        resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Create audit log entry
        
        Args:
            action: Action performed
            user_id: User identifier
            resource: Resource accessed
            details: Additional details
        """
        log_entry = {
            "timestamp": time.time(),
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "details": details or {}
        }
        
        logger.info(f"AUDIT: {log_entry}")
    
    def validate_input(self, data: str, max_length: int = 10000) -> str:
        """
        Validate and sanitize input data
        
        Args:
            data: Input data to validate
            max_length: Maximum allowed length
            
        Returns:
            Sanitized data
            
        Raises:
            HTTPException: If validation fails
        """
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input data cannot be empty"
            )
        
        if len(data) > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input data too long (max {max_length} characters)"
            )
        
        # Basic sanitization - remove potential script tags
        sanitized = data.replace("<script>", "").replace("</script>", "")
        
        return sanitized.strip()
    
    def check_permissions(self, user_id: str, action: str, resource: str) -> bool:
        """
        Check if user has permission for action on resource
        
        Args:
            user_id: User identifier
            action: Action to perform
            resource: Resource to access
            
        Returns:
            True if allowed, False otherwise
        """
        # Basic permission check - in production implement proper RBAC
        return True
    
    def get_client_info(self, request) -> Dict[str, Any]:
        """
        Extract client information from request
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client information dictionary
        """
        return {
            "ip": get_remote_address(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "host": request.headers.get("Host", ""),
            "referer": request.headers.get("Referer", ""),
            "timestamp": time.time()
        }


# Dependency functions for FastAPI
security_manager = SecurityManager()


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security_manager.bearer_scheme)) -> Optional[str]:
    """
    FastAPI dependency to get current authenticated user
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User identifier if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    if not security_manager.verify_api_key(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In production, decode JWT token to get user ID
    # For now, return token as user ID
    return credentials.credentials


def require_auth(credentials: HTTPAuthorizationCredentials = Security(security_manager.bearer_scheme)) -> str:
    """
    FastAPI dependency that requires authentication
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User identifier
        
    Raises:
        HTTPException: If not authenticated
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not security_manager.verify_api_key(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


def check_rate_limit(request):
    """Rate limiting check for endpoints"""
    try:
        # This will be used with @limiter.limit() decorator
        pass
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )