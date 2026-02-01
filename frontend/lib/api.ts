/**
 * API Client for File Vault
 *
 * Calls Next.js API routes which proxy to the FastAPI backend with proper JWT tokens.
 */

// Use Next.js API routes as proxy (they handle JWT token creation)
const API_BASE_URL = "/api";

/**
 * API Error class for structured error handling
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Upload a document to the backend
 *
 * @param file - File to upload
 * @returns Promise with upload response
 */
export async function uploadDocument(file: File): Promise<any> {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || "Upload failed");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Upload failed");
  }
}

/**
 * Get list of documents for the current user
 *
 * @returns Promise with list of documents
 */
export async function getDocuments(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/documents`, {
      method: "GET",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || "Failed to fetch documents");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to fetch documents");
  }
}

/**
 * Get a specific document by ID
 *
 * @param documentId - Document ID
 * @returns Promise with document data
 */
export async function getDocumentById(documentId: string): Promise<any> {
  try {
    const url = `${API_BASE_URL}/documents/${documentId}`;

    const response = await fetch(url, {
      method: "GET",
    });


    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || "Failed to fetch document");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to fetch document");
  }
}

/**
 * Approve a document
 *
 * @param documentId - Document ID to approve
 * @returns Promise with approval response
 */
export async function approveDocument(documentId: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/approval/approve/${documentId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || "Failed to approve document");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to approve document");
  }
}

/**
 * Reject a document
 *
 * @param documentId - Document ID to reject
 * @param reason - Optional rejection reason
 * @returns Promise with rejection response
 */
export async function rejectDocument(documentId: string, reason?: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/approval/reject/${documentId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: reason ? JSON.stringify({ reason }) : undefined,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || "Failed to reject document");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to reject document");
  }
}

/**
 * Sync documents from GCS bucket
 *
 * Useful when documents exist in GCS but not showing in the app
 * (e.g., after server restart)
 *
 * @returns Promise with sync result
 */
export async function syncDocuments(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/documents/sync`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || "Failed to sync documents");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to sync documents");
  }
}

/**
 * Test PII detection on a document
 *
 * Combines Document AI OCR with Cloud DLP to detect PII and map to bounding boxes
 *
 * @param documentId - Document ID to test
 * @returns Promise with PII detection results
 */
export async function testPiiDetection(documentId: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/test-pii-detection?documentId=${documentId}`, {
      method: "POST",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || "Failed to detect PII");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to detect PII");
  }
}

/**
 * Test complete redaction pipeline on a document
 *
 * Runs OCR, PII detection, creates redacted PDF, and validates
 *
 * @param documentId - Document ID to redact
 * @returns Promise with redaction results and validation
 */
export async function testRedaction(documentId: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/test-redaction?documentId=${documentId}`, {
      method: "POST",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || "Failed to redact document");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to redact document");
  }
}

/**
 * Get download URL for redacted document
 *
 * @param documentId - Document ID
 * @returns Promise with signed download URL (valid for 1 hour)
 */
export async function getRedactedDownloadUrl(documentId: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/download-redacted/${documentId}`, {
      method: "GET",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || "Failed to get download URL");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to get download URL");
  }
}

/**
 * Wait for document redaction to complete
 *
 * Polls the document status every 2 seconds until redaction is complete
 *
 * @param documentId - Document ID to wait for
 * @param onProgress - Optional callback for progress updates
 * @returns Promise with final document status
 */
export async function waitForRedaction(
  documentId: string,
  onProgress?: (status: string) => void
): Promise<any> {
  const maxAttempts = 60; // 2 minutes max (2 sec * 60)
  let attempts = 0;

  while (attempts < maxAttempts) {
    try {
      const doc = await getDocumentById(documentId);

      // Call progress callback if provided
      if (onProgress) {
        onProgress(doc.status);
      }

      // Check if redaction is complete
      if (doc.status === "redacted") {
        return { success: true, document: doc };
      }

      if (doc.status === "redaction_failed") {
        return { success: false, document: doc, error: "Redaction failed" };
      }

      // Still processing, wait 2 seconds before next check
      await new Promise((resolve) => setTimeout(resolve, 2000));
      attempts++;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error("Failed to check redaction status");
    }
  }

  // Timeout
  throw new Error("Redaction timeout - took longer than 2 minutes");
}

/**
 * Get preview URL for a redacted document
 *
 * @param documentId - Document ID to preview
 * @returns Promise with signed URL and document metadata
 */
export async function getPreviewUrl(documentId: string): Promise<any> {
  try {
    const url = `${API_BASE_URL}/approval/preview/${documentId}`;

    const response = await fetch(url, {
      method: "GET",
    });


    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || errorData.detail || "Failed to get preview URL");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to get preview URL");
  }
}

/**
 * Get download URL for an approved document
 *
 * @param documentId - Document ID to download
 * @returns Promise with download URL and filename
 */
export async function getDownloadUrl(documentId: string): Promise<{ download_url: string; filename: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/approval/download/${documentId}`, {
      method: "GET",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || "Failed to get download URL");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to get download URL");
  }
}

/**
 * Download an approved document
 * Triggers browser download dialog
 *
 * @param documentId - Document ID to download
 */
export async function downloadDocument(documentId: string): Promise<void> {
  const { download_url, filename } = await getDownloadUrl(documentId);

  // Create temporary link and trigger download
  const link = document.createElement('a');
  link.href = download_url;
  link.download = filename;
  link.target = '_blank';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Get extraction status and fields for a document
 *
 * @param documentId - Document ID to get extraction for
 * @returns Promise with extraction data
 */
export async function getExtraction(documentId: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/approval/extractions/${documentId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        response.statusText,
        errorData.detail || errorData.error || "Failed to get extraction"
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error) {
      throw new ApiError(500, "Internal Error", error.message);
    }
    throw new ApiError(500, "Internal Error", "Failed to get extraction");
  }
}

/**
 * Delete a document completely (from staging, vault, and database)
 *
 * @param documentId - Document ID to delete
 * @returns Promise with deletion confirmation
 */
export async function deleteDocument(documentId: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        response.statusText,
        errorData.detail || errorData.error || "Failed to delete document"
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error) {
      throw new ApiError(500, "Internal Error", error.message);
    }
    throw new ApiError(500, "Internal Error", "Failed to delete document");
  }
}
