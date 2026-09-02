import React from 'react';

export function PageHeader({
  title = '',
  subtitle = '',
  badge = null,
  actions = null,
  className = '',
}) {
  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3.5 border-b border-zinc-200/90 ${className}`}
    >
      <div>
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="text-base sm:text-lg font-bold text-zinc-900 tracking-tight">{title}</h1>
          {badge}
        </div>
        {subtitle && <p className="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">{subtitle}</p>}
      </div>

      {actions && <div className="flex items-center gap-2.5 shrink-0 flex-wrap">{actions}</div>}
    </div>
  );
}

export default PageHeader;

