import React, { useEffect } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, RefreshCw, X } from 'lucide-react';

/**
 * `onRetry` is opt-in, and passing it changes two things on purpose.
 *
 * It adds the action the user actually wants -- most failures here are a
 * request that did not come back, and without a retry the only way forward was
 * to reload the browser and lose filters, scroll position and unsaved input.
 *
 * It also stops the auto-dismiss. A message that offers "Try again" must not
 * disappear on a five-second timer before the user has read it, and a failure
 * serious enough to warrant a retry has not resolved itself just because time
 * passed.
 */

export function ErrorState({
  title = '',
  message = '',
  type = 'error', // 'error', 'warning', 'info', 'success'
  onDismiss = null,
  onRetry = null,
  retryText = 'Try again',
  isRetrying = false,
  autoDismissMs = 5000,
  className = '',
}) {
  useEffect(() => {
    if (!onRetry && onDismiss && autoDismissMs > 0 && (message || title)) {
      const timer = setTimeout(() => {
        onDismiss();
      }, autoDismissMs);
      return () => clearTimeout(timer);
    }
  }, [message, title, onDismiss, onRetry, autoDismissMs]);

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
      <div className="flex items-center gap-1 shrink-0">
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={isRetrying}
          className="inline-flex items-center gap-1.5 rounded-md border border-current/25 bg-white/70 px-2.5 py-1 text-[11px] font-semibold hover:bg-white disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${isRetrying ? 'animate-spin' : ''}`} />
          {isRetrying ? 'Retrying' : retryText}
        </button>
      )}
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="p-1 rounded-md hover:bg-black/5 text-current opacity-60 hover:opacity-100 transition-opacity"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
      </div>
    </div>
  );
}

export default ErrorState;

