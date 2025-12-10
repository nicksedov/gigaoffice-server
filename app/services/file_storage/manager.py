"""File Storage Manager Service
Handles file upload, storage, and retrieval operations
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from loguru import logger
from fastapi import UploadFile


class FileStorageManager:
    """Manages file storage operations for Excel files"""
    
    def __init__(
        self,
        upload_dir: str = "./uploads/excel",
        max_file_size_mb: int = 50,
        allowed_extensions: tuple = (".xlsx", ".xls")
    ):
        """Initialize file storage manager
        
        Args:
            upload_dir: Directory path for storing uploaded files
            max_file_size_mb: Maximum file size in megabytes
            allowed_extensions: Tuple of allowed file extensions
        """
        self.upload_dir = Path(upload_dir)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.allowed_extensions = tuple(ext.lower() for ext in allowed_extensions)
        
        # Create upload directory if it doesn't exist
        self._ensure_upload_directory()
    
    def _ensure_upload_directory(self) -> None:
        """Create upload directory if it doesn't exist"""
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Upload directory ready: {self.upload_dir.absolute()}")
            
            # Test write permissions
            test_file = self.upload_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            
        except Exception as e:
            logger.error(f"Failed to initialize upload directory: {e}")
            raise RuntimeError(f"Upload directory is not accessible: {e}")
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """Validate file extension and size
        
        Args:
            filename: Name of the file to validate
            file_size: Size of the file in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            return False, f"Only Excel files ({', '.join(self.allowed_extensions)}) are accepted"
        
        # Check size
        if file_size > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            return False, f"File exceeds maximum size of {max_mb:.0f} MB"
        
        return True, None
    
    async def save_file(self, file: UploadFile) -> Tuple[str, str, int, datetime]:
        """Save uploaded file to storage
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Tuple of (file_id, original_filename, file_size, upload_time)
            
        Raises:
            ValueError: If file validation fails
            RuntimeError: If file write operation fails
        """
        # Get file metadata
        original_filename = file.filename or "unknown.xlsx"
        
        # Read file content
        try:
            content = await file.read()
            file_size = len(content)
        except Exception as e:
            logger.error(f"Failed to read uploaded file: {e}")
            raise RuntimeError(f"Failed to read uploaded file: {e}")
        
        # Validate file
        is_valid, error_message = self.validate_file(original_filename, file_size)
        if not is_valid:
            raise ValueError(error_message)
        
        # Generate UUID and construct file path
        file_id = str(uuid.uuid4())
        file_ext = Path(original_filename).suffix.lower()
        storage_filename = f"{file_id}{file_ext}"
        file_path = self.upload_dir / storage_filename
        
        # Write file to storage
        try:
            upload_time = datetime.now()
            
            # Write file atomically (write to temp file, then rename)
            temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
            temp_path.write_bytes(content)
            temp_path.replace(file_path)
            
            logger.info(f"File uploaded successfully: {file_id} ({original_filename}, {file_size} bytes)")
            
            return file_id, original_filename, file_size, upload_time
            
        except Exception as e:
            logger.error(f"Failed to save file {file_id}: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to save file to storage: {e}")
    
    def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get file path for a given file ID
        
        Args:
            file_id: UUID of the file
            
        Returns:
            Path object if file exists, None otherwise
        """
        # Validate UUID format to prevent path traversal
        try:
            uuid.UUID(file_id)
        except ValueError:
            logger.warning(f"Invalid UUID format: {file_id}")
            return None
        
        # Check both .xlsx and .xls extensions
        for ext in self.allowed_extensions:
            file_path = self.upload_dir / f"{file_id}{ext}"
            if file_path.exists() and file_path.is_file():
                return file_path
        
        return None
    
    def get_file_info(self, file_id: str) -> Optional[Tuple[Path, str, int]]:
        """Get file information including path, content type, and size
        
        Args:
            file_id: UUID of the file
            
        Returns:
            Tuple of (file_path, content_type, file_size) if file exists, None otherwise
        """
        file_path = self.get_file_path(file_id)
        if not file_path:
            return None
        
        # Determine content type based on extension
        file_ext = file_path.suffix.lower()
        content_type = self._get_content_type(file_ext)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        return file_path, content_type, file_size
    
    def _get_content_type(self, extension: str) -> str:
        """Get MIME type for file extension
        
        Args:
            extension: File extension (e.g., '.xlsx')
            
        Returns:
            MIME type string
        """
        content_types = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel"
        }
        return content_types.get(extension.lower(), "application/octet-stream")
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file from storage
        
        Args:
            file_id: UUID of the file to delete
            
        Returns:
            True if file was deleted, False if file not found
        """
        file_path = self.get_file_path(file_id)
        if not file_path:
            return False
        
        try:
            file_path.unlink()
            logger.info(f"File deleted: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False


# Create global instance with environment variable configuration
_upload_dir = os.getenv("EXCEL_UPLOAD_DIR", "./uploads/excel")
_max_file_size = int(os.getenv("EXCEL_MAX_FILE_SIZE_MB", "50"))
_allowed_extensions = os.getenv("EXCEL_ALLOWED_EXTENSIONS", ".xlsx,.xls").split(",")

file_storage_manager = FileStorageManager(
    upload_dir=_upload_dir,
    max_file_size_mb=_max_file_size,
    allowed_extensions=tuple(_allowed_extensions)
)
