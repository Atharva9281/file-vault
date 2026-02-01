"""
Application configuration management.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        PROJECT_ID: GCP project identifier
        STAGING_BUCKET: GCS bucket for uploaded files awaiting approval
        VAULT_BUCKET: GCS bucket for approved files
        DB_SECRET_NAME: Secret Manager secret name for database credentials
        DB_INSTANCE_NAME: Cloud SQL instance name
        DB_NAME: Database name
        DB_USER: Database user
        REGION: GCP region for resources
        NEXTAUTH_SECRET: Secret used to verify NextAuth.js JWT tokens
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account key file
        DOCUMENT_AI_PROCESSOR_ID: Document AI processor ID for OCR
        DOCUMENT_AI_LOCATION: Document AI processor location
        VERTEX_AI_LOCATION: Vertex AI location for Gemini models
    """
    PROJECT_ID: str
    STAGING_BUCKET: str
    VAULT_BUCKET: str
    DB_SECRET_NAME: str = "file-vault-db-credentials"
    DB_INSTANCE_NAME: str
    DB_NAME: str
    DB_USER: str
    REGION: str = "us-central1"
    NEXTAUTH_SECRET: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    DOCUMENT_AI_PROCESSOR_ID: str
    DOCUMENT_AI_LOCATION: str = "us"
    VERTEX_AI_LOCATION: str = "us-central1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
