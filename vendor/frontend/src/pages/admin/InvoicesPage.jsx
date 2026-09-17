/**
 * InvoicesPage.jsx
 *
 * Enterprise Customer Invoices & Billing Management
 * Displays customer tax invoices generated for completed jobs & approved quotations.
 * Includes KPI metrics, advanced filtering, table/card views, GST breakdown,
 * interactive tax invoice preview, payment recording, and PDF export.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  CreditCard,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  IndianRupee,
  LayoutGrid,
  List,
  Loader2,
  MapPin,
  Phone,
  Printer,
  Receipt,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react';
import { apiRequest } from '../../api/client.js';
import {
  apiGetInvoices,
  apiGetInvoiceDetail,
  apiRecordInvoicePayment,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { MetricStrip } from '../../components/enterprise/MetricStrip.jsx';

const STATUS_CONFIGS = {
  PAID: {
    label: 'Paid',
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
    dotClass: 'bg-emerald-500',
  },
  ISSUED: {
    label: 'Issued (Pending)',
    badgeClass: 'bg-sky-50 text-sky-700 border-sky-200/80',
    dotClass: 'bg-sky-500',
  },
  PARTIALLY_PAID: {
    label: 'Partially Paid',
    badgeClass: 'bg-amber-50 text-amber-800 border-amber-200/80',
    dotClass: 'bg-amber-500',
  },
  CANCELLED: {
    label: 'Cancelled',
    badgeClass: 'bg-zinc-100 text-zinc-600 border-zinc-200/80',
    dotClass: 'bg-zinc-400',
  },
  REFUNDED: {
    label: 'Refunded',
    badgeClass: 'bg-purple-50 text-purple-700 border-purple-200/80',
    dotClass: 'bg-purple-500',
  },
  DRAFT: {
    label: 'Draft',
    badgeClass: 'bg-zinc-100 text-zinc-600 border-zinc-200/80',
    dotClass: 'bg-zinc-400',
  },
};

const PAYMENT_METHODS = [
  { value: 'ONLINE', label: 'Online / Gateway' },
  { value: 'UPI', label: 'UPI / QR Code' },
  { value: 'CASH', label: 'Cash Collected' },
  { value: 'CARD', label: 'Credit / Debit Card' },
  { value: 'OTHER', label: 'Bank Transfer / Other' },
];

function formatMoney(value) {
  return Number(value || 0).toLocaleString('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  });
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch (_) {
    return dateStr;
  }
}

export function InvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'cards'
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [flashMessage, setFlashMessage] = useState(null);

  const loadInvoices = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiGetInvoices();
      setInvoices(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err?.message || 'Failed to load invoices from server.');
      setInvoices([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

  // Flash auto-dismiss
  useEffect(() => {
    if (flashMessage) {
      const t = setTimeout(() => setFlashMessage(null), 5000);
      return () => clearTimeout(t);
    }
  }, [flashMessage]);

  // Filtered dataset
  const filteredInvoices = useMemo(() => {
    return invoices.filter((inv) => {
      const term = search.toLowerCase().trim();
      const num = (inv.invoice_number || '').toLowerCase();
      const name = (inv.bill_to_name || '').toLowerCase();
      const phone = (inv.bill_to_phone || '').toLowerCase();
      const svc = (inv.service_name || inv.service_category || '').toLowerCase();
      const jobId = String(inv.job_id || '');

      const matchesSearch =
        !term ||
        num.includes(term) ||
        name.includes(term) ||
        phone.includes(term) ||
        svc.includes(term) ||
        jobId.includes(term);

      const matchesStatus =
        statusFilter === 'ALL' ||
        (inv.status || '').toUpperCase() === statusFilter.toUpperCase();

      return matchesSearch && matchesStatus;
    });
  }, [invoices, search, statusFilter]);

  // Financial KPIs
  const kpis = useMemo(() => {
    let totalBilled = 0;
    let totalCollected = 0;
    let totalOutstanding = 0;
    let paidCount = 0;
    let pendingCount = 0;

    invoices.forEach((inv) => {
      const total = Number(inv.total_amount || 0);
      const paid = Number(inv.amount_paid || 0);
      const bal = Number(inv.balance_due || 0);

      totalBilled += total;
      totalCollected += paid;
      totalOutstanding += bal;

      if (inv.status === 'PAID') {
        paidCount += 1;
      } else if (inv.status === 'ISSUED' || inv.status === 'PARTIALLY_PAID') {
        pendingCount += 1;
      }
    });

    return [
      {
        label: 'Total Invoiced',
        value: formatMoney(totalBilled),
        subtext: `${invoices.length} invoices generated`,
        icon: Receipt,
        iconColor: 'text-indigo-600',
        valueColor: 'text-zinc-950',
      },
      {
        label: 'Collected Amount',
        value: formatMoney(totalCollected),
        subtext: `${paidCount} fully paid invoices`,
        icon: ShieldCheck,
        iconColor: 'text-emerald-600',
        valueColor: 'text-emerald-700',
      },
      {
        label: 'Pending / Outstanding',
        value: formatMoney(totalOutstanding),
        subtext: `${pendingCount} awaiting payment`,
        icon: Clock,
        iconColor: 'text-amber-600',
        valueColor: 'text-amber-700',
      },
      {
        label: 'Total Invoices',
        value: String(invoices.length),
        subtext: `${paidCount} Paid · ${pendingCount} Unpaid`,
        icon: FileText,
        iconColor: 'text-sky-600',
        valueColor: 'text-zinc-900',
      },
    ];
  }, [invoices]);

  const handleOpenDetail = async (invoice) => {
    try {
      const detail = await apiGetInvoiceDetail(invoice.id);
      setSelectedInvoice(detail);
    } catch (err) {
      setError(err?.message || 'Could not load invoice details.');
    }
  };

  const handleExportCsv = () => {
    if (invoices.length === 0) return;
    const headers = [
      'Invoice Number',
      'Status',
      'Job ID',
      'Customer Name',
      'Customer Phone',
      'Service',
      'Issued Date',
      'Total Amount (INR)',
      'Amount Paid (INR)',
      'Balance Due (INR)',
    ];

    const rows = filteredInvoices.map((i) => [
      i.invoice_number,
      i.status,
      i.job_id || 'N/A',
      `"${(i.bill_to_name || '').replace(/"/g, '""')}"`,
      i.bill_to_phone || '',
      `"${(i.service_name || i.service_category || '').replace(/"/g, '""')}"`,
      formatDate(i.issued_at),
      i.total_amount || '0',
      i.amount_paid || '0',
      i.balance_due || '0',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `invoices_export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const statusCounts = useMemo(() => {
    const counts = { ALL: invoices.length, PAID: 0, ISSUED: 0, PARTIALLY_PAID: 0, CANCELLED: 0 };
    invoices.forEach((i) => {
      const st = (i.status || '').toUpperCase();
      if (counts[st] !== undefined) counts[st] += 1;
    });
    return counts;
  }, [invoices]);

  return (
    <AppShell
      breadcrumbs={[
        { label: 'Admin', path: '/workforce/admin/dashboard' },
        { label: 'Finance', path: '/workforce/admin/wallet' },
        { label: 'Invoices' },
      ]}
    >
      {/* Global Print-only Styles */}
      <style>{`
        @page {
          size: A4;
          margin: 12mm 15mm;
        }
        @media print {
          html, body {
            background: white !important;
          }
          body * {
            visibility: hidden !important;
          }
          #printable-tax-invoice, #printable-tax-invoice * {
            visibility: visible !important;
          }
          #printable-tax-invoice {
            position: fixed !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
            background: white !important;
            z-index: 999999 !important;
            box-shadow: none !important;
            border: none !important;
          }
          .no-print {
            display: none !important;
          }
        }
      `}</style>

      <div className="space-y-4 max-w-7xl mx-auto pb-10">
        {/* Page Header */}
        <PageHeader
          title="Customer Invoices & Billing"
          subtitle="Tax invoices generated automatically for completed service requests and approved quotations."
          actions={
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleExportCsv}
                disabled={filteredInvoices.length === 0}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-zinc-700 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 transition shadow-xs disabled:opacity-50"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                Export CSV
              </button>
              <button
                type="button"
                onClick={loadInvoices}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-zinc-700 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 transition shadow-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-zinc-500 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          }
        />

        {/* Flash notification */}
        {flashMessage && (
          <div className="bg-emerald-50 border border-emerald-200/90 rounded-lg p-3.5 flex items-center gap-3 text-emerald-900 text-xs font-medium animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="flex-1">{flashMessage}</span>
            <button
              type="button"
              onClick={() => setFlashMessage(null)}
              className="text-emerald-500 hover:text-emerald-700"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Error notification */}
        {error && (
          <div className="bg-rose-50 border border-rose-200 rounded-lg p-3.5 flex items-center gap-3 text-rose-900 text-xs font-medium">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span className="flex-1">{error}</span>
            <button
              type="button"
              onClick={loadInvoices}
              className="text-xs font-bold text-rose-700 underline hover:text-rose-900"
            >
              Retry
            </button>
          </div>
        )}

        {/* Financial KPI Cards */}
        <MetricStrip metrics={kpis} columns={4} />

        {/* Controls Toolbar */}
        <div className="bg-white border border-zinc-200/90 rounded-lg p-3 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
            {[
              { id: 'ALL', label: 'All Invoices' },
              { id: 'PAID', label: 'Paid' },
              { id: 'ISSUED', label: 'Issued / Pending' },
              { id: 'PARTIALLY_PAID', label: 'Partial' },
              { id: 'CANCELLED', label: 'Cancelled' },
            ].map((tab) => {
              const active = statusFilter === tab.id;
              const count = statusCounts[tab.id] ?? 0;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setStatusFilter(tab.id)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold whitespace-nowrap transition-colors ${
                    active
                      ? 'bg-zinc-900 text-white shadow-xs'
                      : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`px-1.5 py-0.2 text-[10px] rounded-full font-bold ${
                      active ? 'bg-zinc-700 text-zinc-100' : 'bg-zinc-100 text-zinc-600'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Search & Layout toggle */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1 md:w-64">
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search invoice, customer, job..."
                className="w-full bg-zinc-50 border border-zinc-200 rounded-md pl-8 pr-3 py-1.5 text-xs text-zinc-900 placeholder:text-zinc-400 focus:outline-hidden focus:bg-white focus:border-zinc-400 transition"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="flex items-center border border-zinc-200 rounded-md bg-zinc-50 p-0.5 shrink-0">
              <button
                type="button"
                onClick={() => setViewMode('table')}
                title="Table View"
                className={`p-1 rounded ${viewMode === 'table' ? 'bg-white shadow-xs text-zinc-900 font-bold' : 'text-zinc-500 hover:text-zinc-800'}`}
              >
                <List className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                title="Cards Grid"
                className={`p-1 rounded ${viewMode === 'cards' ? 'bg-white shadow-xs text-zinc-900 font-bold' : 'text-zinc-500 hover:text-zinc-800'}`}
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Content View */}
        {isLoading ? (
          <div className="bg-white border border-zinc-200/90 rounded-lg p-16 flex flex-col items-center justify-center text-center">
            <Loader2 className="w-7 h-7 animate-spin text-zinc-400 mb-2" />
            <p className="text-xs font-semibold text-zinc-600">Loading invoices...</p>
          </div>
        ) : filteredInvoices.length === 0 ? (
          <div className="bg-white border border-zinc-200/90 rounded-lg p-16 flex flex-col items-center justify-center text-center shadow-xs">
            <div className="w-12 h-12 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-400 mb-3">
              <Receipt className="w-6 h-6" />
            </div>
            <p className="text-sm font-bold text-zinc-800">No invoices found</p>
            <p className="text-xs text-zinc-500 mt-1 max-w-sm">
              {search || statusFilter !== 'ALL'
                ? 'Try adjusting your search query or status filter.'
                : 'Invoices will automatically be generated once jobs are completed or quotations are approved.'}
            </p>
          </div>
        ) : viewMode === 'table' ? (
          /* Table View */
          <div className="bg-white border border-zinc-200/90 rounded-lg shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-zinc-50/90 border-b border-zinc-200 text-zinc-700 text-[11px] font-semibold uppercase tracking-wider select-none">
                    <th className="py-2.5 px-3.5">Invoice #</th>
                    <th className="py-2.5 px-3.5">Customer</th>
                    <th className="py-2.5 px-3.5">Service Details</th>
                    <th className="py-2.5 px-3.5">Issued Date</th>
                    <th className="py-2.5 px-3.5 text-right">Total Amount</th>
                    <th className="py-2.5 px-3.5">Status</th>
                    <th className="py-2.5 px-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {filteredInvoices.map((inv) => {
                    const cfg = STATUS_CONFIGS[inv.status] || STATUS_CONFIGS.DRAFT;
                    const balance = Number(inv.balance_due || 0);
                    return (
                      <tr
                        key={inv.id}
                        onClick={() => handleOpenDetail(inv)}
                        className="hover:bg-zinc-50/80 cursor-pointer transition-colors group"
                      >
                        {/* Invoice Number & Job Reference */}
                        <td className="py-3 px-3.5 font-mono">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-bold text-zinc-950 group-hover:text-indigo-600 transition-colors">
                              {inv.invoice_number}
                            </span>
                          </div>
                          {(inv.job_request_id || inv.job_id) && (
                            <div className="text-[10px] text-zinc-500 font-sans mt-0.5">
                              Booking: <span className="font-semibold text-zinc-700">{inv.job_request_id || `Job #${inv.job_id}`}</span>
                            </div>
                          )}
                        </td>

                        {/* Customer */}
                        <td className="py-3 px-3.5">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-zinc-200 to-zinc-100 text-zinc-700 font-bold text-[10px] flex items-center justify-center shrink-0 border border-zinc-200">
                              {(inv.bill_to_name || 'C').charAt(0).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold text-zinc-900 truncate max-w-[140px]">
                                {inv.bill_to_name || 'Customer'}
                              </p>
                              {inv.bill_to_phone && (
                                <p className="text-[10px] text-zinc-500">{inv.bill_to_phone}</p>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Service Details */}
                        <td className="py-3 px-3.5">
                          <p className="font-medium text-zinc-900 truncate max-w-xs">
                            {inv.service_name || inv.service_category || 'Service Request'}
                          </p>
                          {inv.service_category && inv.service_category !== inv.service_name && (
                            <span className="inline-block mt-0.5 px-1.5 py-0.2 text-[9px] font-bold uppercase rounded-sm bg-zinc-100 text-zinc-600">
                              {inv.service_category}
                            </span>
                          )}
                        </td>

                        {/* Issued Date */}
                        <td className="py-3 px-3.5 text-zinc-600 whitespace-nowrap">
                          {formatDate(inv.issued_at)}
                        </td>

                        {/* Total Amount */}
                        <td className="py-3 px-3.5 text-right whitespace-nowrap">
                          <p className="font-bold text-zinc-950 text-xs">
                            {formatMoney(inv.total_amount)}
                          </p>
                          {balance > 0 ? (
                            <p className="text-[10px] font-semibold text-amber-700">
                              {formatMoney(balance)} due
                            </p>
                          ) : (
                            <p className="text-[10px] font-medium text-emerald-600">Settled</p>
                          )}
                        </td>

                        {/* Status */}
                        <td className="py-3 px-3.5 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold border ${cfg.badgeClass}`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dotClass}`} />
                            {cfg.label}
                          </span>
                        </td>

                        {/* Actions */}
                        <td
                          className="py-3 px-3.5 text-right whitespace-nowrap"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              onClick={() => handleOpenDetail(inv)}
                              className="p-1.5 rounded-md hover:bg-zinc-200/80 text-zinc-600 hover:text-zinc-900 transition"
                              title="View Tax Invoice"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          /* Cards Grid View */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredInvoices.map((inv) => {
              const cfg = STATUS_CONFIGS[inv.status] || STATUS_CONFIGS.DRAFT;
              const balance = Number(inv.balance_due || 0);
              return (
                <div
                  key={inv.id}
                  onClick={() => handleOpenDetail(inv)}
                  className="bg-white border border-zinc-200/90 rounded-lg p-4 shadow-xs hover:shadow-md hover:border-zinc-300 transition-all cursor-pointer flex flex-col justify-between gap-3 group"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono font-bold text-zinc-950 group-hover:text-indigo-600 transition-colors">
                            {inv.invoice_number}
                          </span>
                        </div>
                        <p className="text-[10px] text-zinc-400 mt-0.5">
                          Issued: {formatDate(inv.issued_at)}
                        </p>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${cfg.badgeClass}`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${cfg.dotClass}`} />
                        {cfg.label}
                      </span>
                    </div>

                    <div className="mt-3 pt-3 border-t border-zinc-100 flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-zinc-100 text-zinc-700 font-bold text-[10px] flex items-center justify-center shrink-0 border border-zinc-200">
                        {(inv.bill_to_name || 'C').charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-zinc-900 truncate">
                          {inv.bill_to_name || 'Customer'}
                        </p>
                        <p className="text-[10px] text-zinc-500 truncate">
                          {inv.service_name || inv.service_category || 'Service'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-zinc-100 flex items-center justify-between">
                    <div>
                      <p className="text-[10px] text-zinc-400 uppercase font-semibold">Total</p>
                      <p className="text-sm font-extrabold text-zinc-950">
                        {formatMoney(inv.total_amount)}
                      </p>
                    </div>
                    {balance > 0 ? (
                      <div className="text-right">
                        <p className="text-[10px] text-amber-600 uppercase font-semibold">
                          Balance Due
                        </p>
                        <p className="text-xs font-bold text-amber-700">
                          {formatMoney(balance)}
                        </p>
                      </div>
                    ) : (
                      <div className="text-right">
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200/60">
                          <CheckCircle2 className="w-3 h-3" /> Fully Paid
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Enterprise Tax Invoice Modal */}
        {selectedInvoice && (
          <TaxInvoiceModal
            invoice={selectedInvoice}
            onClose={() => setSelectedInvoice(null)}
            onPaymentRecorded={(updated, message) => {
              setSelectedInvoice(updated);
              setInvoices((prev) =>
                prev.map((i) => (i.id === updated.id ? { ...i, ...updated } : i))
              );
              setFlashMessage(message);
            }}
            onError={(err) => setError(err)}
          />
        )}
      </div>
    </AppShell>
  );
}

/**
 * Enterprise GST Tax Invoice Modal with Print and PDF Support
 */
function TaxInvoiceModal({ invoice, onClose, onPaymentRecorded, onError }) {
  const [amount, setAmount] = useState(String(invoice.balance_due || ''));
  const [method, setMethod] = useState('ONLINE');
  const [reference, setReference] = useState('');
  const [isSavingPayment, setIsSavingPayment] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const outstanding = Number(invoice.balance_due || 0);
  const total = Number(invoice.total_amount || 0);
  const subtotal = Number(invoice.subtotal_amount || 0);
  const tax = Number(invoice.tax_amount || 0);
  const paid = Number(invoice.amount_paid || 0);

  const cfg = STATUS_CONFIGS[invoice.status] || STATUS_CONFIGS.DRAFT;

  async function handleRecordPayment(e) {
    e.preventDefault();
    if (!Number(amount) || Number(amount) <= 0) return;

    setIsSavingPayment(true);
    try {
      const result = await apiRecordInvoicePayment(invoice.id, {
        amount,
        method,
        reference,
      });
      onPaymentRecorded(
        result.invoice,
        result.duplicate
          ? `Reference "${reference}" was already logged on this invoice.`
          : `Payment of ${formatMoney(amount)} successfully recorded!`
      );
      setReference('');
    } catch (err) {
      onError(err?.message || 'Could not record payment.');
    } finally {
      setIsSavingPayment(false);
    }
  }

  async function handleDownloadPdf() {
    setIsDownloadingPdf(true);
    try {
      const blob = await apiRequest(`/workforce/invoices/${invoice.id}/pdf/`, { raw: true });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${invoice.invoice_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      onError(err?.message || 'Could not generate PDF.');
    } finally {
      setIsDownloadingPdf(false);
    }
  }

  function handlePrint() {
    const previousTitle = document.title;
    document.title = invoice?.invoice_number ? `${invoice.invoice_number}` : 'SEVO Tax Invoice';
    window.print();
    setTimeout(() => {
      document.title = previousTitle;
    }, 1500);
  }

  return (
    <div
      className="fixed inset-0 bg-zinc-950/60 backdrop-blur-xs flex items-center justify-center z-50 p-3 sm:p-4 overflow-y-auto animate-in fade-in"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-2xl my-auto overflow-hidden border border-zinc-200 flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header Bar (Hidden during Print) */}
        <div className="no-print px-5 py-3.5 bg-zinc-900 text-white flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2">
            <Receipt className="w-4 h-4 text-emerald-400" />
            <span className="font-mono font-bold text-sm tracking-wide text-white">
              {invoice.invoice_number}
            </span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${cfg.badgeClass}`}
            >
              {cfg.label}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-100 rounded-md transition"
              title="Print Tax Invoice"
            >
              <Printer className="w-3.5 h-3.5 text-zinc-300" />
              <span>Print</span>
            </button>
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={isDownloadingPdf}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-100 rounded-md transition disabled:opacity-50"
              title="Download Official PDF"
            >
              {isDownloadingPdf ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Download className="w-3.5 h-3.5 text-emerald-400" />
              )}
              <span>Download PDF</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-white transition ml-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body / Printable Invoice Sheet */}
        <div
          id="printable-tax-invoice"
          className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5 bg-white text-zinc-900"
        >
          {/* Invoice Company & Document Details */}
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-zinc-200">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base text-zinc-950 tracking-tight">
                  SEVO
                </span>
                <span className="text-[10px] font-bold bg-zinc-100 px-1.5 py-0.5 rounded-sm text-zinc-600 border border-zinc-200">
                  TAX INVOICE
                </span>
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">
                On-Demand Field Service & Operations Platform
              </p>
              {(invoice.job_request_id || invoice.job_id) && (
                <div className="text-xs text-zinc-700 mt-1.5 flex items-center gap-1.5 flex-wrap">
                  <span className="text-zinc-500 font-normal">Booking Reference:</span>
                  <span className="font-mono font-bold text-zinc-950 bg-zinc-100 px-1.5 py-0.5 rounded">
                    {invoice.job_request_id || `Job #${invoice.job_id}`}
                  </span>
                </div>
              )}
            </div>

            <div className="sm:text-right text-xs space-y-1 text-zinc-600">
              <p>
                <span className="text-zinc-400 font-medium">Invoice Date:</span>{' '}
                <strong className="text-zinc-900">{formatDate(invoice.issued_at)}</strong>
              </p>
              <p>
                <span className="text-zinc-400 font-medium">Payment Due Date:</span>{' '}
                <strong className="text-zinc-900">{formatDate(invoice.due_at)}</strong>
              </p>
              {(invoice.technician_name || invoice.technician_id) && (
                <p>
                  <span className="text-zinc-400 font-medium">Assigned Technician:</span>{' '}
                  <strong className="text-zinc-900 font-semibold">
                    {invoice.technician_name || `Technician #${invoice.technician_id}`}
                  </strong>
                </p>
              )}
            </div>
          </div>

          {/* Customer Bill To Box */}
          <div className="bg-zinc-50 border border-zinc-200/90 rounded-lg p-3.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
              Billed To (Customer)
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div>
                <p className="font-bold text-zinc-900 text-sm">
                  {invoice.bill_to_name || 'Valued Customer'}
                </p>
                {invoice.bill_to_phone && (
                  <p className="text-zinc-600 flex items-center gap-1.5 mt-0.5">
                    <Phone className="w-3 h-3 text-zinc-400" />
                    {invoice.bill_to_phone}
                  </p>
                )}
                {invoice.bill_to_email && (
                  <p className="text-zinc-600 truncate mt-0.5">{invoice.bill_to_email}</p>
                )}
              </div>
              {invoice.bill_to_address && (
                <div>
                  <p className="text-zinc-500 flex items-start gap-1.5 leading-relaxed">
                    <MapPin className="w-3.5 h-3.5 text-zinc-400 shrink-0 mt-0.5" />
                    <span>{invoice.bill_to_address}</span>
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Itemized Line Items Table */}
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-600 mb-2">
              Itemized Charges & Services
            </p>
            <div className="border border-zinc-200 rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-zinc-100/80 border-b border-zinc-200 text-zinc-700 text-[10px] font-bold uppercase">
                    <th className="py-2 px-3">Item / Service Description</th>
                    <th className="py-2 px-3 text-center">Qty</th>
                    <th className="py-2 px-3 text-right">Unit Rate</th>
                    <th className="py-2 px-3 text-right">Line Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 text-zinc-800">
                  {(invoice.items || []).length > 0 ? (
                    invoice.items.map((item, idx) => (
                      <tr key={item.id || idx} className="hover:bg-zinc-50/50">
                        <td className="py-2.5 px-3">
                          <p className="font-semibold text-zinc-900">{item.name}</p>
                          {item.description && (
                            <p className="text-[10px] text-zinc-500 mt-0.5">{item.description}</p>
                          )}
                          {item.section && item.section !== 'Service' && (
                            <span className="text-[9px] font-bold text-zinc-500 uppercase bg-zinc-100 px-1 py-0.2 rounded-sm">
                              {item.section}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono">
                          {item.quantity} {item.unit || ''}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono">
                          {formatMoney(item.unit_price)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold font-mono text-zinc-950">
                          {formatMoney(item.line_total)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="py-2.5 px-3 font-semibold">
                        {invoice.service_name || invoice.service_category || 'Service'}
                      </td>
                      <td className="py-2.5 px-3 text-center">1</td>
                      <td className="py-2.5 px-3 text-right">{formatMoney(total)}</td>
                      <td className="py-2.5 px-3 text-right font-bold">{formatMoney(total)}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Tax Breakdown & Financial Totals */}
          <div className="flex flex-col sm:flex-row justify-end pt-2">
            <div className="w-full sm:w-64 space-y-1.5 text-xs bg-zinc-50 p-3.5 rounded-lg border border-zinc-200">
              <div className="flex justify-between text-zinc-600">
                <span>Subtotal (Excl. Tax)</span>
                <span className="font-mono">{formatMoney(subtotal)}</span>
              </div>
              {tax > 0 && (
                <div className="flex justify-between text-zinc-600">
                  <span>GST (18% Integrated)</span>
                  <span className="font-mono">{formatMoney(tax)}</span>
                </div>
              )}
              <div className="pt-2 border-t border-zinc-200 flex justify-between text-sm font-bold text-zinc-950">
                <span>Total Amount</span>
                <span className="font-mono">{formatMoney(total)}</span>
              </div>
              <div className="flex justify-between text-emerald-700 font-medium">
                <span>Amount Paid</span>
                <span className="font-mono">{formatMoney(paid)}</span>
              </div>
              <div className="pt-1 border-t border-zinc-200 flex justify-between text-xs font-bold text-zinc-900">
                <span className={outstanding > 0 ? 'text-amber-800' : 'text-zinc-600'}>
                  Balance Due
                </span>
                <span
                  className={`font-mono font-bold ${
                    outstanding > 0 ? 'text-amber-800' : 'text-emerald-700'
                  }`}
                >
                  {formatMoney(outstanding)}
                </span>
              </div>
            </div>
          </div>

          {/* Payment History Records */}
          {(invoice.payments || []).length > 0 && (
            <div className="pt-3 border-t border-zinc-200">
              <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-600 mb-2">
                Payment History
              </p>
              <div className="space-y-1.5">
                {invoice.payments.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between bg-zinc-50 border border-zinc-200 rounded-md px-3 py-2 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <CreditCard className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="font-semibold text-zinc-900">{p.method}</span>
                      {p.reference && (
                        <span className="text-zinc-500 font-mono text-[10px]">
                          Ref: {p.reference}
                        </span>
                      )}
                      {p.created_at && (
                        <span className="text-zinc-400 text-[10px]">
                          · {formatDate(p.created_at)}
                        </span>
                      )}
                    </div>
                    <span className="font-mono font-bold text-emerald-700">
                      {formatMoney(p.amount)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Inline Record Payment Form (Hidden during Print) */}
          {outstanding > 0 && invoice.status !== 'CANCELLED' && (
            <form
              onSubmit={handleRecordPayment}
              className="no-print bg-amber-50/70 border border-amber-200/90 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center gap-2 text-amber-900 font-bold text-xs">
                <IndianRupee className="w-4 h-4 text-amber-600" />
                <span>Record Direct Customer Settlement</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] font-semibold text-zinc-600 uppercase mb-1">
                    Amount to Collect (INR)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={outstanding}
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="w-full bg-white border border-zinc-300 rounded-md px-3 py-1.5 text-xs text-zinc-900 font-bold"
                    placeholder="Enter amount"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-zinc-600 uppercase mb-1">
                    Payment Method
                  </label>
                  <select
                    value={method}
                    onChange={(e) => setMethod(e.target.value)}
                    className="w-full bg-white border border-zinc-300 rounded-md px-3 py-1.5 text-xs text-zinc-900"
                  >
                    {PAYMENT_METHODS.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-zinc-600 uppercase mb-1">
                  Transaction / UPI Reference Number
                </label>
                <input
                  type="text"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  className="w-full bg-white border border-zinc-300 rounded-md px-3 py-1.5 text-xs text-zinc-900 font-mono"
                  placeholder="e.g. UPI-9382104928 or Cash receipt ID"
                />
              </div>

              <button
                type="submit"
                disabled={isSavingPayment || !Number(amount)}
                className="w-full inline-flex items-center justify-center gap-2 bg-zinc-900 hover:bg-zinc-800 text-white font-bold text-xs py-2 px-4 rounded-md transition shadow-xs disabled:opacity-50"
              >
                {isSavingPayment ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                )}
                <span>Record Payment of {formatMoney(amount)}</span>
              </button>
            </form>
          )}
        </div>

        {/* Modal Footer (Hidden during Print) */}
        <div className="no-print px-5 py-3 bg-zinc-50 border-t border-zinc-200 flex items-center justify-between text-xs text-zinc-500">
          <span>SEVO Invoicing</span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-xs font-semibold bg-white border border-zinc-300 rounded-md text-zinc-700 hover:bg-zinc-100 transition shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default InvoicesPage;
