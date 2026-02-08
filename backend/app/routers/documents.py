"""
Document management endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from google.cloud import storage
from app.auth import get_current_user
from app.config import settings


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=List[dict])
async def get_documents(request: Request, user_id: str = Depends(get_current_user)):
    """
    Get all documents for the current user.

    Args:
        request: FastAPI request object
        user_id: Current authenticated user ID

    Returns:
        List of document objects
    """
    try:
        database_service = request.app.state.database_service
        documents = database_service.get_documents_by_user_dict(user_id)
        return documents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Get a specific document by ID.

    Args:
        document_id: Document identifier
        request: FastAPI request object
        user_id: Current authenticated user ID

    Returns:
        Document object

    Raises:
        HTTPException: If document not found or unauthorized
    """
    try:
        database_service = request.app.state.database_service
        document = database_service.get_document_dict(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        # Check if user owns this document
        if document["user_id"] != user_id:
            # Log unauthorized access attempt
            audit_logger = request.app.state.audit_logger
            audit_logger.log_unauthorized_access(
                user_id=user_id,
                document_id=document_id,
                reason=f"User attempted to access another user's document (owner: {document['user_id']})",
                ip_address=request.client.host if request.client else None
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this document"
            )

        return document

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Delete a document completely (from staging, vault, and database).

    Args:
        document_id: Document identifier
        request: FastAPI request object (to access app state)
        user_id: Current authenticated user ID

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If document not found or unauthorized
    """
    try:
        # Get document from database
        database_service = request.app.state.database_service
        document = database_service.get_document_dict(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        # Check if user owns this document
        if document["user_id"] != user_id:
            # Log unauthorized access attempt
            audit_logger = request.app.state.audit_logger
            audit_logger.log_unauthorized_access(
                user_id=user_id,
                document_id=document_id,
                reason=f"User attempted to delete another user's document (owner: {document['user_id']})",
                ip_address=request.client.host if request.client else None
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this document"
            )

        storage_client = storage.Client(project=settings.PROJECT_ID)
        deleted_files = []

        # Delete from staging bucket (original and redacted)
        if document.get("gcs_path"):
            try:
                gcs_path = document["gcs_path"]
                if gcs_path.startswith("gs://"):
                    path_parts = gcs_path.replace("gs://", "").split("/", 1)
                    bucket_name = path_parts[0]
                    blob_path = path_parts[1]

                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_path)
                    blob.delete()
                    deleted_files.append(gcs_path)
            except Exception as e:
                pass

        if document.get("redacted_path"):
            try:
                redacted_path = document["redacted_path"]
                if redacted_path.startswith("gs://"):
                    path_parts = redacted_path.replace("gs://", "").split("/", 1)
                    bucket_name = path_parts[0]
                    blob_path = path_parts[1]

                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_path)
                    blob.delete()
                    deleted_files.append(redacted_path)
            except Exception as e:
                pass

        # Delete from vault bucket
        if document.get("vault_path"):
            try:
                vault_path = document["vault_path"]
                if vault_path.startswith("gs://"):
                    path_parts = vault_path.replace("gs://", "").split("/", 1)
                    bucket_name = path_parts[0]
                    blob_path = path_parts[1]

                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_path)
                    blob.delete()
                    deleted_files.append(vault_path)
            except Exception as e:
                pass

        # Delete tax extraction from database (if exists)
        try:
            database_service.delete_tax_extraction(document_id)
        except Exception as e:
            pass

        # Delete document from database
        database_service.delete_document(document_id)

        return {
            "status": "success",
            "message": f"Document {document_id} deleted successfully",
            "document_id": document_id,
            "deleted_files": deleted_files
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )
