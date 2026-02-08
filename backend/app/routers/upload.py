"""
File upload endpoints.
"""

import uuid
from io import BytesIO
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request, BackgroundTasks
from app.auth import get_current_user
from app.config import settings
from app.utils.validators import validate_upload_file, sanitize_filename
from app.services.storage_service import StorageService
import traceback


router = APIRouter(prefix="/upload", tags=["upload"])


def process_redaction(doc_id: str, gcs_input_path: str, redaction_service, storage_service, database_service, audit_logger=None):
    """
    Background task to process redaction pipeline.
    Runs OCR → PII detection → PDF redaction → Validation.

    Args:
        doc_id: Document identifier
        gcs_input_path: GCS path to original file
        redaction_service: RedactionService instance
        storage_service: StorageService instance for file cleanup
        database_service: DatabaseService instance for document storage
        audit_logger: AuditLoggingService instance for logging
    """
    try:
        # Get document info
        document = database_service.get_document_dict(doc_id)
        user_id = document["user_id"] if document else "unknown"
        filename = document["filename"] if document else "unknown"

        # Log redaction start
        if audit_logger:
            audit_logger.log_redaction_started(
                user_id=user_id,
                document_id=doc_id,
                filename=filename
            )

        # Update status to 'redacting'
        database_service.update_document_status(doc_id, "redacting")

        # Generate output path
        gcs_output_path = gcs_input_path.replace("_original_", "_redacted_")

        # Step 1: Extract text with OCR
        ocr_result = redaction_service.extract_text_with_coordinates(gcs_input_path)

        # Step 2: Detect PII
        pii_findings = redaction_service.detect_pii(ocr_result["text"])

        pii_types = {}
        for finding in pii_findings:
            # Handle both string and dict formats
            if isinstance(finding, str):
                pii_type = finding
            elif isinstance(finding, dict):
                pii_type = finding.get('info_type', {}).get('name', 'UNKNOWN') if isinstance(finding.get('info_type'), dict) else str(finding.get('info_type', 'UNKNOWN'))
            else:
                pii_type = 'UNKNOWN'
            pii_types[pii_type] = pii_types.get(pii_type, 0) + 1

        # Step 3: Identify regions to redact
        redaction_regions = redaction_service.identify_pii_regions(ocr_result, pii_findings)

        # Step 4: Create redacted PDF (SECURE method)
        redacted_path = redaction_service.redact_pdf(
            gcs_input_path,
            gcs_output_path,
            redaction_regions
        )

        # Step 5: Validate redaction
        validation = redaction_service.validate_redaction(redacted_path)

        # Check if validation passed
        if validation["is_clean"]:
            # SUCCESS: Redaction is safe
            database_service.update_document(doc_id, **{
                "redacted_path": redacted_path,
                "status": "redacted",
                "pii_count": len(pii_findings),
                "validation": validation
            })

            # Log successful redaction
            if audit_logger:
                audit_logger.log_redaction_completed(
                    user_id=user_id,
                    document_id=doc_id,
                    pii_items_found=len(pii_findings),
                    pii_items_redacted=len(redaction_regions)
                )
        else:
            # FAILED: PII still visible - delete unsafe files
            try:
                # Delete original file
                storage_service.delete_file(gcs_input_path)

                # Delete failed redacted file
                storage_service.delete_file(redacted_path)

            except Exception as cleanup_error:
                pass

            # Update document status
            database_service.update_document(doc_id, **{
                "status": "redaction_failed",
                "pii_count": len(pii_findings),
                "validation": validation,
                "files_deleted": True,
                "failure_reason": f"PII still visible after redaction ({validation.get('pii_found', 0)} items detected)"
            })

            # Log redaction failure
            if audit_logger:
                audit_logger.log_redaction_failed(
                    user_id=user_id,
                    document_id=doc_id,
                    error=f"PII still visible after redaction ({validation.get('pii_found', 0)} items detected)"
                )

    except Exception as e:
        # Delete files on error (unsafe/incomplete redaction)
        try:
            storage_service.delete_file(gcs_input_path)

            # Try to delete redacted file if it was created
            redacted_path = gcs_input_path.replace("_original_", "_redacted_")
            storage_service.delete_file(redacted_path)
        except Exception as cleanup_error:
            pass

        # Update status to failed
        database_service.update_document(doc_id, **{
            "status": "redaction_failed",
            "files_deleted": True,
            "failure_reason": f"Error during redaction: {str(e)}"
        })

        # Log redaction failure
        if audit_logger:
            document = database_service.get_document_dict(doc_id)
            user_id = document["user_id"] if document else "unknown"
            audit_logger.log_redaction_failed(
                user_id=user_id,
                document_id=doc_id,
                error=str(e)
            )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
    user_id: str = Depends(get_current_user)
):
    """
    Upload a document to the staging bucket and trigger automatic redaction.

    Args:
        file: File to upload
        background_tasks: FastAPI background tasks
        request: FastAPI request object (to access app state)
        user_id: Current authenticated user ID

    Returns:
        Dictionary containing upload status and document metadata

    Raises:
        HTTPException: If upload fails or validation fails
    """
    try:
        # Validate the uploaded file
        await validate_upload_file(file)

        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)

        # Generate unique document ID
        doc_id = str(uuid.uuid4())

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Create file object for upload
        file_obj = BytesIO(file_content)

        # Initialize storage service
        storage_service = StorageService(project_id=settings.PROJECT_ID)

        # Define GCS path: users/{user_id}/{doc_id}_original_{filename}
        blob_path = f"users/{user_id}/{doc_id}_original_{safe_filename}"

        # Upload to staging bucket
        gcs_path = storage_service.upload_file(
            bucket_name=settings.STAGING_BUCKET,
            file_obj=file_obj,
            destination_blob_name=blob_path,
            content_type=file.content_type
        )

        # Create document record in database
        database_service = request.app.state.database_service
        doc_obj = database_service.create_document(
            doc_id=doc_id,
            user_id=user_id,
            filename=safe_filename,
            gcs_path=gcs_path,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream"
        )
        document = doc_obj.to_dict()

        # Log upload event
        if request:
            audit_logger = request.app.state.audit_logger
            audit_logger.log_document_uploaded(
                user_id=user_id,
                document_id=doc_id,
                filename=safe_filename,
                file_size=file_size,
                ip_address=request.client.host if request.client else None
            )

        # Trigger automatic redaction in background
        if background_tasks and request:
            redaction_service = request.app.state.redaction_service
            storage_service = request.app.state.storage_service
            audit_logger = request.app.state.audit_logger
            background_tasks.add_task(
                process_redaction,
                doc_id,
                gcs_path,
                redaction_service,
                storage_service,
                database_service,
                audit_logger
            )

        # Return success response
        return {
            "document_id": doc_id,
            "status": "uploaded",
            "filename": safe_filename,
            "file_size": file_size,
            "gcs_path": gcs_path,
            "created_at": document["created_at"]
        }

    except HTTPException:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/download-redacted/{document_id}")
async def download_redacted(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """
    Generate a signed URL to download the redacted PDF.

    Args:
        document_id: Document identifier
        request: FastAPI request object
        user_id: Current authenticated user ID

    Returns:
        Signed URL valid for 1 hour
    """
    try:
        from google.cloud import storage
        from datetime import timedelta

        # Get document
        database_service = request.app.state.database_service
        document = database_service.get_document_dict(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Verify ownership
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
                detail="Access denied"
            )

        # Check if redacted file exists
        if "redacted_path" not in document or not document["redacted_path"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Redacted file not found. Run redaction first."
            )

        # Parse GCS path
        gcs_path = document["redacted_path"]
        parts = gcs_path.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1]

        # Generate signed URL (valid for 1 hour)
        storage_client = storage.Client(project=settings.PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET"
        )

        return {
            "download_url": url,
            "filename": document["filename"].replace(".pdf", "_redacted.pdf"),
            "expires_in": "1 hour"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )
