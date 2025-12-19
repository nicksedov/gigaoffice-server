"""File Operation API Models"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response model for successful file upload"""
    success: bool = Field(True, description="Always true for successful upload")
    file_id: str = Field(..., description="Generated UUID identifier")
    original_filename: str = Field(..., description="Original uploaded filename")
    assigned_filename = Field(..., description="The filename assigned by the backend")
    size: int = Field(..., description="File size in bytes", ge=0)
    upload_time: datetime = Field(..., description="ISO 8601 timestamp of upload")


class FileDownloadInfo(BaseModel):
    """Information about a file for download"""
    file_id: str = Field(..., description="UUID of the file")
    filename: str = Field(..., description="Filename with extension")
    size: int = Field(..., description="File size in bytes", ge=0)
    content_type: str = Field(..., description="MIME type of the file")
