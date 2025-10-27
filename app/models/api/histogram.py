"""
Histogram Analysis API Data Models
Pydantic models for histogram generation with statistical metadata support
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class HistogramResponse(BaseModel):
    """AI-generated histogram configuration recommendations
    
    Contains recommendations for creating histogram visualizations from
    spreadsheet data with numerical columns.
    
    Example:
    ```json
    {
        "source_columns": [1, 2],
        "recommended_bins": 10,
        "range_column_name": "Диапазон температур (°C)",
        "count_column_name": "Количество измерений"
    }
    ```
    """
    source_columns: List[int] = Field(
        ..., 
        description="Indices of columns containing numerical values for histogram"
    )
    recommended_bins: int = Field(
        ..., 
        description="Recommended number of histogram bins based on data characteristics",
        ge=1,
        le=100
    )
    range_column_name: str = Field(
        ..., 
        description="Suggested name for the bin range column (in Russian)"
    )
    count_column_name: str = Field(
        ..., 
        description="Suggested name for the frequency count column (in Russian)"
    )
    
    @field_validator('source_columns')
    @classmethod
    def validate_source_columns(cls, v):
        """Validate that source_columns is not empty and contains valid indices"""
        if not v:
            raise ValueError('source_columns must contain at least one column index')
        if any(idx < 0 for idx in v):
            raise ValueError('Column indices must be non-negative')
        return v
    
    @field_validator('recommended_bins')
    @classmethod
    def validate_bins(cls, v):
        """Validate bin count is in practical range"""
        if v < 5 or v > 20:
            # Log warning but don't fail - GigaChat might have good reasons
            pass
        return v


class HistogramRequest(BaseModel):
    """Request model for histogram analysis
    
    Extends the existing SpreadsheetRequest structure but expects spreadsheet_data
    to contain columns with statistical metadata (min, max, median, count).
    """
    spreadsheet_data: dict = Field(
        ..., 
        description="Enhanced spreadsheet data with statistical metadata"
    )
    query_text: str = Field(
        ..., 
        description="Natural language description of the histogram task"
    )
    category: str = Field(
        default="data-histogram", 
        description="Request category (defaults to 'data-histogram')"
    )


class HistogramProcessResponse(BaseModel):
    """Response model for histogram analysis request initiation
    
    Returned when a histogram analysis request is submitted to the processing queue.
    
    Example:
    ```json
    {
        "success": true,
        "request_id": "a3f2b1c0-4d5e-6f7g-8h9i-0j1k2l3m4n5o",
        "status": "queued",
        "message": "Histogram analysis request queued for processing",
        "error_message": null
    }
    ```
    """
    success: bool = Field(
        ..., 
        description="Indicates if request was successfully queued"
    )
    request_id: str = Field(
        ..., 
        description="UUID for tracking this request"
    )
    status: str = Field(
        ..., 
        description="Current status: 'queued', 'processing', 'completed', 'failed'"
    )
    message: str = Field(
        ..., 
        description="Human-readable status message"
    )
    error_message: Optional[str] = Field(
        None, 
        description="Error details if status is 'failed'"
    )
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status against valid values"""
        valid_statuses = ['queued', 'processing', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v


class HistogramStatusResponse(BaseModel):
    """Response model for histogram analysis status polling
    
    Returned when checking the status of a histogram analysis request.
    
    Example:
    ```json
    {
        "success": true,
        "request_id": "a3f2b1c0-4d5e-6f7g-8h9i-0j1k2l3m4n5o",
        "status": "processing",
        "message": "Histogram analysis in progress",
        "error_message": null
    }
    ```
    """
    success: bool = Field(
        ..., 
        description="True if request exists and is processing/completed"
    )
    request_id: str = Field(
        ..., 
        description="The request UUID"
    )
    status: str = Field(
        ..., 
        description="Current status: 'pending', 'processing', 'completed', 'failed'"
    )
    message: str = Field(
        ..., 
        description="Status-specific message"
    )
    error_message: Optional[str] = Field(
        None, 
        description="Error details if status is 'failed'"
    )
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status against valid values"""
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v


class HistogramResultResponse(BaseModel):
    """Response model for histogram analysis result retrieval
    
    Returned when retrieving the completed histogram configuration.
    
    Example (completed):
    ```json
    {
        "success": true,
        "status": "completed",
        "message": "Histogram analysis completed successfully",
        "histogram_config": {
            "source_columns": [2, 3],
            "recommended_bins": 8,
            "range_column_name": "Диапазон значений",
            "count_column_name": "Количество элементов"
        },
        "tokens_used": 523,
        "processing_time": 2.14
    }
    ```
    
    Example (in progress):
    ```json
    {
        "success": false,
        "status": "processing",
        "message": "Histogram analysis is still in progress",
        "histogram_config": null,
        "tokens_used": null,
        "processing_time": null
    }
    ```
    """
    success: bool = Field(
        ..., 
        description="True if result is available"
    )
    status: str = Field(
        ..., 
        description="Current request status"
    )
    message: str = Field(
        ..., 
        description="Human-readable message"
    )
    histogram_config: Optional[HistogramResponse] = Field(
        None, 
        description="Generated histogram configuration (when completed)"
    )
    tokens_used: Optional[int] = Field(
        None, 
        description="Number of GigaChat tokens consumed",
        ge=0
    )
    processing_time: Optional[float] = Field(
        None, 
        description="Processing duration in seconds",
        ge=0.0
    )
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status against valid values"""
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v
