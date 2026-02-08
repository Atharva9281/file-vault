"""
In-memory document storage.

This is a temporary storage solution for development.
In production, this would be replaced with a proper database.
"""

from typing import Dict, List, Optional
from datetime import datetime

# In-memory storage for documents
# Format: {document_id: document_object}
_documents: Dict[str, dict] = {}


def create_document(
    doc_id: str,
    user_id: str,
    filename: str,
    gcs_path: str,
    file_size: int,
    content_type: str
) -> dict:
    """
    Create and store a new document.

    Args:
        doc_id: Unique document identifier
        user_id: User who uploaded the document
        filename: Original filename
        gcs_path: GCS path where file is stored
        file_size: Size of the file in bytes
        content_type: MIME type of the file

    Returns:
        Created document object
    """
    current_time = datetime.utcnow().isoformat()

    document = {
        "id": doc_id,
        "user_id": user_id,
        "filename": filename,
        "status": "uploaded",
        "gcs_path": gcs_path,
        "file_size": file_size,
        "content_type": content_type,
        "created_at": current_time,
        "updated_at": current_time,
        "extraction_status": "not_started"  # Initialize extraction status
    }

    _documents[doc_id] = document
    return document


def get_document(doc_id: str) -> Optional[dict]:
    """
    Retrieve a document by ID.

    Args:
        doc_id: Document identifier

    Returns:
        Document object if found, None otherwise
    """
    return _documents.get(doc_id)


def get_documents_by_user(user_id: str) -> List[dict]:
    """
    Retrieve all documents for a specific user.

    Args:
        user_id: User identifier

    Returns:
        List of document objects
    """
    return [
        doc for doc in _documents.values()
        if doc["user_id"] == user_id
    ]


def update_document_status(doc_id: str, status: str) -> Optional[dict]:
    """
    Update the status of a document.

    Args:
        doc_id: Document identifier
        status: New status (uploaded, redacting, redacted, approved, rejected)

    Returns:
        Updated document object if found, None otherwise
    """
    if doc_id in _documents:
        _documents[doc_id]["status"] = status
        _documents[doc_id]["updated_at"] = datetime.utcnow().isoformat()
        return _documents[doc_id]
    return None


def update_document(doc_id: str, updates: dict) -> Optional[dict]:
    """
    Update multiple fields of a document.

    Args:
        doc_id: Document identifier
        updates: Dictionary of fields to update

    Returns:
        Updated document object if found, None otherwise
    """
    if doc_id in _documents:
        _documents[doc_id].update(updates)
        _documents[doc_id]["updated_at"] = datetime.utcnow().isoformat()
        return _documents[doc_id]
    return None


def delete_document(doc_id: str) -> bool:
    """
    Delete a document from storage.

    Args:
        doc_id: Document identifier

    Returns:
        True if deleted, False if not found
    """
    if doc_id in _documents:
        del _documents[doc_id]
        return True
    return False


def get_all_documents() -> List[dict]:
    """
    Retrieve all documents.

    Returns:
        List of all document objects
    """
    return list(_documents.values())


def sync_from_gcs(storage_client, staging_bucket_name: str, vault_bucket_name: str = None) -> int:
    """
    Sync documents from GCS buckets into in-memory storage.
    Syncs from both staging (for uploaded/redacted) and vault (for approved).
    Useful for recovering document list after server restart.

    Args:
        storage_client: Google Cloud Storage client
        staging_bucket_name: Name of the staging bucket to sync from
        vault_bucket_name: Optional name of the vault bucket to sync approved documents

    Returns:
        Number of documents synced
    """
    from datetime import datetime

    synced_count = 0

    # Sync from staging bucket (uploaded and redacted documents)
    staging_bucket = storage_client.bucket(staging_bucket_name)
    staging_blobs = list(staging_bucket.list_blobs())

    # First pass: collect all document IDs and their files from staging
    doc_files = {}  # {doc_id: {'original': blob, 'redacted': blob}}

    for blob in staging_blobs:
        # Parse blob path: users/{user_id}/{doc_id}_original_{filename} or {doc_id}_redacted_{filename}
        path_parts = blob.name.split('/')

        if len(path_parts) < 3 or path_parts[0] != 'users':
            continue

        user_id = path_parts[1]
        filename_part = path_parts[2]

        # Extract doc_id and file type
        doc_id = None
        file_type = None
        filename = None

        if '_original_' in filename_part:
            doc_id_part, filename = filename_part.split('_original_', 1)
            doc_id = doc_id_part
            file_type = 'original'
        elif '_redacted_' in filename_part:
            doc_id_part, filename = filename_part.split('_redacted_', 1)
            doc_id = doc_id_part
            file_type = 'redacted'
        else:
            continue

        # Initialize doc_files entry if needed
        if doc_id not in doc_files:
            doc_files[doc_id] = {
                'user_id': user_id,
                'filename': filename,
                'original': None,
                'redacted': None,
                'bucket': staging_bucket_name
            }

        # Store the blob
        doc_files[doc_id][file_type] = blob

    # Second pass: create document records for staging documents
    for doc_id, files in doc_files.items():
        # Skip if already in memory
        if doc_id in _documents:
            continue

        original_blob = files['original']
        redacted_blob = files['redacted']

        # Determine status based on which files exist
        if redacted_blob:
            status = "redacted"
            gcs_path = f"gs://{staging_bucket_name}/{original_blob.name}" if original_blob else None
            redacted_path = f"gs://{staging_bucket_name}/{redacted_blob.name}"
        elif original_blob:
            status = "uploaded"
            gcs_path = f"gs://{staging_bucket_name}/{original_blob.name}"
            redacted_path = None
        else:
            continue

        # Use original blob for metadata, fall back to redacted if original doesn't exist
        metadata_blob = original_blob if original_blob else redacted_blob

        # Create document record
        document = {
            "id": doc_id,
            "user_id": files['user_id'],
            "filename": files['filename'],
            "status": status,
            "gcs_path": gcs_path,
            "file_size": metadata_blob.size,
            "content_type": metadata_blob.content_type or "application/octet-stream",
            "created_at": metadata_blob.time_created.isoformat() if metadata_blob.time_created else datetime.utcnow().isoformat(),
            "updated_at": metadata_blob.updated.isoformat() if metadata_blob.updated else datetime.utcnow().isoformat(),
            "extraction_status": "not_started"  # Initialize extraction status for synced documents
        }

        # Add redacted_path if it exists
        if redacted_path:
            document["redacted_path"] = redacted_path

        _documents[doc_id] = document
        synced_count += 1

    # Sync from vault bucket (approved documents)
    if vault_bucket_name:
        vault_bucket = storage_client.bucket(vault_bucket_name)
        vault_blobs = list(vault_bucket.list_blobs())

        for blob in vault_blobs:
            # Parse blob path: users/{user_id}/documents/{doc_id}_redacted.pdf
            path_parts = blob.name.split('/')

            if len(path_parts) < 4 or path_parts[0] != 'users' or path_parts[2] != 'documents':
                continue

            user_id = path_parts[1]
            filename_part = path_parts[3]

            # Extract doc_id from vault naming pattern: {doc_id}_redacted_{original_filename}
            if '_redacted_' in filename_part:
                doc_id, original_filename = filename_part.split('_redacted_', 1)

                # Skip if already in memory
                if doc_id in _documents:
                    continue

                vault_path = f"gs://{vault_bucket_name}/{blob.name}"

                # Create approved document record
                document = {
                    "id": doc_id,
                    "user_id": user_id,
                    "filename": original_filename,
                    "status": "approved",
                    "gcs_path": None,  # Original file deleted
                    "redacted_path": None,  # Moved to vault
                    "vault_path": vault_path,
                    "file_size": blob.size,
                    "content_type": blob.content_type or "application/pdf",
                    "created_at": blob.time_created.isoformat() if blob.time_created else datetime.utcnow().isoformat(),
                    "updated_at": blob.updated.isoformat() if blob.updated else datetime.utcnow().isoformat(),
                    "approved_at": blob.updated.isoformat() if blob.updated else datetime.utcnow().isoformat(),
                    "extraction_status": "completed"  # Assume extraction completed for approved vault documents
                }

                _documents[doc_id] = document
                synced_count += 1

    return synced_count
