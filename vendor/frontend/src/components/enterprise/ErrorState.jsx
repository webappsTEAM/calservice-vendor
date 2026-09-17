import React, { useEffect } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';

export function ErrorState({
  title = '',
  message = '',
  type = 'error', // 'error', 'warning', 'info', 'success'
  onDismiss = null,
  autoDismissMs = 5000,
  className = '',
}) {
  useEffect(() => {
    if (onDismiss && autoDismissMs > 0 && (message || title)) {
      const timer = setTimeout(() => {
        onDismiss();
      }, autoDismissMs);
      return () => clearTimeout(timer);
    }
  }, [message, title, onDismiss, autoDismissMs]);

  if (!message && !title) return null;

  const configs = {
    error: {
      bg: 'bg-rose-50 border-rose-200/90 text-rose-800',
      icon: AlertCircle,
      iconColor: 'text-rose-600',
    },
    warning: {
      bg: 'bg-amber-50 border-amber-200/90 text-amber-800',
      icon: AlertTriangle,
      iconColor: 'text-amber-600',
    },
    info: {
      bg: 'bg-zinc-100 border-zinc-300 text-zinc-900',
      icon: Info,
      iconColor: 'text-zinc-700',
    },
    success: {
      bg: 'bg-emerald-50 border-emerald-200/90 text-emerald-800',
      icon: CheckCircle2,
      iconColor: 'text-emerald-600',
    },
  };

  const config = configs[type] || configs.error;
  const Icon = config.icon;

  return (
    <div
      className={`p-3.5 rounded-lg border flex items-start justify-between gap-3 text-xs shadow-xs ${config.bg} ${className}`}
    >
      <div className="flex items-start gap-2.5">
        <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${config.iconColor}`} />
        <div>
          {title && <p className="font-bold tracking-tight">{title}</p>}
          <p className="font-medium leading-relaxed mt-0.5">{message}</p>
        </div>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="p-1 rounded-md hover:bg-black/5 text-current opacity-60 hover:opacity-100 transition-opacity"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

export default ErrorState;

