"""
File Upload and Download API Router
Router for Excel file upload and download operations
"""

import time
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.api.common import ErrorResponse
from app.models.api.file import FileUploadResponse
from app.services.file_storage import file_storage_manager

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

files_router = APIRouter(prefix="/api/v1/files", tags=["File Operations"])


@files_router.post("/upload", response_model=FileUploadResponse)
@limiter.limit("30/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
):
    """Upload an Excel file to the server
    
    Accepts Excel files (.xlsx, .xls) up to 50 MB.
    Returns a unique UUID that can be used to download the file.
    
    Args:
        request: FastAPI request object (for rate limiting)
        file: Excel file to upload
        
    Returns:
        FileUploadResponse with file_id, filename, size, and upload_time
        
    Raises:
        HTTPException 400: If file validation fails
        HTTPException 413: If file is too large
        HTTPException 500: If file storage fails
    """
    start_time = time.time()
    
    try:
        # Check if file was provided
        if not file:
            logger.info("Upload request with no file")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_file_provided",
                    "message": "No file uploaded in request",
                    "details": None
                }
            )
        
        logger.info(f"File upload initiated: {file.filename}")
        
        # Save file using storage manager
        try:
            file_id, original_filename, file_size, upload_time = await file_storage_manager.save_file(file)
        except ValueError as e:
            # Validation error
            logger.info(f"File validation failed: {e}")
            
            # Check if it's a size error for 413 response
            if "exceeds maximum size" in str(e):
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "file_too_large",
                        "message": str(e),
                        "details": None
                    }
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_file",
                        "message": str(e),
                        "details": None
                    }
                )
        except RuntimeError as e:
            # Storage error
            logger.error(f"File storage failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "storage_error",
                    "message": "Failed to save file to storage",
                    "details": {"internal_error": str(e)}
                }
            )
        
        duration = time.time() - start_time
        logger.info(f"File upload completed: {file_id} in {duration:.2f}s")
        
        return FileUploadResponse(
            success=True,
            file_id=file_id,
            filename=original_filename,
            size=file_size,
            upload_time=upload_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "details": None
            }
        )


@files_router.get("/download/{file_id}")
async def download_file(file_id: str, delete_after_download: bool = False):
    """Download an Excel file by UUID
    
    Retrieves the file with the specified UUID and returns it as a download.
    Optionally deletes the file after successful download.
    
    Args:
        file_id: UUID of the file to download
        delete_after_download: If True, deletes the file from storage after download (default: False)
        
    Returns:
        FileResponse with the file content
        
    Raises:
        HTTPException 400: If file_id format is invalid
        HTTPException 404: If file not found
        HTTPException 500: If file read fails
    """
    try:
        logger.info(f"File download requested: {file_id}")
        
        # Get file information
        file_info = file_storage_manager.get_file_info(file_id)
        
        if not file_info:
            logger.info(f"File not found: {file_id}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "file_not_found",
                    "message": f"File with ID {file_id} not found",
                    "details": None
                }
            )
        
        file_path, content_type, file_size = file_info
        
        # Create file response
        logger.info(f"File download successful: {file_id} ({file_size} bytes)")
        
        response = FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=file_path.name,
            headers={
                "Content-Disposition": f'attachment; filename="{file_path.name}"'
            }
        )
        
        # Delete file after download if requested
        if delete_after_download:
            deletion_success = file_storage_manager.delete_file(file_id)
            if deletion_success:
                logger.info(f"File deleted after download: {file_id}")
            else:
                logger.error(f"Failed to delete file after download {file_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "download_error",
                "message": "Failed to read file from storage",
                "details": {"internal_error": str(e)}
            }
        )
