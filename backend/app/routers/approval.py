"""
Document approval and preview endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel
from app.auth import get_current_user
from datetime import datetime


router = APIRouter(prefix="/approval", tags=["approval"])


class ApprovalRequest(BaseModel):
    """Request model for document approval/rejection."""
    document_id: str
    reason: str = None


@router.get("/preview/{document_id}")
async def preview_document(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Preview a redacted document before approval.

    Args:
        document_id: ID of the document to preview
        request: FastAPI request object (to access app state)
        user_id: Current authenticated user ID

    Returns:
        Dictionary containing document metadata and preview URL

    Raises:
        HTTPException: If document not found or user not authorized
    """
    try:
        from app.storage import document_store

        # Get document from store
        document = document_store.get_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Verify document belongs to user
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

        # Verify document has been redacted
        if document["status"] not in ["redacted", "approved"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document not ready for preview. Current status: {document['status']}"
            )

        # Check if redacted file exists
        if not document.get("redacted_path"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redacted file not found"
            )

        # Parse GCS path
        gcs_path = document["redacted_path"]
        if not gcs_path.startswith("gs://"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid GCS path format"
            )

        path_parts = gcs_path.replace("gs://", "").split("/", 1)
        bucket_name = path_parts[0]
        blob_path = path_parts[1]

        # Get storage service from app state
        storage_service = request.app.state.storage_service

        # Generate signed URL for redacted file
        signed_url = storage_service.generate_signed_url(
            bucket_name,
            blob_path,
            expiration_minutes=15
        )

        # Log preview access
        audit_logger = request.app.state.audit_logger
        audit_logger.log_document_previewed(
            user_id=user_id,
            document_id=document_id,
            filename=document["filename"],
            redacted_path=gcs_path,
            ip_address=request.client.host if request.client else None
        )

        return {
            "document_id": document_id,
            "signed_url": signed_url,
            "expires_in_minutes": 15,
            "document": {
                "id": document["id"],
                "filename": document["filename"],
                "status": document["status"],
                "created_at": document["created_at"],
                "pii_count": document.get("pii_count", 0)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )


@router.post("/approve/{document_id}", status_code=status.HTTP_200_OK)
async def approve_document(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Approve a redacted document:
    1. Move redacted file from staging to vault
    2. Delete original file from staging
    3. Update document status to 'approved'
    4. Trigger field extraction in background

    Args:
        document_id: Document identifier
        request: FastAPI request object
        background_tasks: FastAPI background tasks
        user_id: Current authenticated user ID

    Returns:
        Dictionary containing approval status

    Raises:
        HTTPException: If document not found or user not authorized
    """
    try:
        from app.storage import document_store
        from app.config import settings
        from datetime import datetime

        # Get document
        document = document_store.get_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Verify document belongs to user
        if document["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to approve this document"
            )

        # Verify document is redacted
        if document["status"] != "redacted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document must be redacted before approval. Current status: {document['status']}"
            )

        # Check redacted file exists
        if not document.get("redacted_path"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redacted file not found"
            )

        # Get storage service
        storage_service = request.app.state.storage_service

        # Parse paths
        redacted_path = document["redacted_path"]
        original_path = document["gcs_path"]
        original_filename = document["filename"]

        # Generate vault path (preserve original filename for recovery after restart)
        vault_path = f"gs://{settings.VAULT_BUCKET}/users/{user_id}/documents/{document_id}_redacted_{original_filename}"

        # Move redacted file to vault (this does copy + delete)
        storage_service.move_file(redacted_path, vault_path)

        # Delete original file from staging
        storage_service.delete_file(original_path)

        # Verify cleanup
        original_still_exists = storage_service.file_exists(original_path)
        redacted_still_exists = storage_service.file_exists(redacted_path)
        vault_exists = storage_service.file_exists(vault_path)

        warnings = []
        if original_still_exists or redacted_still_exists:
            if original_still_exists:
                warnings.append("Original file still in staging")
            if redacted_still_exists:
                warnings.append("Redacted file still in staging")

        if not vault_exists:
            warning = "Vault file not found!"
            warnings.append(warning)

        # Update document
        document_store.update_document(document_id, {
            "status": "approved",
            "vault_path": vault_path,
            "approved_at": datetime.utcnow().isoformat(),
            "gcs_path": None,  # Original deleted
            "redacted_path": None,  # Moved to vault
            "extraction_status": "not_started",  # Initialize extraction status
        })

        # Log approval
        audit_logger = request.app.state.audit_logger
        audit_logger.log_document_approved(
            user_id=user_id,
            document_id=document_id,
            vault_path=vault_path,
            ip_address=request.client.host if request.client else None
        )

        # Log file operations
        audit_logger.log_file_moved(
            user_id=user_id,
            document_id=document_id,
            source_path=redacted_path,
            destination_path=vault_path,
            operation="move_to_vault"
        )

        audit_logger.log_file_deleted(
            user_id=user_id,
            document_id=document_id,
            file_path=original_path,
            file_type="original",
            reason="approved"
        )

        # Trigger extraction in background
        background_tasks.add_task(
            extract_and_store_fields,
            document_id,
            vault_path,
            user_id,
            request.app.state.extraction_service,
            request.app.state.database_service,
            audit_logger
        )

        result = {
            "success": True,
            "message": "Document approved successfully. Field extraction in progress.",
            "document_id": document_id,
            "vault_path": vault_path,
            "status": "approved"
        }

        if warnings:
            result["warnings"] = warnings

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve document: {str(e)}"
        )


async def extract_and_store_fields(
    doc_id: str,
    vault_path: str,
    user_id: str,
    extraction_service,
    database_service,
    audit_logger=None
):
    """
    Background task to extract fields and store in database.

    Args:
        doc_id: Document ID
        vault_path: GCS path to redacted document in vault
        user_id: User ID who owns the document
        extraction_service: Extraction service instance
        database_service: Database service instance
        audit_logger: Audit logging service instance
    """
    try:
        from app.storage import document_store

        # Update status to extracting
        document_store.update_document(doc_id, {
            "extraction_status": "extracting",
            "updated_at": datetime.utcnow().isoformat()
        })

        # Log extraction start
        if audit_logger:
            audit_logger.log_extraction_started(
                user_id=user_id,
                document_id=doc_id,
                vault_path=vault_path
            )

        # Step 1: Extract fields from vault PDF
        extracted_fields = extraction_service.extract_tax_fields(vault_path)

        # Log extraction completion
        if audit_logger:
            audit_logger.log_extraction_completed(
                user_id=user_id,
                document_id=doc_id,
                extracted_fields=extracted_fields
            )

        # Step 2: Save to database
        record_id = database_service.insert_extraction(user_id, doc_id, extracted_fields)

        # Verify the record was saved by reading it back
        saved_data = database_service.get_extraction(doc_id)

        # Log database write
        if audit_logger:
            audit_logger.log_database_write(
                user_id=user_id,
                document_id=doc_id,
                operation="insert_extraction",
                record_id=record_id,
                table="extractions"
            )

        # Update document status
        document_store.update_document(doc_id, {
            "extraction_status": "completed",
            "extraction_record_id": record_id,
            "extracted_fields": extracted_fields,
            "updated_at": datetime.utcnow().isoformat()
        })

    except Exception as e:

        # Log extraction failure
        if audit_logger:
            audit_logger.log_extraction_failed(
                user_id=user_id,
                document_id=doc_id,
                error=str(e)
            )

        # Update status to failed
        try:
            from app.storage import document_store
            document_store.update_document(doc_id, {
                "extraction_status": "failed",
                "extraction_error": str(e),
                "updated_at": datetime.utcnow().isoformat()
            })
        except Exception as update_error:
            pass


@router.post("/reject/{document_id}", status_code=status.HTTP_200_OK)
async def reject_document(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Reject a redacted document:
    1. Delete original file from staging
    2. Delete redacted file from staging
    3. Update document status to 'rejected'

    Args:
        document_id: Document identifier
        request: FastAPI request object
        user_id: Current authenticated user ID

    Returns:
        Dictionary containing rejection status

    Raises:
        HTTPException: If document not found or user not authorized
    """
    try:
        from app.storage import document_store
        from datetime import datetime

        # Get document
        document = document_store.get_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Verify document belongs to user
        if document["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to reject this document"
            )

        # Verify document can be rejected (allow redacted, redaction_failed, uploaded, redacting)
        if document["status"] not in ["redacted", "redaction_failed", "uploaded", "redacting"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document cannot be rejected. Current status: {document['status']}"
            )

        # Get storage service
        storage_service = request.app.state.storage_service

        # Track deleted files
        deleted_files = []
        errors = []

        # Delete original file
        original_path = document.get("gcs_path")
        if original_path:
            try:
                was_deleted = storage_service.delete_file(original_path)
                if was_deleted:
                    deleted_files.append("original")
            except Exception as e:
                error_msg = f"Failed to delete original file: {str(e)}"
                errors.append(error_msg)

        # Delete redacted file
        redacted_path = document.get("redacted_path")
        if redacted_path:
            try:
                was_deleted = storage_service.delete_file(redacted_path)
                if was_deleted:
                    deleted_files.append("redacted")
            except Exception as e:
                error_msg = f"Failed to delete redacted file: {str(e)}"
                errors.append(error_msg)

        # Verify deletion
        if original_path:
            original_still_exists = storage_service.file_exists(original_path)
            if original_still_exists:
                warning = "Original file still exists in staging!"
                errors.append(warning)

        if redacted_path:
            redacted_still_exists = storage_service.file_exists(redacted_path)
            if redacted_still_exists:
                warning = "Redacted file still exists in staging!"
                errors.append(warning)

        # Update document status even if some deletions failed
        document_store.update_document(document_id, {
            "status": "rejected",
            "rejected_at": datetime.utcnow().isoformat(),
            "deletion_errors": errors if errors else None,
            "deleted_files": deleted_files
        })

        # Log rejection
        audit_logger = request.app.state.audit_logger
        audit_logger.log_document_rejected(
            user_id=user_id,
            document_id=document_id,
            filename=document["filename"],
            ip_address=request.client.host if request.client else None
        )

        # Log file deletions
        if "original" in deleted_files:
            audit_logger.log_file_deleted(
                user_id=user_id,
                document_id=document_id,
                file_path=original_path,
                file_type="original",
                reason="rejected"
            )

        if "redacted" in deleted_files:
            audit_logger.log_file_deleted(
                user_id=user_id,
                document_id=document_id,
                file_path=redacted_path,
                file_type="redacted",
                reason="rejected"
            )

        # Return success with details
        result = {
            "success": True,
            "message": "Document rejected",
            "document_id": document_id,
            "status": "rejected",
            "deleted_files": deleted_files,
        }

        if errors:
            result["warnings"] = errors

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject document: {str(e)}"
        )


@router.get("/download/{document_id}")
async def download_document(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Generate download URL for an approved document.
    Only works for documents with status 'approved'.

    Args:
        document_id: Document identifier
        request: FastAPI request object
        user_id: Current authenticated user ID

    Returns:
        Dictionary containing download URL and metadata

    Raises:
        HTTPException: If document not found or not approved
    """
    try:
        from app.storage import document_store

        # Get document
        document = document_store.get_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Verify document belongs to user
        if document["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to download this document"
            )

        # Verify document is approved
        if document["status"] != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only approved documents can be downloaded. Current status: {document['status']}"
            )

        # Check vault file exists
        if not document.get("vault_path"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found in vault"
            )

        # Get storage service
        storage_service = request.app.state.storage_service

        # Parse vault path
        vault_path = document["vault_path"]
        if not vault_path.startswith("gs://"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid vault path format"
            )

        path_parts = vault_path.replace("gs://", "").split("/", 1)
        bucket_name = path_parts[0]
        blob_path = path_parts[1]

        # Generate signed URL (expires in 15 minutes)
        signed_url = storage_service.generate_signed_url(
            bucket_name,
            blob_path,
            expiration_minutes=15
        )

        # Log download
        audit_logger = request.app.state.audit_logger
        audit_logger.log_document_downloaded(
            user_id=user_id,
            document_id=document_id,
            filename=document["filename"],
            vault_path=vault_path,
            ip_address=request.client.host if request.client else None
        )

        return {
            "document_id": document_id,
            "download_url": signed_url,
            "filename": document["filename"],
            "expires_in_minutes": 15
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.get("/extractions/{document_id}")
async def get_extraction(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Get extracted tax fields for a document.

    Args:
        document_id: Document identifier
        request: FastAPI request object
        user_id: Current authenticated user ID

    Returns:
        Dictionary containing extraction status and fields

    Raises:
        HTTPException: If document not found or user not authorized
    """
    try:
        from app.storage import document_store

        # Get document
        document = document_store.get_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Verify document belongs to user
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

        # Check if extraction completed
        extraction_status = document.get("extraction_status", "not_started")

        if extraction_status == "not_started":
            return {
                "document_id": document_id,
                "status": "not_started",
                "message": "Document has not been approved yet"
            }

        if extraction_status == "extracting":
            return {
                "document_id": document_id,
                "status": "extracting",
                "message": "Field extraction in progress..."
            }

        if extraction_status == "failed":
            return {
                "document_id": document_id,
                "status": "failed",
                "error": document.get("extraction_error", "Unknown error")
            }

        # Get from database
        database_service = request.app.state.database_service
        extraction_data = database_service.get_extraction(document_id)

        if not extraction_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extraction data not found"
            )

        return {
            "document_id": document_id,
            "status": "completed",
            "extracted_fields": {
                "filing_status": extraction_data["filing_status"],
                "w2_wages": extraction_data["w2_wages"],
                "total_deductions": extraction_data["total_deductions"],
                "ira_distributions_total": extraction_data["ira_distributions_total"],
                "capital_gain_or_loss": extraction_data["capital_gain_or_loss"]
            },
            "extracted_at": extraction_data["extracted_at"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/auth/session")
async def validate_session(request: Request, user_id: str = Depends(get_current_user)):
    """
    Validate user session and log login event.
    Called by frontend after successful authentication.

    Returns:
        User session information
    """
    try:
        # Log user session
        audit_logger = request.app.state.audit_logger
        audit_logger.log_user_login(
            user_id=user_id,
            user_email=user_id,  # Email is used as user_id
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "user_id": user_id,
            "message": "Session validated successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session validation failed: {str(e)}"
        )


