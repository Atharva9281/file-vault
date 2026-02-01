"""
Document management endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from google.cloud import storage
from app.auth import get_current_user
from app.config import settings
from app.storage import document_store


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=List[dict])
async def get_documents(user_id: str = Depends(get_current_user)):
    """
    Get all documents for the current user.

    Args:
        user_id: Current authenticated user ID

    Returns:
        List of document objects
    """
    try:
        documents = document_store.get_documents_by_user(user_id)
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
        document = document_store.get_document(document_id)

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


@router.post("/sync")
async def sync_documents_from_gcs(user_id: str = Depends(get_current_user)):
    """
    Manually sync documents from GCS bucket.
    Useful if documents are missing after server restart.

    Args:
        user_id: Current authenticated user ID (for auth only)

    Returns:
        Sync status with count of documents synced
    """
    try:
        storage_client = storage.Client(project=settings.PROJECT_ID)
        synced_count = document_store.sync_from_gcs(
            storage_client,
            settings.STAGING_BUCKET,
            settings.VAULT_BUCKET
        )

        return {
            "status": "success",
            "message": f"Synced {synced_count} documents from GCS buckets (staging + vault)",
            "synced_count": synced_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync documents: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Delete a document completely (from staging, vault, database, and in-memory store).

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
        # Get document from store
        document = document_store.get_document(document_id)

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

        # Delete from database (if extraction exists)
        try:
            database_service = request.app.state.database_service
            database_service.delete_tax_extraction(document_id)
        except Exception as e:
            pass

        # Delete from in-memory document store
        document_store.delete_document(document_id)

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
