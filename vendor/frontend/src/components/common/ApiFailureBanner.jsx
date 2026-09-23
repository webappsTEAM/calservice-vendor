import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, RefreshCw, X } from 'lucide-react';

/**
 * Tells the user when data on screen is incomplete.
 *
 * Most loaders in this app catch a failed request and fall back to an empty
 * list. On its own that is sensible -- one failing widget should not blank a
 * whole screen -- but it means a dead API is drawn as real, empty data: a
 * dashboard reading "0 jobs" when the truth is "we could not ask".
 *
 * api/client.js now emits `workforce:api-error` for every failed request, so
 * this one component can say so wherever it happens, without each page having
 * to grow its own error surface.
 *
 * Deliberate choices:
 *
 * - It does not block. The screen may still be mostly correct, and a modal
 *   over a half-loaded page helps nobody.
 * - It names what failed rather than saying "an error occurred", because
 *   "Jobs could not load" tells the user which part of the screen to distrust.
 * - It stays until dismissed or reloaded. An auto-hiding toast for "what you
 *   are reading is wrong" is worse than none.
 * - 401 never reaches here; the auth flow handles it.
 */

const MAX_LISTED = 3;

function labelFor(path = '') {
  const cleaned = String(path).split('?')[0].replace(/^\/+|\/+$/g, '');
  const parts = cleaned.split('/').filter((p) => p && !/^\d+$/.test(p));
  const known = {
    jobs: 'Jobs',
    quotes: 'Quotations',
    invoices: 'Invoices',
    wallet: 'Wallet',
    withdrawals: 'Withdrawals',
    employees: 'Employees',
    applications: 'Applications',
    'rate-cards': 'Rate cards',
    'pricing-policies': 'Pricing settings',
    notifications: 'Notifications',
    scorecards: 'Scorecards',
    documents: 'Documents',
    services: 'Services',
    location: 'Location',
    presence: 'Presence',
  };
  for (let i = parts.length - 1; i >= 0; i -= 1) {
    if (known[parts[i]]) return known[parts[i]];
  }
  const last = parts[parts.length - 1] || 'Data';
  return last.charAt(0).toUpperCase() + last.slice(1).replace(/-/g, ' ');
}

export function ApiFailureBanner() {
  const [failures, setFailures] = useState([]);
  const [dismissed, setDismissed] = useState(false);
  const dismissedRef = useRef(false);

  const onFailure = useCallback((event) => {
    const detail = event?.detail || {};
    // A new failure after a dismissal is new information, so show it again.
    if (dismissedRef.current) {
      dismissedRef.current = false;
      setDismissed(false);
    }
    setFailures((prev) => {
      const label = labelFor(detail.path);
      if (prev.some((f) => f.label === label)) return prev;
      return [...prev, { label, status: detail.status, message: detail.message }];
    });
  }, []);

  useEffect(() => {
    window.addEventListener('workforce:api-error', onFailure);
    return () => window.removeEventListener('workforce:api-error', onFailure);
  }, [onFailure]);

  if (dismissed || failures.length === 0) return null;

  const offline = failures.every((f) => f.status === 0);
  const listed = failures.slice(0, MAX_LISTED).map((f) => f.label);
  const extra = failures.length - listed.length;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-xl"
    >
      <div className="flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 shadow-lg">
        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />

        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-amber-900">
            {offline
              ? 'You appear to be offline — this page may be out of date.'
              : 'Some of this page could not be loaded.'}
          </p>
          <p className="text-[11px] text-amber-800 mt-0.5">
            {listed.join(', ')}
            {extra > 0 ? ` and ${extra} more` : ''}
            {offline ? '' : ' did not load. What you see may be incomplete.'}
          </p>
        </div>

        <button
          type="button"
          onClick={() => window.location.reload()}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-amber-700"
        >
          <RefreshCw className="w-3 h-3" />
          Reload
        </button>

        <button
          type="button"
          aria-label="Dismiss"
          onClick={() => { dismissedRef.current = true; setDismissed(true); }}
          className="shrink-0 rounded-lg p-1.5 text-amber-700 hover:bg-amber-100"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

export default ApiFailureBanner;
