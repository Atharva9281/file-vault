import Link from 'next/link';
import { FileText } from 'lucide-react';
import { StatusBadge } from '@/components/StatusBadge';

interface DocumentCardProps {
  document: any;
  onDownload?: (docId: string) => void;
  onDelete?: (docId: string) => void;
}

export function DocumentCard({ document, onDownload, onDelete }: DocumentCardProps) {
  const iconColors: Record<string, string> = {
    uploaded: 'bg-blue-50',
    redacting: 'bg-yellow-50',
    redacted: 'bg-green-50',
    approved: 'bg-purple-50',
    rejected: 'bg-red-50',
  };

  const iconTextColors: Record<string, string> = {
    uploaded: 'text-blue-600',
    redacting: 'text-yellow-600',
    redacted: 'text-green-600',
    approved: 'text-purple-600',
    rejected: 'text-red-600',
  };

  // Parse the created_at timestamp
  const createdDate = new Date(document.created_at);
  const formattedDate = createdDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div className="flex items-center justify-between p-5 bg-background border border-border rounded-xl hover:shadow-md transition-all duration-200 group">
      <div className="flex items-center gap-4">
        <div
          className={`w-12 h-12 rounded-xl flex items-center justify-center ${iconColors[document.status] || 'bg-muted'}`}
        >
          <FileText className={`w-6 h-6 ${iconTextColors[document.status] || 'text-muted-foreground'}`} />
        </div>

        <div>
          <h4 className="font-semibold text-foreground group-hover:text-primary transition-colors">
            {document.filename}
          </h4>
          <p className="text-sm text-muted-foreground">
            Uploaded {formattedDate}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <StatusBadge status={document.status} />

        {/* Show "Review" button for redacted documents (one-time approval) */}
        {document.status === 'redacted' && (
          <Link
            href={`/approval/${document.id}`}
            className="text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors px-4 py-2 rounded-lg"
          >
            Review
          </Link>
        )}

        {/* Show "View" and "Download" buttons for approved documents */}
        {document.status === 'approved' && (
          <>
            <Link
              href={`/view/${document.id}`}
              className="text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors px-4 py-2 rounded-lg"
            >
              View
            </Link>
            {onDownload && (
              <button
                onClick={() => onDownload(document.id)}
                className="text-sm font-medium bg-green-600 hover:bg-green-700 text-white transition-colors px-4 py-2 rounded-lg"
              >
                Download
              </button>
            )}
          </>
        )}

        {/* For other statuses (uploaded, redacting, etc.), show disabled state */}
        {document.status !== 'redacted' && document.status !== 'approved' && (
          <button
            disabled
            className="text-sm font-medium text-muted-foreground px-4 py-2 rounded-lg cursor-not-allowed opacity-50"
          >
            {document.status === 'redacting' ? 'Processing...' : 'Pending'}
          </button>
        )}

        {/* Delete button - always available */}
        {onDelete && (
          <button
            onClick={() => onDelete(document.id)}
            className="text-sm font-medium bg-background hover:bg-muted text-red-600 border-2 border-red-200 hover:border-red-300 transition-colors px-4 py-2 rounded-lg"
            title="Delete document"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}
