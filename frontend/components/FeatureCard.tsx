import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface FeatureCardProps {
  icon: ReactNode;
  iconBgClass: string;
  title: string;
  description: string;
  className?: string;
}

export function FeatureCard({ icon, iconBgClass, title, description, className }: FeatureCardProps) {
  return (
    <div
      className={cn(
        'bg-background border border-border rounded-2xl p-10 shadow-card hover:shadow-md transition-all duration-300',
        className
      )}
    >
      <div
        className={cn(
          'w-16 h-16 rounded-xl flex items-center justify-center mb-6',
          iconBgClass
        )}
      >
        {icon}
      </div>

      <h3 className="text-xl font-semibold text-foreground mb-3">
        {title}
      </h3>

      <p className="text-muted-foreground leading-relaxed">
        {description}
      </p>
    </div>
  );
}
