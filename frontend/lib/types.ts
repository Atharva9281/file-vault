export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

export type DocumentStatus =
  | 'uploaded'
  | 'redacting'
  | 'redacted'
  | 'approved'
  | 'rejected';

export interface Document {
  id: string;
  userId: string;
  filename: string;
  status: DocumentStatus;
  fileSize?: number;
  mimeType?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface TaxExtraction {
  filingStatus: string;
  w2Wages: number;
  totalDeductions: number;
  iraDistributions: number;
  capitalGainLoss: number;
}

export const statusConfig: Record<DocumentStatus, { label: string; className: string }> = {
  uploaded: {
    label: 'Uploaded',
    className: 'bg-blue-50 text-blue-700',
  },
  redacting: {
    label: 'Processing',
    className: 'bg-yellow-50 text-yellow-700',
  },
  redacted: {
    label: 'Ready for Review',
    className: 'bg-green-50 text-green-700',
  },
  approved: {
    label: 'Approved',
    className: 'bg-purple-50 text-purple-700',
  },
  rejected: {
    label: 'Rejected',
    className: 'bg-red-50 text-red-700',
  },
};
