"""
Database service for Cloud SQL PostgreSQL connections
Handles tax extraction data storage and retrieval
"""

import os
import sqlalchemy
from google.cloud.sql.connector import Connector
from google.cloud import secretmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, MetaData, Table, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class TaxExtraction(Base):
    """SQLAlchemy model for tax extractions"""
    __tablename__ = 'tax_extractions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    document_id = Column(String(255), nullable=False, index=True)
    filing_status = Column(String(50), nullable=True)
    w2_wages = Column(Float, nullable=True)
    total_deductions = Column(Float, nullable=True)
    ira_distributions_total = Column(Float, nullable=True)
    capital_gain_or_loss = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Document(Base):
    """SQLAlchemy model for documents"""
    __tablename__ = 'documents'

    # Primary key - UUID as string
    id = Column(String(36), primary_key=True)

    # Core fields
    user_id = Column(String(255), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)

    # GCS paths
    gcs_path = Column(Text, nullable=True)
    redacted_path = Column(Text, nullable=True)
    vault_path = Column(Text, nullable=True)

    # Status fields
    status = Column(String(50), nullable=False, default='uploaded', index=True)
    extraction_status = Column(String(50), nullable=False, default='not_started', index=True)

    # Redaction metadata
    pii_count = Column(Integer, nullable=True)
    validation = Column(JSONB, nullable=True)
    files_deleted = Column(Boolean, nullable=True, default=False)
    failure_reason = Column(Text, nullable=True)
    deletion_errors = Column(JSONB, nullable=True)
    deleted_files = Column(JSONB, nullable=True)

    # Extraction linkage
    extraction_record_id = Column(Integer, nullable=True)
    extracted_fields = Column(JSONB, nullable=True)
    extraction_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Convert model to dictionary for API compatibility"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "gcs_path": self.gcs_path,
            "redacted_path": self.redacted_path,
            "vault_path": self.vault_path,
            "status": self.status,
            "extraction_status": self.extraction_status,
            "pii_count": self.pii_count,
            "validation": self.validation,
            "files_deleted": self.files_deleted,
            "failure_reason": self.failure_reason,
            "deletion_errors": self.deletion_errors,
            "deleted_files": self.deleted_files,
            "extraction_record_id": self.extraction_record_id,
            "extracted_fields": self.extracted_fields,
            "extraction_error": self.extraction_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
        }


class DatabaseService:
    """Service for managing Cloud SQL database connections and operations"""

    def __init__(
        self,
        project_id: str,
        region: str,
        instance_name: str,
        database_name: str,
        db_user: str,
        secret_name: str
    ):
        """
        Initialize database service with Cloud SQL connector

        Args:
            project_id: GCP project ID
            region: Cloud SQL instance region
            instance_name: Cloud SQL instance name
            database_name: Database name
            db_user: Database user
            secret_name: Secret Manager secret name for database password
        """
        self.project_id = project_id
        self.region = region
        self.instance_name = instance_name
        self.database_name = database_name
        self.db_user = db_user
        self.secret_name = secret_name

        self.connector = None
        self.engine = None
        self.SessionLocal = None

        logger.info(f"Initializing DatabaseService for project: {project_id}")

    def _get_db_password(self) -> str:
        """Fetch database password from Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            secret_path = f"projects/{self.project_id}/secrets/{self.secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": secret_path})
            password = response.payload.data.decode("UTF-8")
            logger.info("Successfully retrieved database password from Secret Manager")
            return password
        except Exception as e:
            logger.error(f"Failed to retrieve database password from Secret Manager: {e}")
            raise

    def _get_connection(self) -> Any:
        """Create a database connection using Cloud SQL Connector"""
        try:
            instance_connection_string = f"{self.project_id}:{self.region}:{self.instance_name}"
            conn = self.connector.connect(
                instance_connection_string,
                "pg8000",
                user=self.db_user,
                password=self._get_db_password(),
                db=self.database_name
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise

    def initialize(self):
        """Initialize database connection pool and create tables"""
        try:
            logger.info("Initializing Cloud SQL connector...")
            self.connector = Connector()

            # Create SQLAlchemy engine with connection pooling
            self.engine = create_engine(
                "postgresql+pg8000://",
                creator=self._get_connection,
                pool_size=5,
                max_overflow=2,
                pool_timeout=30,
                pool_recycle=1800,  # Recycle connections after 30 minutes
            )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database initialization complete. Tables created/verified.")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_session(self) -> Session:
        """Get a new database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.SessionLocal()

    def close(self):
        """Close database connections and cleanup"""
        try:
            if self.connector:
                self.connector.close()
                logger.info("Database connector closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connector: {e}")

    # CRUD Operations for Tax Extractions

    def create_tax_extraction(
        self,
        user_id: str,
        document_id: str,
        filing_status: Optional[str] = None,
        w2_wages: Optional[float] = None,
        total_deductions: Optional[float] = None,
        ira_distributions_total: Optional[float] = None,
        capital_gain_or_loss: Optional[float] = None
    ) -> TaxExtraction:
        """
        Create a new tax extraction record

        Args:
            user_id: User identifier
            document_id: Document identifier
            filing_status: Filing status (Single, Married, etc.)
            w2_wages: W2 wages amount
            total_deductions: Total deductions amount
            ira_distributions_total: IRA distributions total
            capital_gain_or_loss: Capital gain or loss amount

        Returns:
            Created TaxExtraction object
        """
        session = self.get_session()
        try:
            extraction = TaxExtraction(
                user_id=user_id,
                document_id=document_id,
                filing_status=filing_status,
                w2_wages=w2_wages,
                total_deductions=total_deductions,
                ira_distributions_total=ira_distributions_total,
                capital_gain_or_loss=capital_gain_or_loss
            )

            session.add(extraction)
            session.commit()
            session.refresh(extraction)

            logger.info(f"Created tax extraction record for document: {document_id}")
            return extraction
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create tax extraction: {e}")
            raise
        finally:
            session.close()

    def get_tax_extraction_by_document(self, document_id: str) -> Optional[TaxExtraction]:
        """Get tax extraction by document ID"""
        session = self.get_session()
        try:
            extraction = session.query(TaxExtraction).filter(
                TaxExtraction.document_id == document_id
            ).first()
            return extraction
        finally:
            session.close()

    def get_tax_extractions_by_user(self, user_id: str) -> list[TaxExtraction]:
        """Get all tax extractions for a user"""
        session = self.get_session()
        try:
            extractions = session.query(TaxExtraction).filter(
                TaxExtraction.user_id == user_id
            ).order_by(TaxExtraction.created_at.desc()).all()
            return extractions
        finally:
            session.close()

    def update_tax_extraction(
        self,
        document_id: str,
        **kwargs
    ) -> Optional[TaxExtraction]:
        """
        Update tax extraction record

        Args:
            document_id: Document identifier
            **kwargs: Fields to update

        Returns:
            Updated TaxExtraction object or None if not found
        """
        session = self.get_session()
        try:
            extraction = session.query(TaxExtraction).filter(
                TaxExtraction.document_id == document_id
            ).first()

            if not extraction:
                return None

            for key, value in kwargs.items():
                if hasattr(extraction, key):
                    setattr(extraction, key, value)

            extraction.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(extraction)
            logger.info(f"Updated tax extraction for document: {document_id}")
            return extraction
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update tax extraction: {e}")
            raise
        finally:
            session.close()

    def delete_tax_extraction(self, document_id: str) -> bool:
        """Delete tax extraction by document ID"""
        session = self.get_session()
        try:
            extraction = session.query(TaxExtraction).filter(
                TaxExtraction.document_id == document_id
            ).first()

            if not extraction:
                return False

            session.delete(extraction)
            session.commit()
            logger.info(f"Deleted tax extraction for document: {document_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete tax extraction: {e}")
            raise
        finally:
            session.close()

    # Convenience methods for extraction workflow

    def insert_extraction(self, user_id: str, document_id: str, extracted_fields: Dict[str, Any]) -> int:
        """
        Insert extraction data (convenience wrapper for create_tax_extraction)

        Args:
            user_id: User identifier
            document_id: Document identifier
            extracted_fields: Dictionary containing extracted field values

        Returns:
            Record ID of created extraction
        """
        extraction = self.create_tax_extraction(
            user_id=user_id,
            document_id=document_id,
            filing_status=extracted_fields.get("filing_status"),
            w2_wages=extracted_fields.get("w2_wages"),
            total_deductions=extracted_fields.get("total_deductions"),
            ira_distributions_total=extracted_fields.get("ira_distributions_total"),
            capital_gain_or_loss=extracted_fields.get("capital_gain_or_loss")
        )
        return extraction.id

    def get_extraction(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get extraction data as dictionary (convenience wrapper)

        Args:
            document_id: Document identifier

        Returns:
            Dictionary with extraction data or None if not found
        """
        extraction = self.get_tax_extraction_by_document(document_id)

        if not extraction:
            return None

        return {
            "id": extraction.id,
            "user_id": extraction.user_id,
            "document_id": extraction.document_id,
            "filing_status": extraction.filing_status,
            "w2_wages": extraction.w2_wages,
            "total_deductions": extraction.total_deductions,
            "ira_distributions_total": extraction.ira_distributions_total,
            "capital_gain_or_loss": extraction.capital_gain_or_loss,
            "extracted_at": extraction.created_at.isoformat() if extraction.created_at else None,
            "updated_at": extraction.updated_at.isoformat() if extraction.updated_at else None
        }

    # Document CRUD Operations

    def create_document(
        self,
        doc_id: str,
        user_id: str,
        filename: str,
        gcs_path: str,
        file_size: int,
        content_type: str
    ) -> Document:
        """
        Create a new document record

        Args:
            doc_id: Unique document identifier (UUID)
            user_id: User identifier
            filename: Original filename
            gcs_path: GCS path to uploaded file
            file_size: File size in bytes
            content_type: MIME type

        Returns:
            Created Document object
        """
        session = self.get_session()
        try:
            document = Document(
                id=doc_id,
                user_id=user_id,
                filename=filename,
                gcs_path=gcs_path,
                file_size=file_size,
                content_type=content_type,
                status='uploaded',
                extraction_status='not_started'
            )

            session.add(document)
            session.commit()
            session.refresh(document)

            logger.info(f"Created document record: {doc_id}")
            return document
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create document: {e}")
            raise
        finally:
            session.close()

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        session = self.get_session()
        try:
            document = session.query(Document).filter(
                Document.id == doc_id
            ).first()
            return document
        finally:
            session.close()

    def get_documents_by_user(self, user_id: str) -> list:
        """Get all documents for a user"""
        session = self.get_session()
        try:
            documents = session.query(Document).filter(
                Document.user_id == user_id
            ).order_by(Document.created_at.desc()).all()
            return documents
        finally:
            session.close()

    def get_all_documents(self) -> list:
        """Get all documents (for admin/maintenance)"""
        session = self.get_session()
        try:
            documents = session.query(Document).order_by(
                Document.created_at.desc()
            ).all()
            return documents
        finally:
            session.close()

    def update_document(
        self,
        doc_id: str,
        **kwargs
    ) -> Optional[Document]:
        """
        Update document record

        Args:
            doc_id: Document identifier
            **kwargs: Fields to update

        Returns:
            Updated Document object or None if not found
        """
        session = self.get_session()
        try:
            document = session.query(Document).filter(
                Document.id == doc_id
            ).first()

            if not document:
                return None

            for key, value in kwargs.items():
                if hasattr(document, key):
                    setattr(document, key, value)

            document.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(document)
            logger.info(f"Updated document: {doc_id}")
            return document
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update document: {e}")
            raise
        finally:
            session.close()

    def update_document_status(
        self,
        doc_id: str,
        status: str
    ) -> Optional[Document]:
        """Update document status (convenience method)"""
        return self.update_document(doc_id, status=status)

    def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID"""
        session = self.get_session()
        try:
            document = session.query(Document).filter(
                Document.id == doc_id
            ).first()

            if not document:
                return False

            session.delete(document)
            session.commit()
            logger.info(f"Deleted document: {doc_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete document: {e}")
            raise
        finally:
            session.close()

    # Helper methods for API compatibility (return dicts)

    def get_document_dict(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document as dictionary (API compatibility)"""
        document = self.get_document(doc_id)
        return document.to_dict() if document else None

    def get_documents_by_user_dict(self, user_id: str) -> list:
        """Get user's documents as dictionaries (API compatibility)"""
        documents = self.get_documents_by_user(user_id)
        return [doc.to_dict() for doc in documents]

    def get_all_documents_dict(self) -> list:
        """Get all documents as dictionaries (API compatibility)"""
        documents = self.get_all_documents()
        return [doc.to_dict() for doc in documents]
