"use client";

import { useEffect, useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { Navbar } from '@/components/Navbar';
import { UploadZone } from '@/components/UploadZone';
import { DocumentCard } from '@/components/DocumentCard';
import { DeleteConfirmModal } from '@/components/DeleteConfirmModal';
import { getDocuments, downloadDocument as apiDownloadDocument, deleteDocument } from '@/lib/api';
import { FileText } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const { data: session } = useSession();
  const router = useRouter();
  const [documents, setDocuments] = useState<any[]>([]);
  const [pendingDocs, setPendingDocs] = useState<any[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<any>(null);

  // Fetch documents when component mounts
  useEffect(() => {
    fetchDocuments();
  }, []);

  // Auto-redirect to approval page when document is ready
  useEffect(() => {
    if (!isLoadingDocuments && pendingDocs.length > 0) {
      // Redirect to first pending document for approval
      router.push(`/approval/${pendingDocs[0].id}`);
    }
  }, [pendingDocs, isLoadingDocuments, router]);

  const fetchDocuments = useCallback(async () => {
    try {
      setIsLoadingDocuments(true);
      const docs = await getDocuments();
      // Filter to only show approved documents in dashboard
      // Other statuses (uploaded, redacting, redacted) are for approval workflow
      const approvedDocs = docs.filter((doc: any) => doc.status === 'approved');
      const pending = docs.filter((doc: any) => doc.status === 'redacted');
      setDocuments(approvedDocs);
      setPendingDocs(pending);
      setPendingCount(pending.length);
    } catch (err) {
      setDocuments([]);
      setPendingDocs([]);
      setPendingCount(0);
    } finally {
      setIsLoadingDocuments(false);
    }
  }, []);

  const handleUploadComplete = useCallback(() => {
    // Refresh documents list after successful upload
    fetchDocuments();
  }, [fetchDocuments]);

  const handleDownload = useCallback(async (docId: string) => {
    try {
      await apiDownloadDocument(docId);
      toast.success('Download started!');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to download document';
      toast.error(errorMsg);
    }
  }, []);

  const handleDelete = useCallback((docId: string) => {
    const doc = documents.find(d => d.id === docId);
    if (doc) {
      setDocumentToDelete(doc);
      setDeleteModalOpen(true);
    }
  }, [documents]);

  const confirmDelete = useCallback(async () => {
    if (!documentToDelete) return;

    try {
      await deleteDocument(documentToDelete.id);
      toast.success('Document deleted successfully!');
      // Refresh documents list
      fetchDocuments();
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete document';
      toast.error(errorMsg);
    } finally {
      setDocumentToDelete(null);
    }
  }, [documentToDelete, fetchDocuments]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 py-16">
        {/* Page Header */}
        <div className="mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold text-foreground mb-3">
            {session?.user?.name ? `Welcome, ${session.user.name.split(' ')[0]}` : 'Documents'}
          </h1>
          <p className="text-lg text-muted-foreground">
            Upload and manage your financial documents securely
          </p>
        </div>

        {/* Upload Zone */}
        <div className="mb-20">
          <UploadZone onUploadComplete={handleUploadComplete} />
        </div>


        {/* Documents List */}
        <section>
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl font-bold text-foreground">Recent Documents</h2>
            <span className="text-sm font-medium text-muted-foreground bg-muted px-4 py-2 rounded-full">
              {documents.length} {documents.length === 1 ? 'document' : 'documents'}
            </span>
          </div>

          {isLoadingDocuments ? (
            <div className="bg-card border border-border rounded-3xl p-20 text-center shadow-card">
              <div className="w-16 h-16 border-4 border-foreground border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
              <p className="text-lg text-muted-foreground">Loading documents...</p>
            </div>
          ) : documents.length > 0 ? (
            <div className="space-y-4">
              {documents.map((doc) => (
                <DocumentCard key={doc.id} document={doc} onDownload={handleDownload} onDelete={handleDelete} />
              ))}
            </div>
          ) : (
            <div className="bg-card border border-border rounded-3xl p-20 text-center shadow-card">
              <div className="w-24 h-24 rounded-3xl bg-muted flex items-center justify-center mx-auto mb-8">
                <FileText className="w-12 h-12 text-muted-foreground" />
              </div>
              <h3 className="text-2xl font-bold text-foreground mb-3">No documents yet</h3>
              <p className="text-lg text-muted-foreground">
                Upload your first document above to get started
              </p>
            </div>
          )}
        </section>
      </main>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        documentName={documentToDelete?.filename || ''}
      />
    </div>
  );
}
