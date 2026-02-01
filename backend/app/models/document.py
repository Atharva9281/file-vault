"""
Document data models and schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """
    Enumeration of possible document statuses in the vault workflow.
    """
    UPLOADED = "uploaded"
    REDACTING = "redacting"
    REDACTED = "redacted"
    APPROVED = "approved"
    REJECTED = "rejected"


class Document(BaseModel):
    """
    Document model representing a file in the vault system.

    Attributes:
        id: Unique identifier for the document
        user_id: ID of the user who uploaded the document
        filename: Original filename of the uploaded document
        status: Current status of the document in the workflow
        created_at: Timestamp when the document was created
        updated_at: Timestamp when the document was last updated
    """
    id: str = Field(..., description="Unique document identifier")
    user_id: str = Field(..., description="User who uploaded the document")
    filename: str = Field(..., description="Original filename")
    status: DocumentStatus = Field(
        default=DocumentStatus.UPLOADED,
        description="Current document status"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
