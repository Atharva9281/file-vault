"use client";

import { use, useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  getDocumentById,
  getDownloadUrl,
  getExtraction,
  ApiError
} from '@/lib/api';
import { signOut } from 'next-auth/react';
import toast from 'react-hot-toast';
import dynamic from 'next/dynamic';
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

export default function ViewDocument({
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

  // Extraction state
  const [extractionData, setExtractionData] = useState<any>(null);
  const [extractionStatus, setExtractionStatus] = useState<'extracting' | 'completed' | 'failed' | 'not_started'>('not_started');
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (id) {
      loadPreview();
      loadExtraction();
    }
  }, [id]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const loadPreview = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Get document metadata
      const docData = await getDocumentById(id);

      // Check if document is approved (only approved documents can be viewed)
      if (docData.status !== 'approved') {
        setError(`Document cannot be viewed. Only approved documents can be viewed. Current status: ${docData.status}`);
        return;
      }

      // Use PDF proxy for viewing approved documents from vault
      const proxyUrl = `/api/view/pdf/${id}`;
      setPreviewUrl(proxyUrl);
      setDocument(docData);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Failed to load preview: ${err.message}`);
      } else {
        setError('Failed to load preview. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

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
      } else if (extraction.status === 'failed') {
        setExtractionError(extraction.error || 'Extraction failed');
        // Stop polling if it's running
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
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
            }
          }, 60000);
        }
      }
    } catch (err) {
      // Don't show error if extraction hasn't started yet
      if (err instanceof ApiError && err.status !== 404) {
        setExtractionError('Failed to load extraction data');
      }
    }
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-muted/20 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error || !previewUrl) {
    return (
      <div className="min-h-screen bg-muted/20 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-foreground mb-2">Unable to Load Document</h2>
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

        {/* RIGHT SIDE: Info Panel (25%) - Read-only, No Approval Buttons */}
        <div className="w-[25%] bg-background border-l border-border overflow-y-auto">
          <div className="p-4 space-y-3">

            {/* Document Info */}
            <div>
              <h2 className="text-lg font-bold text-foreground mb-3">Document Details</h2>

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
                    <span className="inline-block px-2 py-0.5 bg-green-500/10 text-green-700 dark:text-green-400 rounded text-xs font-semibold">
                      {document?.status}
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

            {/* Tax Extraction Card - Always show for approved documents */}
            {document?.status === 'approved' && (
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
    </div>
  );
}
