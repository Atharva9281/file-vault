interface ExtractionCardProps {
  extractedFields: {
    filing_status: string | null;
    w2_wages: number | null;
    total_deductions: number | null;
    ira_distributions_total: number | null;
    capital_gain_or_loss: number | null;
  };
  extractedAt?: string;
  status?: 'extracting' | 'completed' | 'failed' | 'not_started';
  error?: string;
}

export function ExtractionCard({ extractedFields, extractedAt, status, error }: ExtractionCardProps) {
  // Show loading state
  if (status === 'extracting') {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-6">
        <div className="flex items-center space-x-3">
          <div className="w-5 h-5 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin"></div>
          <div>
            <h3 className="text-sm font-semibold text-yellow-900 dark:text-yellow-300">Extracting Tax Fields...</h3>
            <p className="text-xs text-yellow-700 dark:text-yellow-400 mt-1">
              This may take up to 30 seconds
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (status === 'failed') {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6">
        <div className="flex">
          <div className="flex-shrink-0">
            <span className="text-2xl">⚠️</span>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-semibold text-red-900 dark:text-red-300">Extraction Failed</h3>
            <p className="text-xs text-red-700 dark:text-red-400 mt-1">
              {error || 'Unable to extract tax fields from this document'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Show not started state
  if (status === 'not_started') {
    return (
      <div className="bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-800 rounded-xl p-6">
        <div className="flex">
          <div className="flex-shrink-0">
            <span className="text-2xl">📋</span>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-300">No Extraction Yet</h3>
            <p className="text-xs text-gray-700 dark:text-gray-400 mt-1">
              Document needs to be approved first
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Format currency
  const formatCurrency = (value: number | null) => {
    if (value === null) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return '';
    try {
      return new Date(dateString).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden shadow-sm">
      {/* Header - Stripe style */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-800">
        <h3 className="text-xs font-semibold text-gray-900 dark:text-white uppercase tracking-wide">Tax Information</h3>
        <span className="px-1.5 py-0.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800 rounded text-[10px] font-medium">Extracted</span>
      </div>

      {/* Extracted Fields - Stripe minimal style */}
      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {/* Filing Status */}
        <div className="px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-0.5 uppercase tracking-wider">Filing Status</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {extractedFields.filing_status || 'N/A'}
          </p>
        </div>

        {/* W-2 Wages */}
        <div className="px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-0.5 uppercase tracking-wider">W-2 Wages</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {formatCurrency(extractedFields.w2_wages)}
          </p>
        </div>

        {/* Total Deductions */}
        <div className="px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-0.5 uppercase tracking-wider">Total Deductions</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {formatCurrency(extractedFields.total_deductions)}
          </p>
        </div>

        {/* IRA Distributions */}
        <div className="px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-0.5 uppercase tracking-wider">IRA Distributions</p>
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {formatCurrency(extractedFields.ira_distributions_total)}
          </p>
        </div>

        {/* Capital Gain/Loss */}
        <div className="px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-0.5 uppercase tracking-wider">Capital Gain/Loss</p>
          <p className={`text-sm font-medium ${
            extractedFields.capital_gain_or_loss && extractedFields.capital_gain_or_loss < 0
              ? 'text-red-600 dark:text-red-400'
              : 'text-green-600 dark:text-green-400'
          }`}>
            {formatCurrency(extractedFields.capital_gain_or_loss)}
          </p>
        </div>
      </div>
    </div>
  );
}
