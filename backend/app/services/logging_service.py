from google.cloud import logging as cloud_logging
from datetime import datetime
from typing import Dict, Optional, Any
import json

class AuditLoggingService:
    def __init__(self, project_id: str):
        """
        Initialize audit logging service.

        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id

        # Initialize Cloud Logging client
        self.client = cloud_logging.Client(project=project_id)
        self.logger = self.client.logger("file-vault-audit")

    def log_event(
        self,
        event_type: str,
        user_id: str,
        severity: str = "INFO",
        document_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit event to Cloud Logging.

        Args:
            event_type: Type of event (e.g., "document_uploaded", "document_approved")
            user_id: User who performed the action
            severity: Log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            document_id: Document ID (if applicable)
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
        """
        try:
            # Build structured log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type,
                "user_id": user_id,
                "severity": severity
            }

            if document_id:
                log_entry["document_id"] = document_id

            if ip_address:
                log_entry["ip_address"] = ip_address

            if user_agent:
                log_entry["user_agent"] = user_agent

            if details:
                log_entry["details"] = details

            # Write to Cloud Logging
            self.logger.log_struct(log_entry, severity=severity)

        except Exception as e:
            # Never fail the operation due to logging error
            pass

    # Convenience methods for common events

    def log_document_uploaded(self, user_id: str, document_id: str, filename: str,
                             file_size: int, ip_address: Optional[str] = None):
        """Log document upload event"""
        self.log_event(
            event_type="document_uploaded",
            user_id=user_id,
            document_id=document_id,
            ip_address=ip_address,
            details={
                "filename": filename,
                "file_size_bytes": file_size,
                "action": "File uploaded to staging bucket"
            }
        )

    def log_redaction_started(self, user_id: str, document_id: str, filename: str):
        """Log redaction start event"""
        self.log_event(
            event_type="redaction_started",
            user_id=user_id,
            document_id=document_id,
            details={
                "filename": filename,
                "action": "PII redaction process started"
            }
        )

    def log_redaction_completed(self, user_id: str, document_id: str,
                               pii_items_found: int, pii_items_redacted: int):
        """Log redaction completion event"""
        self.log_event(
            event_type="redaction_completed",
            user_id=user_id,
            document_id=document_id,
            details={
                "pii_items_found": pii_items_found,
                "pii_items_redacted": pii_items_redacted,
                "action": "PII redaction completed successfully"
            }
        )

    def log_redaction_failed(self, user_id: str, document_id: str, error: str):
        """Log redaction failure event"""
        self.log_event(
            event_type="redaction_failed",
            user_id=user_id,
            document_id=document_id,
            severity="ERROR",
            details={
                "error": error,
                "action": "PII redaction failed"
            }
        )

    def log_document_approved(self, user_id: str, document_id: str,
                             vault_path: str, ip_address: Optional[str] = None):
        """Log document approval event"""
        self.log_event(
            event_type="document_approved",
            user_id=user_id,
            document_id=document_id,
            ip_address=ip_address,
            details={
                "vault_path": vault_path,
                "action": "Document approved and moved to vault"
            }
        )

    def log_document_rejected(self, user_id: str, document_id: str,
                             filename: str = None, ip_address: Optional[str] = None):
        """Log document rejection event"""
        details = {"action": "Document rejected and deleted from staging"}
        if filename:
            details["filename"] = filename

        self.log_event(
            event_type="document_rejected",
            user_id=user_id,
            document_id=document_id,
            severity="WARNING",
            ip_address=ip_address,
            details=details
        )

    def log_extraction_started(self, user_id: str, document_id: str,
                               vault_path: str = None):
        """Log field extraction start event"""
        details = {"action": "Tax field extraction started"}
        if vault_path:
            details["vault_path"] = vault_path

        self.log_event(
            event_type="extraction_started",
            user_id=user_id,
            document_id=document_id,
            details=details
        )

    def log_extraction_completed(self, user_id: str, document_id: str,
                                extracted_fields: Dict[str, Any] = None,
                                fields_extracted: int = None):
        """Log field extraction completion event"""
        details = {"action": "Tax fields extracted and saved to database"}

        if extracted_fields:
            details["extracted_fields"] = extracted_fields
            details["fields_extracted"] = len(extracted_fields)
        elif fields_extracted:
            details["fields_extracted"] = fields_extracted

        self.log_event(
            event_type="extraction_completed",
            user_id=user_id,
            document_id=document_id,
            details=details
        )

    def log_extraction_failed(self, user_id: str, document_id: str, error: str):
        """Log field extraction failure event"""
        self.log_event(
            event_type="extraction_failed",
            user_id=user_id,
            document_id=document_id,
            severity="ERROR",
            details={
                "error": error,
                "action": "Tax field extraction failed"
            }
        )

    def log_document_downloaded(self, user_id: str, document_id: str,
                               filename: str, vault_path: str = None,
                               ip_address: Optional[str] = None):
        """Log document download event"""
        details = {
            "filename": filename,
            "action": "Document downloaded from vault"
        }
        if vault_path:
            details["vault_path"] = vault_path

        self.log_event(
            event_type="document_downloaded",
            user_id=user_id,
            document_id=document_id,
            ip_address=ip_address,
            details=details
        )

    def log_document_previewed(self, user_id: str, document_id: str,
                              filename: str, redacted_path: str = None,
                              ip_address: Optional[str] = None):
        """Log document preview event"""
        details = {
            "filename": filename,
            "action": "Document previewed for approval"
        }
        if redacted_path:
            details["redacted_path"] = redacted_path

        self.log_event(
            event_type="document_previewed",
            user_id=user_id,
            document_id=document_id,
            ip_address=ip_address,
            details=details
        )

    def log_database_write(self, user_id: str, document_id: str,
                          operation: str = None, record_id: int = None,
                          table: str = None, table_name: str = None):
        """Log database write event"""
        _table = table or table_name or "unknown"
        details = {
            "table_name": _table,
            "action": f"Data written to {_table} table"
        }
        if operation:
            details["operation"] = operation
        if record_id:
            details["record_id"] = record_id

        self.log_event(
            event_type="database_write",
            user_id=user_id,
            document_id=document_id,
            details=details
        )

    def log_file_moved(self, user_id: str, document_id: str,
                      source_path: str, destination_path: str,
                      operation: str = None):
        """Log file movement event"""
        details = {
            "source": source_path,
            "destination": destination_path,
            "action": "File moved from staging to vault"
        }
        if operation:
            details["operation"] = operation

        self.log_event(
            event_type="file_moved",
            user_id=user_id,
            document_id=document_id,
            details=details
        )

    def log_file_deleted(self, user_id: str, document_id: str,
                        file_path: str, file_type: str = None,
                        reason: str = None):
        """Log file deletion event"""
        details = {
            "file_path": file_path,
            "action": "File deleted from storage"
        }
        if file_type:
            details["file_type"] = file_type
        if reason:
            details["reason"] = reason

        self.log_event(
            event_type="file_deleted",
            user_id=user_id,
            document_id=document_id,
            severity="WARNING",
            details=details
        )

    def log_unauthorized_access(self, user_id: str, document_id: str,
                               reason: str, ip_address: Optional[str] = None):
        """Log unauthorized access attempt"""
        self.log_event(
            event_type="unauthorized_access",
            user_id=user_id,
            document_id=document_id,
            severity="WARNING",
            ip_address=ip_address,
            details={
                "reason": reason,
                "action": "Access denied - unauthorized attempt"
            }
        )

    def log_user_login(self, user_id: str, user_email: str,
                      ip_address: Optional[str] = None):
        """Log user login event"""
        self.log_event(
            event_type="user_login",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "user_email": user_email,
                "action": "User logged in successfully"
            }
        )

    def log_authentication_failed(self, error: str,
                                 ip_address: Optional[str] = None):
        """Log authentication failure"""
        self.log_event(
            event_type="authentication_failed",
            user_id="unknown",
            severity="WARNING",
            ip_address=ip_address,
            details={
                "error": error,
                "action": "Authentication failed"
            }
        )
