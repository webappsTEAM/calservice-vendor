import React from 'react';

export function Card({
  children,
  className = '',
  hoverEffect = false,
  onClick = null,
  ...props
}) {
  return (
    <div
      onClick={onClick}
      className={`bg-white border border-zinc-200/90 rounded-md shadow-card transition-all ${
        hoverEffect ? 'hover:border-zinc-300 hover:shadow-bento cursor-pointer' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }) {
  return (
    <div
      className={`px-4 sm:px-5 py-3.5 border-b border-zinc-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '', icon: Icon = null, ...props }) {
  return (
    <div className={`flex items-center gap-2 ${className}`} {...props}>
      {Icon && (
        <span className="p-1.5 rounded-lg bg-zinc-100 text-zinc-700 shrink-0">
          {typeof Icon === 'function' || typeof Icon === 'object' ? (
            <Icon className="w-4 h-4" />
          ) : (
            Icon
          )}
        </span>
      )}
      <h3 className="text-xs sm:text-sm font-bold text-zinc-900 tracking-tight">{children}</h3>
    </div>
  );
}

export function CardDescription({ children, className = '', ...props }) {
  return (
    <p className={`text-[11px] text-zinc-500 font-normal leading-relaxed ${className}`} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ children, className = '', ...props }) {
  return (
    <div className={`p-4 sm:p-5 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className = '', ...props }) {
  return (
    <div
      className={`px-4 sm:px-5 py-3 bg-zinc-50/70 border-t border-zinc-100 flex items-center justify-between gap-3 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardBadge({ children, variant = 'neutral', className = '' }) {
  const badgeStyles = {
    neutral: 'bg-zinc-100 text-zinc-700 border-zinc-200/80',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
    amber: 'bg-amber-50 text-amber-700 border-amber-200/80',
    rose: 'bg-rose-50 text-rose-700 border-rose-200/80',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
        badgeStyles[variant] || badgeStyles.neutral
      } ${className}`}
    >
      {children}
    </span>
  );
}

export default Card;
