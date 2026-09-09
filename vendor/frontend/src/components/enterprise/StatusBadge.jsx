import React from 'react';

const STATUS_CONFIGS = {
  // Application & Verification statuses
  approved: {
    label: 'Approved',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    dot: 'bg-emerald-500',
  },
  active: {
    label: 'Active',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    dot: 'bg-emerald-500',
  },
  online: {
    label: 'Online',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    dot: 'bg-emerald-500 animate-pulse',
  },
  available: {
    label: 'Available',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    dot: 'bg-emerald-500',
  },
  busy: {
    label: 'Busy (On Job)',
    bg: 'bg-zinc-900 text-white border-zinc-900',
    dot: 'bg-emerald-400 animate-pulse',
  },
  submitted: {
    label: 'Submitted',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-500',
  },
  under_review: {
    label: 'Under Review',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-500',
  },
  pending: {
    label: 'Pending',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-500',
  },
  correction_required: {
    label: 'Correction Required',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-600',
  },
  rejected: {
    label: 'Rejected',
    bg: 'bg-rose-50 text-rose-800 border-rose-200/80',
    dot: 'bg-rose-500',
  },
  offline: {
    label: 'Offline',
    bg: 'bg-zinc-100 text-zinc-600 border-zinc-200/80',
    dot: 'bg-zinc-400',
  },
  not_started: {
    label: 'Not Started',
    bg: 'bg-zinc-100 text-zinc-600 border-zinc-200/80',
    dot: 'bg-zinc-400',
  },

  // Job & Dispatch statuses
  assigned: {
    label: 'Assigned',
    bg: 'bg-zinc-100 text-zinc-800 border-zinc-300',
    dot: 'bg-zinc-600',
  },
  offered: {
    label: 'Offered',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-500 animate-pulse',
  },
  accepted: {
    label: 'Accepted',
    bg: 'bg-zinc-900 text-white border-zinc-900',
    dot: 'bg-emerald-400',
  },
  on_the_way: {
    label: 'On The Way',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-500 animate-pulse',
  },
  arrived: {
    label: 'Arrived',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    dot: 'bg-emerald-500',
  },
  in_progress: {
    label: 'In Progress',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-500 animate-pulse',
  },
  completed: {
    label: 'Completed',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    dot: 'bg-emerald-500',
  },
  cancelled: {
    label: 'Cancelled',
    bg: 'bg-zinc-100 text-zinc-600 border-zinc-200/80',
    dot: 'bg-zinc-400',
  },

  // Payment statuses
  collected: {
    label: 'Cash Collected',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    dot: 'bg-emerald-500',
  },
  pending_collection: {
    label: 'COD Pending',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-500',
  },
  paid: {
    label: 'Paid',
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    dot: 'bg-emerald-500',
  },
  processing: {
    label: 'Processing',
    bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dot: 'bg-amber-500 animate-pulse',
  },
  failed: {
    label: 'Failed',
    bg: 'bg-rose-50 text-rose-800 border-rose-200/80',
    dot: 'bg-rose-500',
  },
};

export function StatusBadge({ status = '', label = '', size = 'sm', showDot = true, className = '' }) {
  const normalizedKey = String(status || '').toLowerCase().trim().replace(/[\s-]+/g, '_');
  const config = STATUS_CONFIGS[normalizedKey] || {
    label: label || status.replace(/_/g, ' ') || 'Unknown',
    bg: 'bg-zinc-100 text-zinc-700 border-zinc-200/80',
    dot: 'bg-zinc-400',
  };

  const displayLabel = label || config.label;
  const isXs = size === 'xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 border font-semibold uppercase tracking-wider rounded-full shadow-xs ${
        isXs ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-0.5 text-[11px]'
      } ${config.bg} ${className}`}
    >
      {showDot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${config.dot}`} />}
      <span className="truncate">{displayLabel}</span>
    </span>
  );
}

export default StatusBadge;

