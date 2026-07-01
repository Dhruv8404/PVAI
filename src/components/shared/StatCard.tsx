import React from 'react';
import { Card, CardContent } from '../ui/Card';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: {
    value: string;
    direction: 'up' | 'down' | 'neutral';
  };
  description?: string;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  trend,
  description,
  className = ''
}) => {
  return (
    <Card hoverable className={`overflow-hidden relative ${className}`}>
      <CardContent className="p-5">
        <div className="flex justify-between items-start">
          <span className="text-xs font-semibold text-slate-500 dark:text-zinc-400 uppercase tracking-wider">
            {title}
          </span>
          <div className="p-2 rounded-lg bg-slate-50 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 border border-slate-100 dark:border-zinc-800/80">
            {icon}
          </div>
        </div>

        <div className="mt-3">
          <span className="text-2xl font-bold text-slate-900 dark:text-zinc-50 tracking-tight">
            {value}
          </span>
        </div>

        {(trend || description) && (
          <div className="mt-3 flex items-center gap-1.5 text-xs">
            {trend && (
              <span className={`inline-flex items-center gap-0.5 font-semibold ${
                trend.direction === 'up' ? 'text-emerald-600 dark:text-emerald-400' :
                trend.direction === 'down' ? 'text-rose-600 dark:text-rose-400' :
                'text-slate-500 dark:text-zinc-400'
              }`}>
                {trend.direction === 'up' && <ArrowUpRight className="h-3 w-3" />}
                {trend.direction === 'down' && <ArrowDownRight className="h-3 w-3" />}
                {trend.direction === 'neutral' && <Minus className="h-3 w-3" />}
                {trend.value}
              </span>
            )}
            {description && (
              <span className="text-slate-500 dark:text-zinc-400 font-medium">
                {description}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
export default StatCard;
