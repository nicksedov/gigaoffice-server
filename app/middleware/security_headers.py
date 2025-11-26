"""
Security Headers Middleware
Adds security-related HTTP headers to all API responses
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.
    
    Headers added:
    - X-Robots-Tag: Instructs search engines not to index, follow links, 
      cache, or show snippets
    - X-Content-Type-Options: Prevents MIME-type sniffing
    - X-Frame-Options: Prevents clickjacking by blocking iframe embedding
    - Referrer-Policy: Prevents referrer information leakage
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and add security headers to the response.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler in the chain
            
        Returns:
            Response with security headers added
        """
        # Process the request and get the response
        response: Response = await call_next(request)
        
        # Add security headers
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        
        return response
