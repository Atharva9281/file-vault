"""
Google Cloud Storage service for file management.
"""

from typing import BinaryIO, Optional
from google.cloud import storage


class StorageService:
    """
    Service for managing file uploads and downloads to Google Cloud Storage.

    Attributes:
        project_id: GCP project identifier
        client: Google Cloud Storage client instance
    """

    def __init__(self, project_id: str):
        """
        Initialize the storage service.

        Args:
            project_id: GCP project identifier
        """
        self.project_id = project_id
        self.client = storage.Client(project=project_id)

    def upload_file(
        self,
        bucket_name: str,
        file_obj: BinaryIO,
        destination_blob_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to a GCS bucket.

        Args:
            bucket_name: Name of the target bucket
            file_obj: File-like object to upload
            destination_blob_name: Destination path in the bucket
            content_type: MIME type of the file

        Returns:
            GCS URI of the uploaded file

        Raises:
            Exception: If upload fails
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        if content_type:
            blob.content_type = content_type

        blob.upload_from_file(file_obj, rewind=True)

        return f"gs://{bucket_name}/{destination_blob_name}"

    def download_file(
        self,
        bucket_name: str,
        source_blob_name: str,
        destination_file_obj: BinaryIO
    ) -> None:
        """
        Download a file from a GCS bucket.

        Args:
            bucket_name: Name of the source bucket
            source_blob_name: Path to the blob in the bucket
            destination_file_obj: File-like object to write to

        Raises:
            Exception: If download fails
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_file(destination_file_obj)

    def copy_file(
        self,
        source_bucket_name: str,
        source_blob_name: str,
        destination_bucket_name: str,
        destination_blob_name: str
    ) -> str:
        """
        Copy a file from one bucket to another.

        Args:
            source_bucket_name: Source bucket name
            source_blob_name: Source blob path
            destination_bucket_name: Destination bucket name
            destination_blob_name: Destination blob path

        Returns:
            GCS URI of the copied file

        Raises:
            Exception: If copy fails
        """
        source_bucket = self.client.bucket(source_bucket_name)
        source_blob = source_bucket.blob(source_blob_name)
        destination_bucket = self.client.bucket(destination_bucket_name)

        source_bucket.copy_blob(
            source_blob,
            destination_bucket,
            destination_blob_name
        )

        return f"gs://{destination_bucket_name}/{destination_blob_name}"

    def delete_file(self, bucket_name: str, blob_name: str) -> None:
        """
        Delete a file from a GCS bucket.

        Args:
            bucket_name: Bucket name
            blob_name: Blob path to delete

        Raises:
            Exception: If deletion fails
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()

    def file_exists(self, bucket_name: str, blob_name: str) -> bool:
        """
        Check if a file exists in a GCS bucket.

        Args:
            bucket_name: Bucket name
            blob_name: Blob path to check

        Returns:
            True if file exists, False otherwise
        """
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()

    def move_file(self, source_gcs_path: str, dest_gcs_path: str) -> None:
        """
        Move a file from one GCS location to another.
        This is effectively a copy + delete operation.

        Args:
            source_gcs_path: Source path (gs://bucket/path)
            dest_gcs_path: Destination path (gs://bucket/path)

        Raises:
            Exception: If move operation fails
        """
        try:
            # Parse source
            source_parts = source_gcs_path.replace("gs://", "").split("/", 1)
            source_bucket_name = source_parts[0]
            source_blob_path = source_parts[1]

            # Parse destination
            dest_parts = dest_gcs_path.replace("gs://", "").split("/", 1)
            dest_bucket_name = dest_parts[0]
            dest_blob_path = dest_parts[1]

            # Get buckets
            source_bucket = self.client.bucket(source_bucket_name)
            dest_bucket = self.client.bucket(dest_bucket_name)

            # Get source blob
            source_blob = source_bucket.blob(source_blob_path)

            # Copy to destination
            source_bucket.copy_blob(source_blob, dest_bucket, dest_blob_path)

            # Delete source
            source_blob.delete()

        except Exception as e:
            raise Exception(f"Error moving file: {str(e)}")

    def file_exists(self, gcs_path: str) -> bool:
        """
        Check if a file exists in GCS.

        Args:
            gcs_path: Path to file (gs://bucket/path)

        Returns:
            True if file exists, False otherwise
        """
        try:
            if not gcs_path or not gcs_path.startswith("gs://"):
                return False

            # Parse path
            parts = gcs_path.replace("gs://", "").split("/", 1)
            if len(parts) != 2:
                return False

            bucket_name = parts[0]
            blob_path = parts[1]

            # Get bucket and blob
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            return blob.exists()

        except Exception as e:
            return False

    def delete_file(self, gcs_path: str) -> bool:
        """
        Delete a file from GCS.

        Args:
            gcs_path: Path to file (gs://bucket/path)

        Returns:
            True if file was deleted, False if file didn't exist

        Raises:
            Exception: If deletion fails
        """
        try:
            if not gcs_path or not gcs_path.startswith("gs://"):
                raise ValueError(f"Invalid GCS path: {gcs_path}")

            # Parse path
            parts = gcs_path.replace("gs://", "").split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid GCS path format: {gcs_path}")

            bucket_name = parts[0]
            blob_path = parts[1]

            # Get bucket and blob
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            # Check if file exists before attempting delete
            if blob.exists():
                blob.delete()
                return True
            else:
                return False

        except Exception as e:
            error_msg = f"Error deleting file {gcs_path}: {str(e)}"
            raise Exception(error_msg)

    def generate_signed_url(
        self,
        bucket_name: str,
        blob_path: str,
        expiration_minutes: int = 15
    ) -> str:
        """
        Generate a signed URL for file download.
        Works both locally (with service account key) and on Cloud Run (using IAM signBlob).

        Args:
            bucket_name: Name of the bucket
            blob_path: Path to the blob in the bucket
            expiration_minutes: URL expiration time in minutes (default: 15)

        Returns:
            Signed URL string that expires after specified minutes

        Raises:
            Exception: If signed URL generation fails
        """
        from datetime import datetime, timedelta
        from urllib.parse import quote
        import hashlib
        import binascii
        import google.auth
        from google.auth.transport import requests as auth_requests
        from google.cloud import iam_credentials_v1

        try:
            # Try standard method first (works with service account keys locally)
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            return url
        except AttributeError:
            # No private key - use IAM signBlob API (for Cloud Run)
            pass

        # Get credentials and service account email
        credentials, project = google.auth.default()
        auth_request = auth_requests.Request()
        credentials.refresh(auth_request)
        service_account_email = credentials.service_account_email

        # Calculate expiration timestamp
        expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
        expiration_timestamp = int(expiration.timestamp())

        # Construct canonical request components
        canonical_uri = f"/{blob_path}"
        canonical_query_string = f"X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential={quote(service_account_email)}/{expiration.strftime('%Y%m%d')}/auto/storage/goog4_request&X-Goog-Date={expiration.strftime('%Y%m%dT%H%M%SZ')}&X-Goog-Expires={expiration_minutes * 60}&X-Goog-SignedHeaders=host"
        canonical_headers = f"host:{bucket_name}.storage.googleapis.com\n"
        signed_headers = "host"

        # Construct canonical request
        canonical_request = f"GET\n{canonical_uri}\n{canonical_query_string}\n{canonical_headers}\n{signed_headers}\nUNSIGNED-PAYLOAD"

        # Create string to sign
        credential_scope = f"{expiration.strftime('%Y%m%d')}/auto/storage/goog4_request"
        string_to_sign = f"GOOG4-RSA-SHA256\n{expiration.strftime('%Y%m%dT%H%M%SZ')}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

        # Use IAM signBlob API to sign
        iam_client = iam_credentials_v1.IAMCredentialsClient(credentials=credentials)
        service_account_path = f"projects/-/serviceAccounts/{service_account_email}"

        response = iam_client.sign_blob(
            name=service_account_path,
            payload=string_to_sign.encode()
        )

        signature = binascii.hexlify(response.signed_blob).decode()

        # Construct final signed URL
        signed_url = f"https://{bucket_name}.storage.googleapis.com{canonical_uri}?{canonical_query_string}&X-Goog-Signature={signature}"

        return signed_url
