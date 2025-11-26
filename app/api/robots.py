"""
Robots.txt Endpoint
Provides robot exclusion directives for search engines and web crawlers
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

robots_router = APIRouter(tags=["Security"])

@robots_router.get("/robots.txt", response_class=PlainTextResponse)
async def get_robots_txt():
    """
    Serve robots.txt file to instruct search engines and crawlers.
    
    Returns standard robot exclusion protocol directives that:
    - Disallow all crawlers from accessing any part of the service
    - Indicate this is a private API service
    
    This endpoint is publicly accessible without authentication.
    """
    content = """User-agent: *
Disallow: /

# GigaOffice AI Service - Private API
# This is a private API service and should not be crawled"""
    
    return PlainTextResponse(
        content=content,
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
        }
    )
