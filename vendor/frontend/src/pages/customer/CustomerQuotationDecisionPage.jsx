/**
 * CustomerQuotationDecisionPage.jsx
 *
 * The page a customer opens from the link the technician sends after a site
 * inspection. Mounted at `/customer/quote/:token`, `/booking/quote/:token` and
 * `/workforce/customer/quote/:token`.
 *
 * No login: the token in the URL is the credential, because the customer may
 * open the link on a phone that has never signed in to SEVO. The backend
 * validates it (workforce_api/invoice_views.QuoteCustomerDecisionView) and the
 * token is never echoed back into the page payload.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Clock,
  FileText,
  Loader2,
  MessageSquare,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { apiRequest } from '../../api/client.js';

const WARRANTY_LABELS = {
  NONE: null,
  '5_YEAR': '5-Year Warranty',
  '10_YEAR': '10-Year Warranty',
};

function money(value) {
  const n = Number(value || 0);
  return n.toLocaleString('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  });
}

function formatDate(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  } catch {
    return null;
  }
}

export function CustomerQuotationDecisionPage() {
  const { token } = useParams();

  const [quote, setQuote] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [pendingAction, setPendingAction] = useState(null);   // 'DECLINE' | 'REQUEST_CHANGES'
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [outcome, setOutcome] = useState(null);

  const load = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const data = await apiRequest(`/workforce/quotes/decision/${token}/`);
      setQuote(data);
      setError(null);
    } catch (err) {
      setError(err?.message || 'This quotation link is not valid or has expired.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function submit(action, payload = {}) {
    setIsSubmitting(true);
    try {
      const result = await apiRequest(`/workforce/quotes/decision/${token}/`, {
        method: 'POST',
        json: { action, ...payload },
      });
      setOutcome(result);
      setQuote((prev) => ({ ...prev, ...(result.quote || {}), can_decide: false }));
      setPendingAction(null);
      setNotes('');
    } catch (err) {
      setError(err?.message || 'We could not record your decision. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }

  // ---------------------------------------------------------------- states
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
      </div>
    );
  }

  if (error && !quote) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 p-8 text-center">
          <AlertCircle className="w-10 h-10 text-amber-500 mx-auto mb-4" />
          <h1 className="text-lg font-semibold text-slate-900 mb-2">
            This quotation isn&rsquo;t available
          </h1>
          <p className="text-sm text-slate-600">{error}</p>
          <p className="text-sm text-slate-500 mt-4">
            If you were expecting a quotation, please contact the technician who visited you.
          </p>
        </div>
      </div>
    );
  }

  const items = quote?.items || [];
  const invoice = quote?.invoice;
  const advance = invoice?.advance_amount;
  const balance = invoice?.balance_amount;
  const showsSplit = Number(balance || 0) > 0;

  return (
    <div className="min-h-screen bg-slate-50 py-6 px-4">
      <div className="max-w-2xl mx-auto space-y-4">

        {/* header */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">Quotation</p>
              <h1 className="text-xl font-semibold text-slate-900">{quote.quote_number}</h1>
              <p className="text-sm text-slate-600 mt-1">
                {quote.service_name || quote.title}
                {quote.quote_version > 1 && (
                  <span className="ml-2 text-xs text-slate-500">revision {quote.quote_version}</span>
                )}
              </p>
            </div>
            <StatusBadge quote={quote} />
          </div>

          {quote.valid_until && quote.can_decide && (
            <p className="text-xs text-slate-500 mt-4 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              Valid until {formatDate(quote.valid_until)}
            </p>
          )}
        </div>

        {/* outcome banner */}
        {outcome && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 flex gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-emerald-900">{outcome.message}</p>
              {outcome.awaiting_admin_approval && (
                <p className="text-xs text-emerald-800 mt-1">
                  Nothing further is needed from you right now.
                </p>
              )}
            </div>
          </div>
        )}

        {error && quote && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 flex gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-900">{error}</p>
          </div>
        )}

        {/* line items */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-slate-400" />
            <h2 className="text-sm font-medium text-slate-900">What&rsquo;s included</h2>
          </div>

          {items.length === 0 ? (
            <p className="px-6 py-8 text-sm text-slate-500 text-center">
              No line items on this quotation.
            </p>
          ) : (
            <div className="divide-y divide-slate-100">
              {items.map((item) => (
                <div key={item.id} className="px-6 py-4 flex justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900">{item.name}</p>
                    {item.description && (
                      <p className="text-xs text-slate-500 mt-0.5">{item.description}</p>
                    )}
                    <p className="text-xs text-slate-500 mt-1">
                      {item.quantity} {item.unit} &times; {money(item.unit_price)}
                    </p>
                    {WARRANTY_LABELS[item.warranty_tier] && (
                      <span className="inline-flex items-center gap-1 mt-2 text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                        <ShieldCheck className="w-3 h-3" />
                        {WARRANTY_LABELS[item.warranty_tier]}
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-slate-900 whitespace-nowrap">
                    {money(item.total_amount)}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* totals */}
          <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 space-y-2">
            <Row label="Subtotal" value={money(quote.subtotal_amount)} />
            {Number(quote.discount_amount) > 0 && (
              <Row label="Discount" value={`- ${money(quote.discount_amount)}`} />
            )}
            <Row label="GST" value={money(quote.tax_amount)} />
            {Number(quote.inspection_fee_adjusted) > 0 && (
              <Row
                label="Inspection fee credited"
                value={`- ${money(quote.inspection_fee_adjusted)}`}
              />
            )}
            <div className="pt-2 border-t border-slate-200 flex justify-between">
              <span className="text-sm font-semibold text-slate-900">Total</span>
              <span className="text-lg font-semibold text-slate-900">
                {money(quote.net_payable || quote.total_amount)}
              </span>
            </div>
          </div>
        </div>

        {/* payment schedule */}
        {invoice && showsSplit && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="w-4 h-4 text-slate-400" />
              <h2 className="text-sm font-medium text-slate-900">Payment schedule</h2>
            </div>
            <div className="space-y-2">
              <Row
                label={`Advance (${Number(invoice.advance_percent)}%)`}
                value={money(advance)}
                emphasis
              />
              <Row label="Balance on completion" value={money(balance)} />
            </div>
            <p className="text-xs text-slate-500 mt-4">
              The advance covers materials bought before work begins. Work is scheduled
              once it is received.
            </p>
          </div>
        )}

        {/* actions */}
        {quote.can_decide && !outcome && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-3">
            {pendingAction ? (
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-900">
                  {pendingAction === 'DECLINE'
                    ? 'Could you tell us why? (optional)'
                    : 'What would you like changed?'}
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900/10"
                  placeholder={
                    pendingAction === 'DECLINE'
                      ? 'Price, timing, or anything else'
                      : 'e.g. use a different paint brand, exclude the terrace'
                  }
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={isSubmitting || (pendingAction === 'REQUEST_CHANGES' && !notes.trim())}
                    onClick={() =>
                      submit(pendingAction, {
                        notes,
                        reason: pendingAction === 'DECLINE' ? notes : '',
                      })
                    }
                    className="flex-1 rounded-xl bg-slate-900 text-white text-sm font-medium py-3 disabled:opacity-40"
                  >
                    {isSubmitting ? 'Sending…' : 'Send'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setPendingAction(null); setNotes(''); }}
                    className="rounded-xl border border-slate-300 text-slate-700 text-sm font-medium px-5"
                  >
                    Back
                  </button>
                </div>
              </div>
            ) : (
              <>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => submit('ACCEPT')}
                  className="w-full rounded-xl bg-emerald-600 text-white text-sm font-semibold py-3.5 flex items-center justify-center gap-2 disabled:opacity-40"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  {isSubmitting
                    ? 'Approving…'
                    : showsSplit
                      ? `Approve — advance ${money(advance)}`
                      : `Approve ${money(quote.net_payable || quote.total_amount)}`}
                </button>
                <button
                  type="button"
                  onClick={() => setPendingAction('REQUEST_CHANGES')}
                  className="w-full rounded-xl border border-slate-300 text-slate-800 text-sm font-medium py-3 flex items-center justify-center gap-2"
                >
                  <MessageSquare className="w-4 h-4" />
                  Request changes
                </button>
                <button
                  type="button"
                  onClick={() => setPendingAction('DECLINE')}
                  className="w-full text-slate-500 text-sm py-2 flex items-center justify-center gap-2"
                >
                  <XCircle className="w-4 h-4" />
                  Decline
                </button>
              </>
            )}
          </div>
        )}

        {!quote.can_decide && !outcome && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 text-center">
            <p className="text-sm text-slate-600">
              {quote.is_expired
                ? 'This quotation has expired. Please ask the technician to send a fresh one.'
                : 'This quotation has already been actioned.'}
            </p>
          </div>
        )}

        <p className="text-center text-xs text-slate-400 pb-6">
          Quotation issued by SEVO. Questions? Reply to the message this link came in.
        </p>
      </div>
    </div>
  );
}

function Row({ label, value, emphasis }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-600">{label}</span>
      <span className={emphasis ? 'font-semibold text-slate-900' : 'text-slate-900'}>{value}</span>
    </div>
  );
}

function StatusBadge({ quote }) {
  const map = {
    SENT_TO_CUSTOMER: ['Awaiting your decision', 'bg-blue-50 text-blue-700'],
    PENDING_ADMIN_APPROVAL: ['Approved — with SEVO', 'bg-amber-50 text-amber-700'],
    ADMIN_APPROVED: ['Approved', 'bg-emerald-50 text-emerald-700'],
    CONVERTED: ['Scheduled', 'bg-emerald-50 text-emerald-700'],
    CHANGES_REQUESTED: ['Changes requested', 'bg-amber-50 text-amber-700'],
    DECLINED: ['Declined', 'bg-slate-100 text-slate-600'],
    ADMIN_REJECTED: ['Not approved', 'bg-slate-100 text-slate-600'],
    EXPIRED: ['Expired', 'bg-slate-100 text-slate-600'],
    SUPERSEDED: ['Replaced by a newer version', 'bg-slate-100 text-slate-600'],
  };
  const [label, classes] = map[quote.status] || [quote.status_display || quote.status, 'bg-slate-100 text-slate-600'];
  return (
    <span className={`shrink-0 text-xs font-medium px-3 py-1.5 rounded-full ${classes}`}>
      {label}
    </span>
  );
}

export default CustomerQuotationDecisionPage;
