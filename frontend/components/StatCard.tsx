import { cn } from '@/lib/utils';

interface StatCardProps {
  value: string;
  label: string;
  className?: string;
}

export function StatCard({ value, label, className }: StatCardProps) {
  return (
    <div
      className={cn(
        'bg-background border border-border rounded-2xl p-10 text-center shadow-card hover:shadow-lg hover:-translate-y-1 transition-all duration-300',
        className
      )}
    >
      <div className="text-4xl sm:text-5xl font-bold text-foreground mb-3 tracking-tight">{value}</div>
      <div className="text-muted-foreground text-base font-medium">{label}</div>
    </div>
  );
}
