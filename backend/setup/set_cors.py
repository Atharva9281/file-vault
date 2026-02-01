"""
Set CORS configuration on GCS buckets to allow frontend to fetch PDFs
"""
import json
from google.cloud import storage

def set_bucket_cors(bucket_name: str):
    """Set CORS configuration on a GCS bucket"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    cors_configuration = [
        {
            "origin": ["http://localhost:3000", "https://*.vercel.app"],
            "method": ["GET", "HEAD"],
            "responseHeader": ["Content-Type", "Content-Length", "Content-Range"],
            "maxAgeSeconds": 3600
        }
    ]

    bucket.cors = cors_configuration
    bucket.patch()

    print(f"✓ CORS configuration set on {bucket_name}")
    print(f"  Allowed origins: {cors_configuration[0]['origin']}")
    print(f"  Allowed methods: {cors_configuration[0]['method']}")

if __name__ == "__main__":
    # Set CORS on both buckets
    print("Setting CORS configuration on GCS buckets...")
    print()

    set_bucket_cors("file-vault-assessment-484617-staging")
    print()
    set_bucket_cors("file-vault-assessment-484617-vault")
    print()
    print("✓ Done! CORS configuration applied to all buckets.")
    print("  You can now load PDFs from the frontend.")
