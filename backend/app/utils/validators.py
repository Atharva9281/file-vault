"""
File validation utilities.
"""

from typing import Tuple
from fastapi import UploadFile, HTTPException, status


# Allowed file types for upload
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff"
}

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_file_extension(filename: str) -> bool:
    """
    Validate that a filename has an allowed extension.

    Args:
        filename: Name of the file to validate

    Returns:
        True if extension is allowed, False otherwise
    """
    import os
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def validate_mime_type(content_type: str) -> bool:
    """
    Validate that a MIME type is allowed.

    Args:
        content_type: MIME type to validate

    Returns:
        True if MIME type is allowed, False otherwise
    """
    return content_type in ALLOWED_MIME_TYPES


def validate_file_size(file_size: int) -> bool:
    """
    Validate that a file size is within limits.

    Args:
        file_size: Size of the file in bytes

    Returns:
        True if size is within limits, False otherwise
    """
    return 0 < file_size <= MAX_FILE_SIZE


async def validate_upload_file(file: UploadFile) -> Tuple[bool, str]:
    """
    Validate an uploaded file.

    Args:
        file: FastAPI UploadFile object

    Returns:
        Tuple of (is_valid, error_message)

    Raises:
        HTTPException: If file validation fails
    """
    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )

    # Validate file extension
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Validate MIME type
    if file.content_type and not validate_mime_type(file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if not validate_file_size(file_size):
        max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_size_mb}MB"
        )

    return True, "File is valid"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import os
    import re

    # Get just the basename (remove any path components)
    filename = os.path.basename(filename)

    # Remove any characters that aren't alphanumeric, dash, underscore, or dot
    filename = re.sub(r'[^\w\-.]', '_', filename)

    # Ensure filename isn't empty after sanitization
    if not filename or filename == '.':
        filename = "unnamed_file"

    return filename
