/**
 * AdminQuotationApprovalsPage.jsx
 *
 * The SEVO back office's two quotation queues, on one screen because they are
 * the same job done at two different moments:
 *
 *   Before the customer sees it — quotes held by the high-value threshold or
 *   the mason structural-clearance gate. Releasing one sends it.
 *
 *   After the customer accepts — quotes awaiting SEVO's authorisation. Approving
 *   one creates the work booking and issues the invoice.
 *
 * Mounted at /workforce/admin/quotations.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  RefreshCw,
  Send,
  XCircle,
} from 'lucide-react';
import { apiRequest } from '../../api/client.js';

function money(value) {
  return Number(value || 0).toLocaleString('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  });
}

function ago(iso) {
  if (!iso) return '';
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
  if (seconds < 3600) return `${Math.max(1, Math.round(seconds / 60))}m ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
  return `${Math.round(seconds / 86400)}d ago`;
}

const TABS = [
  {
    key: 'acceptance',
    label: 'Awaiting SEVO approval',
    endpoint: '/workforce/quotes/pending-approval/',
    blurb: 'The customer has accepted. Approving creates the work booking and issues the invoice.',
  },
  {
    key: 'presend',
    label: 'Held before sending',
    endpoint: '/workforce/quotes/pending-review/',
    blurb: 'Above the category review threshold, or needing structural clearance. Releasing sends the quote to the customer.',
  },
];

export function AdminQuotationApprovalsPage() {
  const [tab, setTab] = useState('acceptance');
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [flash, setFlash] = useState(null);

  const active = useMemo(() => TABS.find((t) => t.key === tab), [tab]);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiRequest(active.endpoint);
      setRows(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err?.message || 'Could not load the approval queue.');
      setRows([]);
    } finally {
      setIsLoading(false);
    }
  }, [active]);

  useEffect(() => { load(); }, [load]);

  async function decide(quote, approve) {
    const verb = tab === 'presend'
      ? (approve ? 'release and send' : 'reject')
      : (approve ? 'approve' : 'reject');

    // Approving spends money and schedules people. Rejecting ends a quote the
    // customer already said yes to. Both deserve a deliberate second press.
    if (!window.confirm(`${verb.charAt(0).toUpperCase() + verb.slice(1)} ${quote.quote_number}?`)) {
      return;
    }

    let notes = '';
    if (!approve) {
      notes = window.prompt('Reason (shown in the audit trail):') || '';
      if (!notes.trim()) return;
    }

    setBusyId(quote.id);
    try {
      const path = tab === 'presend'
        ? `/workforce/quotes/${quote.id}/pre-send-review/`
        : `/workforce/quotes/${quote.id}/admin-review/`;
      const result = await apiRequest(path, {
        method: 'POST',
        json: { action: approve ? 'APPROVE' : 'REJECT', notes, reason: notes },
      });

      if (result.invoice) {
        setFlash(`${quote.quote_number} approved. Invoice ${result.invoice.invoice_number} issued for ${money(result.invoice.total_amount)}.`);
      } else if (tab === 'presend' && approve) {
        setFlash(`${quote.quote_number} released and sent to the customer.`);
      } else {
        setFlash(`${quote.quote_number} ${approve ? 'approved' : 'rejected'}.`);
      }
      setRows((prev) => prev.filter((r) => r.id !== quote.id));
      setError(null);
    } catch (err) {
      setError(err?.message || `Could not ${verb} ${quote.quote_number}.`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Quotation approvals</h1>
          <p className="text-sm text-slate-600 mt-1">{active.blurb}</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="inline-flex items-center gap-2 text-sm text-slate-600 border border-slate-300 rounded-lg px-3 py-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="flex gap-1 mb-5 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => { setTab(t.key); setFlash(null); }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px ${
              t.key === tab
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {flash && (
        <div className="mb-4 bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <p className="text-sm text-emerald-900">{flash}</p>
        </div>
      )}

      {error && (
        <div className="mb-4 bg-rose-50 border border-rose-200 rounded-xl p-4 flex gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-rose-900">{error}</p>
            <button type="button" onClick={load} className="text-sm text-rose-700 underline mt-1">
              Try again
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="py-16 flex justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
        </div>
      ) : rows.length === 0 ? (
        <div className="py-16 text-center">
          <FileText className="w-8 h-8 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500">Nothing waiting in this queue.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map((q) => (
            <div key={q.id} className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-slate-900">{q.quote_number}</span>
                    {q.quote_version > 1 && (
                      <span className="text-xs text-slate-500">v{q.quote_version}</span>
                    )}
                    {q.requires_structural_clearance && !q.is_structurally_cleared && (
                      <span className="text-xs bg-amber-50 text-amber-800 px-2 py-0.5 rounded-full">
                        Structural clearance needed
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-600 mt-1">
                    {q.service_name || q.title} &middot; {q.customer_name || 'Customer'}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {q.service_category} &middot; job #{q.job_id}
                    {q.submitted_for_approval_at && ` · accepted ${ago(q.submitted_for_approval_at)}`}
                  </p>
                </div>

                <div className="text-right shrink-0">
                  <p className="text-lg font-semibold text-slate-900">
                    {money(q.net_payable || q.total_amount)}
                  </p>
                  <p className="text-xs text-slate-500">incl. GST {money(q.tax_amount)}</p>
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <button
                  type="button"
                  disabled={busyId === q.id}
                  onClick={() => decide(q, true)}
                  className="inline-flex items-center gap-2 rounded-lg bg-slate-900 text-white text-sm font-medium px-4 py-2 disabled:opacity-40"
                >
                  {busyId === q.id
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : tab === 'presend' ? <Send className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                  {tab === 'presend' ? 'Release & send' : 'Approve'}
                </button>
                <button
                  type="button"
                  disabled={busyId === q.id}
                  onClick={() => decide(q, false)}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium px-4 py-2 disabled:opacity-40"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AdminQuotationApprovalsPage;
