import React from 'react';
import { Inbox } from 'lucide-react';

export function EmptyState({
  icon: Icon = Inbox,
  title = 'No records found',
  description = 'There are no records matching your current filter criteria.',
  action = null,
  className = '',
}) {
  return (
    <div className={`bg-white border border-zinc-200/90 rounded-md p-10 text-center shadow-card ${className}`}>
      <div className="w-12 h-12 rounded-full bg-zinc-100 border border-zinc-200/80 flex items-center justify-center mx-auto mb-3.5 text-zinc-500 shadow-xs">
        <Icon className="w-5 h-5" />
      </div>
      <h3 className="text-sm font-bold text-zinc-900 tracking-tight">{title}</h3>
      {description && <p className="text-xs text-zinc-500 mt-1.5 max-w-sm mx-auto leading-relaxed">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export default EmptyState;

