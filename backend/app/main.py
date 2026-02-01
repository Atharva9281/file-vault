"""
File Vault FastAPI Application

Main application entry point for the File Vault system.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage
from app.config import settings
from app.routers import upload, approval, documents
from app.services.redaction_service import RedactionService
from app.services.storage_service import StorageService
from app.services.database_service import DatabaseService
from app.services.extraction_service import ExtractionService
from app.services.logging_service import AuditLoggingService
from app.storage import document_store

# Set Google Cloud credentials from settings (only for local development)
# Cloud Run uses the service account automatically, so this is only needed locally
if hasattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS') and settings.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS


# Create FastAPI application instance
app = FastAPI(
    title="File Vault API",
    description="Secure document management system with redaction and extraction",
    version="0.1.0"
)

# Initialize services
redaction_service = RedactionService(
    project_id=settings.PROJECT_ID,
    processor_id=settings.DOCUMENT_AI_PROCESSOR_ID,
    location=settings.DOCUMENT_AI_LOCATION
)

storage_service = StorageService(
    project_id=settings.PROJECT_ID
)

database_service = DatabaseService(
    project_id=settings.PROJECT_ID,
    region=settings.REGION,
    instance_name=settings.DB_INSTANCE_NAME,
    database_name=settings.DB_NAME,
    db_user=settings.DB_USER,
    secret_name=settings.DB_SECRET_NAME
)

extraction_service = ExtractionService(
    project_id=settings.PROJECT_ID,
    location=settings.VERTEX_AI_LOCATION
)

audit_logger = AuditLoggingService(project_id=settings.PROJECT_ID)

# Make services available to routers
app.state.redaction_service = redaction_service
app.state.storage_service = storage_service
app.state.database_service = database_service
app.state.extraction_service = extraction_service
app.state.audit_logger = audit_logger

# Sync documents from GCS on startup
@app.on_event("startup")
async def startup_event():
    """
    Run on application startup.
    Verifies IAM configuration and syncs existing documents.
    """
    try:
        from google.auth import default
        import logging

        logger = logging.getLogger(__name__)

        # Verify IAM configuration
        logger.info("=" * 60)
        logger.info("Starting File Vault Backend")
        logger.info("=" * 60)

        # Get default credentials
        credentials, project = default()

        logger.info(f"Project ID: {project}")
        if hasattr(credentials, 'service_account_email'):
            logger.info(f"Service Account: {credentials.service_account_email}")
        else:
            logger.info("Service Account: Using default credentials")

        # Verify required environment variables
        required_vars = [
            'PROJECT_ID',
            'STAGING_BUCKET',
            'VAULT_BUCKET',
            'DOCUMENT_AI_PROCESSOR_ID',
            'DOCUMENT_AI_LOCATION',
            'DB_INSTANCE_NAME',
            'DB_NAME',
            'DB_USER',
        ]

        missing = [var for var in required_vars if not getattr(settings, var, None)]
        if missing:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing)}")
            raise Exception(f"Missing environment variables: {missing}")

        logger.info("✓ Environment configuration verified")
        logger.info(f"  - Project ID: {settings.PROJECT_ID}")
        logger.info(f"  - Staging Bucket: {settings.STAGING_BUCKET}")
        logger.info(f"  - Vault Bucket: {settings.VAULT_BUCKET}")
        logger.info(f"  - Document AI Location: {settings.DOCUMENT_AI_LOCATION}")
        logger.info(f"  - Database Instance: {settings.DB_INSTANCE_NAME}")
        logger.info(f"  - Database Name: {settings.DB_NAME}")

        # Sync documents from GCS (both staging and vault)
        storage_client = storage.Client(project=settings.PROJECT_ID)
        synced_count = document_store.sync_from_gcs(
            storage_client,
            settings.STAGING_BUCKET,
            settings.VAULT_BUCKET
        )
        logger.info(f"✓ Synced {synced_count} documents from GCS buckets (staging + vault)")

        # Initialize database connection
        logger.info("Initializing database connection...")
        database_service.initialize()
        logger.info("✓ Database connection established and schema verified")

        logger.info("=" * 60)
        logger.info("✓ File Vault Backend Ready")
        logger.info("=" * 60)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Startup error: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown.
    Closes database connections and cleanup resources.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info("Shutting down File Vault Backend...")
        database_service.close()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend development server
        "https://localhost:3000",  # Frontend HTTPS (if used)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(upload.router)
app.include_router(approval.router)
app.include_router(documents.router)


@app.get("/", tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        Dictionary containing service status and configuration info
    """
    return {
        "status": "healthy",
        "service": "file-vault-api",
        "version": "0.1.0",
        "project_id": settings.PROJECT_ID
    }


@app.get("/config", tags=["health"])
async def get_config():
    """
    Get non-sensitive configuration information.

    Returns:
        Dictionary containing configuration details
    """
    return {
        "project_id": settings.PROJECT_ID,
        "region": settings.REGION,
        "staging_bucket": settings.STAGING_BUCKET,
        "vault_bucket": settings.VAULT_BUCKET
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
