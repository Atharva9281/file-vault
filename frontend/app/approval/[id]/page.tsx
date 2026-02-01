"use client";

import { use, useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  approveDocument,
  rejectDocument,
  getDocumentById,
  getPreviewUrl,
  downloadDocument,
  getExtraction,
  ApiError
} from '@/lib/api';
import { signOut } from 'next-auth/react';
import toast from 'react-hot-toast';
import dynamic from 'next/dynamic';
import { ConfirmModal } from '@/components/ConfirmModal';
import { ExtractionCard } from '@/components/ExtractionCard';

// Dynamic import to avoid SSR issues with react-pdf
const PDFViewer = dynamic(() => import('@/components/PDFViewer'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center min-h-[600px]">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
    </div>
  )
});

export default function Approval({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [document, setDocument] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [isApproveModalOpen, setIsApproveModalOpen] = useState(false);
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);

  // Extraction state - shown after approval
  const [showExtraction, setShowExtraction] = useState(false);
  const [extractionData, setExtractionData] = useState<any>(null);
  const [extractionStatus, setExtractionStatus] = useState<'extracting' | 'completed' | 'failed' | 'not_started'>('not_started');
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const loadPreview = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Get document metadata
      const docData = await getDocumentById(id);

      // Check if document is still redacting
      if (docData.status === 'redacting') {
        setError('Document is still being redacted. Please wait...');
        // Poll again after 2 seconds
        setTimeout(() => {
          loadPreview();
        }, 2000);
        return;
      }

      // Check if document is ready for approval
      if (docData.status === 'redacted') {
        // Use PDF proxy endpoint instead of direct signed URL
        const proxyUrl = `/api/approval/pdf/${id}`;
        setPreviewUrl(proxyUrl);
        setDocument(docData);
      } else if (docData.status === 'redaction_failed') {
        setError('Document redaction failed. Please upload again.');
      } else if (docData.status === 'uploaded') {
        setError('Document has not been redacted yet. Please wait for redaction to complete.');
      } else if (docData.status === 'approved') {
        // Document is already approved, redirect immediately to view page
        router.push(`/view/${id}`);
        return;
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Failed to load preview: ${err.message}`);
      } else {
        setError('Failed to load preview. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  useEffect(() => {
    if (id) {
      loadPreview();
    }
  }, [id, loadPreview]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const loadExtraction = useCallback(async () => {
    try {
      const extraction = await getExtraction(id);

      // Update extraction state
      setExtractionStatus(extraction.status);

      if (extraction.status === 'completed' && extraction.extracted_fields) {
        setExtractionData(extraction.extracted_fields);
        setExtractionError(null);

        // Stop polling if it's running
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }

        // Redirect immediately to view page
        router.push(`/view/${id}`);
      } else if (extraction.status === 'failed') {
        setExtractionError(extraction.error || 'Extraction failed');
        toast.error('Tax field extraction failed');

        // Stop polling if it's running
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }

        // Redirect immediately to view page even on failure
        router.push(`/view/${id}`);
      } else if (extraction.status === 'extracting') {
        // Start polling if not already polling
        if (!pollingIntervalRef.current) {
          pollingIntervalRef.current = setInterval(() => {
            loadExtraction();
          }, 2000); // Poll every 2 seconds

          // Set timeout to stop polling after 60 seconds
          setTimeout(() => {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
              setExtractionStatus('failed');
              setExtractionError('Extraction timeout - took longer than 60 seconds');
              toast.error('Extraction timeout');

              // Redirect immediately to view page
              router.push(`/view/${id}`);
            }
          }, 60000);
        }
      }
    } catch (err) {
      // Don't stop the flow on extraction errors
      if (err instanceof ApiError && err.status !== 404) {
        setExtractionError('Failed to load extraction data');
      }
    }
  }, [id, router]);

  const handleApprove = useCallback(async () => {
    if (!document) return;

    try {
      setIsProcessing(true);
      setError(null);

      await approveDocument(document.id);

      toast.success('Document approved! Extracting tax fields...');

      // Stop processing and show extraction card
      setIsProcessing(false);
      setShowExtraction(true);
      setExtractionStatus('extracting');

      // Wait a moment, then start polling for extraction
      setTimeout(() => {
        loadExtraction();
      }, 1000);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Approval failed: ${err.message}`);
        toast.error(`Approval failed: ${err.message}`);
      } else {
        const errorMsg = err instanceof Error ? err.message : 'Approval failed. Please try again.';
        setError(errorMsg);
        toast.error(errorMsg);
      }
      setIsProcessing(false);
    }
  }, [document, loadExtraction]);

  const handleReject = useCallback(async () => {
    if (!document) return;

    try {
      setIsProcessing(true);
      setError(null);

      await rejectDocument(document.id);

      toast.success('Document rejected and deleted');

      // Redirect to dashboard after short delay
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Rejection failed: ${err.message}`);
        toast.error(`Rejection failed: ${err.message}`);
      } else {
        const errorMsg = err instanceof Error ? err.message : 'Rejection failed. Please try again.';
        setError(errorMsg);
        toast.error(errorMsg);
      }
      setIsProcessing(false);
    }
  }, [document, router]);

  const handleDownload = useCallback(async () => {
    try {
      setDownloading(true);
      await downloadDocument(id);
      toast.success('Download started!');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to download document';
      toast.error(errorMsg);
    } finally {
      setDownloading(false);
    }
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-muted/20 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading preview...</p>
        </div>
      </div>
    );
  }

  if (error || !previewUrl) {
    return (
      <div className="min-h-screen bg-muted/20 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-foreground mb-2">Unable to Load Preview</h2>
          <p className="text-muted-foreground mb-6">{error}</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="bg-primary text-primary-foreground px-6 py-3 rounded-lg font-semibold hover:bg-primary/90"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/20">
      {/* Navbar */}
      <nav className="bg-background border-b border-border">
        <div className="max-w-full mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <svg
                className="w-5 h-5 text-primary-foreground"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <span className="text-xl font-semibold text-foreground">File Vault</span>
          </div>
          <button
            onClick={() => signOut()}
            className="text-muted-foreground hover:text-foreground font-medium text-sm transition-colors"
          >
            Sign out
          </button>
        </div>
      </nav>

      {/* Main Content - SmallPDF Style Layout */}
      <div className="flex h-[calc(100vh-73px)]">

        {/* LEFT SIDE: PDF Viewer (75%) - Scrollable */}
        <div className="w-[75%] bg-muted/50 overflow-y-auto">
          <div className="p-3">
            {/* Back button */}
            <button
              onClick={() => router.push('/dashboard')}
              className="text-primary hover:text-primary/80 font-semibold mb-3 inline-flex items-center transition-colors text-sm"
            >
              ← Back to Dashboard
            </button>

            {/* PDF Viewer - All pages render with continuous scroll */}
            <PDFViewer fileUrl={previewUrl} />
          </div>
        </div>

        {/* RIGHT SIDE: Action Panel (25%) - Fixed, with Approve/Reject */}
        <div className="w-[25%] bg-background border-l border-border overflow-y-auto">
          <div className="p-4 space-y-4">

            {/* Document Info */}
            <div>
              <h2 className="text-lg font-bold text-foreground mb-3">Review Document</h2>

              <div className="space-y-2.5">
                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">Filename</span>
                  <p className="font-semibold text-foreground text-sm mt-0.5">{document?.filename}</p>
                </div>

                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">Uploaded</span>
                  <p className="font-semibold text-foreground text-sm mt-0.5">
                    {document?.created_at ? new Date(document.created_at).toLocaleString() : 'N/A'}
                  </p>
                </div>

                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">Status</span>
                  <div className="mt-1">
                    <span className="inline-block px-2 py-0.5 bg-blue-500 text-white rounded text-xs font-semibold">
                      Awaiting Review
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">PII Redacted</span>
                  <p className="font-semibold text-foreground text-sm mt-0.5">
                    {document?.pii_count || 0} items removed
                  </p>
                </div>
              </div>
            </div>

            {/* Info Box */}
            <div className="bg-blue-500 rounded-xl p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <span className="text-2xl">ℹ️</span>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-semibold text-white">Review Instructions</h3>
                  <p className="text-sm text-white mt-1">
                    Scroll through the entire document on the left to verify all PII has been properly redacted.
                    Black boxes indicate redacted information.
                  </p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3">
              {document?.status === 'approved' ? (
                // Show download button if already approved
                <>
                  <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 text-center">
                    <div className="text-3xl mb-2">✓</div>
                    <p className="text-green-800 dark:text-green-300 font-semibold">Document Approved</p>
                    <p className="text-sm text-green-600 dark:text-green-400 mt-1">Stored in your secure vault</p>
                  </div>

                  <button
                    onClick={handleDownload}
                    disabled={downloading}
                    className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground font-semibold py-4 rounded-xl transition-colors flex items-center justify-center space-x-2"
                  >
                    {downloading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Downloading...</span>
                      </>
                    ) : (
                      <>
                        <span className="text-xl">⬇</span>
                        <span>Download Document</span>
                      </>
                    )}
                  </button>
                </>
              ) : (
                // Show approve/reject buttons if not yet approved
                <>
                  <button
                    onClick={() => setIsApproveModalOpen(true)}
                    disabled={isProcessing}
                    className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-xl transition-colors flex items-center justify-center space-x-2"
                  >
                    {isProcessing ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <span className="text-xl">✓</span>
                        <span>Approve Document</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setIsRejectModalOpen(true)}
                    disabled={isProcessing}
                    className="w-full bg-background hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-red-600 font-semibold py-4 rounded-xl border-2 border-red-200 hover:border-red-300 transition-colors flex items-center justify-center space-x-2"
                  >
                    {isProcessing ? (
                      <>
                        <div className="w-5 h-5 border-2 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <span className="text-xl">✕</span>
                        <span>Reject Document</span>
                      </>
                    )}
                  </button>
                </>
              )}
            </div>

            {/* Warning */}
            {!showExtraction && (
              <div className="bg-red-500 rounded-xl p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <span className="text-xl">⚠️</span>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-white">
                      <strong>Important:</strong> Approving this document will move it to your secure vault.
                      Rejecting will permanently delete it.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Tax Extraction Card - shown after approval */}
            {showExtraction && (
              <ExtractionCard
                extractedFields={extractionData || {
                  filing_status: null,
                  w2_wages: null,
                  total_deductions: null,
                  ira_distributions_total: null,
                  capital_gain_or_loss: null,
                }}
                extractedAt={document?.extracted_at}
                status={extractionStatus}
                error={extractionError || undefined}
              />
            )}

          </div>
        </div>
      </div>

      {/* Confirmation Modals */}
      <ConfirmModal
        isOpen={isApproveModalOpen}
        onClose={() => setIsApproveModalOpen(false)}
        onConfirm={handleApprove}
        title="Approve Document"
        message="Are you sure you want to approve this document? It will be moved to your secure vault."
        confirmText="Approve"
        cancelText="Cancel"
        confirmColor="green"
      />

      <ConfirmModal
        isOpen={isRejectModalOpen}
        onClose={() => setIsRejectModalOpen(false)}
        onConfirm={handleReject}
        title="Reject Document"
        message="Are you sure you want to reject this document? It will be permanently deleted and cannot be recovered."
        confirmText="Reject"
        cancelText="Cancel"
        confirmColor="red"
      />
    </div>
  );
}
