/**
 * InvoicesPage.jsx
 *
 * Invoices raised from approved quotations: what is outstanding, what has been
 * paid, and recording a payment when the customer pays the technician directly.
 *
 * The same screen serves the vendor and SEVO — the backend scopes the list, so
 * a technician sees their own, a vendor admin their company's, and SEVO all of
 * them. Mounted at /workforce/admin/invoices and /workforce/employee/invoices.
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  IndianRupee,
  Loader2,
  RefreshCw,
  Search,
} from 'lucide-react';
import { apiRequest } from '../../api/client.js';
import {
  apiGetInvoices,
  apiGetInvoiceDetail,
  apiRecordInvoicePayment,
} from '../../api/workforceService.js';

const STATUS_STYLES = {
  ISSUED: 'bg-blue-50 text-blue-700',
  PARTIALLY_PAID: 'bg-amber-50 text-amber-800',
  PAID: 'bg-emerald-50 text-emerald-700',
  CANCELLED: 'bg-slate-100 text-slate-600',
  REFUNDED: 'bg-slate-100 text-slate-600',
  DRAFT: 'bg-slate-100 text-slate-600',
};

const METHODS = ['ONLINE', 'UPI', 'CARD', 'CASH', 'OTHER'];

function money(value) {
  return Number(value || 0).toLocaleString('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 2,
  });
}

export function InvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selected, setSelected] = useState(null);
  const [flash, setFlash] = useState(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiGetInvoices({ search, status: statusFilter });
      setInvoices(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err?.message || 'Could not load invoices.');
      setInvoices([]);
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => { load(); }, [load]);

  async function open(invoice) {
    try {
      setSelected(await apiGetInvoiceDetail(invoice.id));
    } catch (err) {
      setError(err?.message || 'Could not open that invoice.');
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Invoices</h1>
          <p className="text-sm text-slate-600 mt-1">
            Raised automatically when SEVO approves a quotation.
          </p>
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

      <div className="flex flex-wrap gap-2 mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Invoice number, customer, phone"
            className="w-full rounded-lg border border-slate-300 pl-9 pr-3 py-2 text-sm"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          {Object.keys(STATUS_STYLES).map((s) => (
            <option key={s} value={s}>{s.replace('_', ' ').toLowerCase()}</option>
          ))}
        </select>
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
      ) : invoices.length === 0 ? (
        <div className="py-16 text-center">
          <IndianRupee className="w-8 h-8 text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500">No invoices yet.</p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
          {invoices.map((inv) => (
            <button
              key={inv.id}
              type="button"
              onClick={() => open(inv)}
              className="w-full text-left px-5 py-4 hover:bg-slate-50 flex flex-wrap items-center justify-between gap-3"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-900">{inv.invoice_number}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLES[inv.status] || 'bg-slate-100 text-slate-600'}`}>
                    {inv.status_display}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mt-0.5">
                  {inv.bill_to_name || 'Customer'} &middot; {inv.service_name || inv.service_category}
                </p>
              </div>
              <div className="text-right">
                <p className="font-medium text-slate-900">{money(inv.total_amount)}</p>
                {Number(inv.balance_due) > 0 && (
                  <p className="text-xs text-amber-700">{money(inv.balance_due)} outstanding</p>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <InvoiceDrawer
          invoice={selected}
          onClose={() => setSelected(null)}
          onPaid={(updated, message) => {
            setSelected(updated);
            setInvoices((prev) => prev.map((i) => (i.id === updated.id ? { ...i, ...updated } : i)));
            setFlash(message);
          }}
          onError={setError}
        />
      )}
    </div>
  );
}

function InvoiceDrawer({ invoice, onClose, onPaid, onError }) {
  const [amount, setAmount] = useState(String(invoice.balance_due || ''));
  const [method, setMethod] = useState('ONLINE');
  const [reference, setReference] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const outstanding = Number(invoice.balance_due || 0);

  async function pay() {
    setIsSaving(true);
    try {
      const result = await apiRecordInvoicePayment(invoice.id, {
        amount, method, reference,
      });
      onPaid(
        result.invoice,
        result.duplicate
          ? `That reference was already recorded on ${invoice.invoice_number}; nothing was charged twice.`
          : `${money(amount)} recorded against ${invoice.invoice_number}.`
      );
      setReference('');
    } catch (err) {
      onError(err?.message || 'Could not record that payment.');
    } finally {
      setIsSaving(false);
    }
  }

  async function downloadPdf() {
    try {
      const blob = await apiRequest(`/workforce/invoices/${invoice.id}/pdf/`, { raw: true });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${invoice.invoice_number}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      onError(err?.message || 'Could not download that invoice.');
    }
  }

  return (
    <div className="fixed inset-0 bg-slate-900/30 flex items-end sm:items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-5 border-b border-slate-100 flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-slate-900">{invoice.invoice_number}</h2>
            <p className="text-sm text-slate-600">{invoice.bill_to_name}</p>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 text-sm">Close</button>
        </div>

        <div className="px-6 py-4 space-y-1">
          {(invoice.items || []).map((item) => (
            <div key={item.id} className="flex justify-between text-sm py-1">
              <span className="text-slate-700">
                {item.name}
                <span className="text-slate-400"> &times; {item.quantity} {item.unit}</span>
              </span>
              <span className="text-slate-900">{money(item.line_total)}</span>
            </div>
          ))}
          <div className="pt-3 mt-2 border-t border-slate-100 space-y-1">
            <Line label="Total" value={money(invoice.total_amount)} strong />
            {Number(invoice.balance_amount) > 0 && (
              <>
                <Line label={`Advance (${Number(invoice.advance_percent)}%)`} value={money(invoice.advance_amount)} />
                <Line label="Balance on completion" value={money(invoice.balance_amount)} />
              </>
            )}
            <Line label="Paid" value={money(invoice.amount_paid)} />
            <Line label="Outstanding" value={money(invoice.balance_due)} strong />
          </div>
        </div>

        {(invoice.payments || []).length > 0 && (
          <div className="px-6 pb-4">
            <p className="text-xs uppercase tracking-wide text-slate-500 mb-2">Payments</p>
            {invoice.payments.map((p) => (
              <div key={p.id} className="flex justify-between text-xs text-slate-600 py-1">
                <span>
                  {p.method}
                  {p.reference && <span className="text-slate-400"> · {p.reference}</span>}
                  {p.ledger_entry_id && (
                    <span className="ml-2 text-emerald-700">credited to wallet</span>
                  )}
                </span>
                <span>{money(p.amount)}</span>
              </div>
            ))}
          </div>
        )}

        {outstanding > 0 && invoice.status !== 'CANCELLED' && (
          <div className="px-6 py-4 border-t border-slate-100 space-y-3">
            <p className="text-sm font-medium text-slate-900">Record a payment</p>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number" step="0.01" min="0" value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Amount"
              />
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <input
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Transaction reference (recommended)"
            />
            <p className="text-xs text-slate-500">
              A reference makes this safe to repeat: recording the same one twice
              will not charge the customer twice.
            </p>
            <button
              type="button"
              disabled={isSaving || !Number(amount)}
              onClick={pay}
              className="w-full rounded-lg bg-slate-900 text-white text-sm font-medium py-2.5 disabled:opacity-40"
            >
              {isSaving ? 'Recording…' : `Record ${money(amount)}`}
            </button>
          </div>
        )}

        <div className="px-6 py-4 border-t border-slate-100">
          <button
            type="button"
            onClick={downloadPdf}
            className="inline-flex items-center gap-2 text-sm text-slate-700 border border-slate-300 rounded-lg px-4 py-2"
          >
            <Download className="w-4 h-4" />
            Download PDF
          </button>
        </div>
      </div>
    </div>
  );
}

function Line({ label, value, strong }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-600">{label}</span>
      <span className={strong ? 'font-semibold text-slate-900' : 'text-slate-900'}>{value}</span>
    </div>
  );
}

export default InvoicesPage;
