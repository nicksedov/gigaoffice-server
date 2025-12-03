"""
Spreadsheet Data Search
Search operations for spreadsheet data using vector embeddings or lemmatization
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from loguru import logger

from app.models.api.spreadsheet import SpreadsheetSearchRequest, SearchResult, SearchResultItem
from app.services.database.session import get_db
from app.services.database.vector_search import header_vector_search
from .dependencies import get_current_user, limiter


# Create router for search endpoints
search_router = APIRouter()


@search_router.post("/data/search", response_model=List[SearchResult])
@limiter.limit("30/minute")
async def search_spreadsheet_data(
    request: Request,
    search_request: SpreadsheetSearchRequest,
    domain: str = Query(..., description="Domain area for search. Currently only supports 'header'"),
    limit: int = Query(..., description="Number of most relevant results to return per search string"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search spreadsheet data using vector embeddings or fast lemmatization matching
    
    Args:
        request: FastAPI request object (for rate limiting)
        search_request: Search request with data to search for
        domain: Domain area for search (currently only 'header')
        limit: Number of results to return per search string
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        List of search results with matched items and scores
        
    Raises:
        HTTPException: 400 for invalid parameters, 500 for server errors
    """
    try:
        # Validate domain parameter
        if domain != "header":
            raise HTTPException(
                status_code=400, 
                detail="Invalid domain parameter. Only 'header' is supported."
            )
        
        # Validate limit parameter
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400, 
                detail="Limit must be between 1 and 100"
            )
        
        # Prepare search strings
        search_strings = search_request.data if isinstance(search_request.data, list) else [search_request.data]
        
        # Collect all results
        all_results = []
        
        # Search for each string using the specified mode
        for search_string in search_strings:
            # Perform search using the unified search method
            results = header_vector_search.search(
                search_string, 
                limit
            )
            
            item_search_results = []
            # Convert to SearchResultItem objects
            for header, score in results:
                item_search_results.append(SearchResultItem(
                    text=header,
                    score=score
                ))
            
            search_result = SearchResult(
                search_text=search_string, 
                search_results=item_search_results
            )
            all_results.append(search_result)   
        
        return all_results
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching spreadsheet data: {e}")
        raise HTTPException(status_code=500, detail="Error searching spreadsheet data")
