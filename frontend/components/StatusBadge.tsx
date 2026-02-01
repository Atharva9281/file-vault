import { DocumentStatus, statusConfig } from '@/lib/types';
import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: DocumentStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={cn(
        'inline-flex items-center px-3 py-1 rounded-lg text-sm font-medium',
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
