"""
Database service for Cloud SQL PostgreSQL connections
Handles tax extraction data storage and retrieval
"""

import os
import sqlalchemy
from google.cloud.sql.connector import Connector
from google.cloud import secretmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, MetaData, Table
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
