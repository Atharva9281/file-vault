interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  documentName: string;
}

export function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  documentName,
}: DeleteConfirmModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-background border border-border rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6 animate-in fade-in zoom-in duration-200">
        {/* Icon */}
        <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-4">
          <span className="text-2xl">🗑️</span>
        </div>

        {/* Title */}
        <h3 className="text-xl font-bold text-center text-foreground mb-2">
          Delete Document?
        </h3>

        {/* Message */}
        <p className="text-center text-muted-foreground mb-6">
          Are you sure you want to delete <span className="font-semibold text-foreground">"{documentName}"</span>?
          This action cannot be undone and will remove the document from all storage locations.
        </p>

        {/* Warning */}
        <div className="bg-red-600 rounded-lg p-3 mb-6">
          <p className="text-sm text-white flex items-start">
            <span className="mr-2">⚠️</span>
            <span>This will permanently delete the document from staging, vault, and database.</span>
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 rounded-xl border-2 border-border hover:bg-muted transition-colors font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className="flex-1 px-4 py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white transition-colors font-semibold"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
