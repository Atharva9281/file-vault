import { cn } from '@/lib/utils';

interface StepCardProps {
  step: number;
  title: string;
  description: string;
  className?: string;
}

export function StepCard({ step, title, description, className }: StepCardProps) {
  return (
    <div className={cn('flex flex-col items-center text-center', className)}>
      <div className="w-14 h-14 rounded-full gradient-primary flex items-center justify-center mb-6 shadow-lg">
        <span className="text-xl font-bold text-primary-foreground">{step}</span>
      </div>

      <h3 className="text-lg font-semibold text-foreground mb-2">
        {title}
      </h3>

      <p className="text-muted-foreground text-sm leading-relaxed max-w-[200px]">
        {description}
      </p>
    </div>
  );
}
