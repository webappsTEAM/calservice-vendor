import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

/**
 * Shown when a page's data could not be loaded.
 *
 * Distinct from ErrorState, which is an auto-dismissing toast for the result of
 * an action ("saved", "could not save"). This is for the other case: the screen
 * you are looking at is missing data, and the only useful next step is to try
 * again. It must not auto-dismiss -- the problem does not go away on a timer --
 * and it must carry the retry, because otherwise the user's only option is to
 * reload the browser and lose their filters.
 *
 * `variant="partial"` is for the common case in this app where some sections
 * loaded and some did not: the page still has content worth showing, so the
 * message sits above it rather than replacing it.
 */
export function LoadFailure({
  message = 'This page could not be loaded.',
  onRetry = null,
  isRetrying = false,
  variant = 'full', // 'full' replaces the content | 'partial' sits above it
  className = '',
}) {
  if (variant === 'partial') {
    return (
      <div
        role="alert"
        className={`flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 mb-4 ${className}`}
      >
        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <p className="flex-1 text-xs text-amber-900">{message}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            disabled={isRetrying}
            className="shrink-0 inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isRetrying ? 'animate-spin' : ''}`} />
            {isRetrying ? 'Retrying' : 'Retry'}
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      role="alert"
      className={`bg-white border border-slate-200 rounded p-12 text-center shadow-sm ${className}`}
    >
      <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-3" />
      <p className="text-xs font-semibold text-slate-800 mb-1">Couldn&rsquo;t load this page</p>
      <p className="text-xs text-slate-500 mb-5 max-w-sm mx-auto leading-relaxed">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={isRetrying}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
          {isRetrying ? 'Retrying…' : 'Try again'}
        </button>
      )}
    </div>
  );
}

export default LoadFailure;
