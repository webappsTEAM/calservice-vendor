import React, { useState, useEffect } from 'react';
import {
  X,
  Printer,
  FileText,
  AlertCircle,
  Loader2,
  ExternalLink,
  ShieldCheck,
  Building2,
  User,
  Wrench,
} from 'lucide-react';
import { apiGetEstimationInvoice } from '../../api/vendorEstimationService.js';

export default function EstimationInvoiceModal({ isOpen, onClose, estimationId }) {
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen || !estimationId) return;

    let mounted = true;
    setLoading(true);
    setError(null);

    apiGetEstimationInvoice(estimationId)
      .then((res) => {
        if (mounted) {
          setInvoice(res.invoice || res.data?.invoice || null);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message || 'Failed to fetch invoice details from database.');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [isOpen, estimationId]);

  if (!isOpen) return null;

  const handlePrint = () => {
    const printUrl = `/api/vendor/estimations/${estimationId}/invoice/?format=html`;
    const win = window.open(printUrl, '_blank');
    if (win) {
      win.focus();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-zinc-200 flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center border border-emerald-200/60">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-900">Official Database Invoice</h3>
              <p className="text-[11px] text-zinc-500 font-mono">
                {invoice?.invoice_number || `INV-EST-${estimationId}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {invoice && (
              <button
                type="button"
                onClick={handlePrint}
                className="px-3 py-1.5 text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg flex items-center gap-1.5 shadow-xs transition-colors"
                title="Print or Save as PDF"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print / PDF</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center text-zinc-400 gap-3">
              <Loader2 className="w-7 h-7 animate-spin text-emerald-600" />
              <p className="text-xs font-medium">Fetching invoice record from database...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
              <div>
                <strong className="block font-bold mb-0.5">Could not load invoice</strong>
                <span>{error}</span>
              </div>
            </div>
          ) : invoice ? (
            <div className="space-y-6">
              {/* Invoice Meta Bar */}
              <div className="flex items-center justify-between p-4 bg-zinc-50 rounded-xl border border-zinc-200/80">
                <div>
                  <span className="text-[11px] text-zinc-500 font-medium block">Invoice Date</span>
                  <span className="text-xs font-bold text-zinc-900">{invoice.invoice_date}</span>
                </div>
                <div>
                  <span className="text-[11px] text-zinc-500 font-medium block">Payment Status</span>
                  <span
                    className={`inline-block px-2.5 py-0.5 text-[10px] font-bold rounded-full uppercase border ${
                      invoice.status === 'PAID'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}
                  >
                    {invoice.status}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] text-zinc-500 font-medium block">Total Due / Paid</span>
                  <span className="text-sm font-extrabold text-zinc-900 font-mono">
                    ₹{Number(invoice.total_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              {/* Company & Customer Details Grid */}
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="p-3.5 bg-white border border-zinc-200 rounded-xl space-y-1.5">
                  <div className="flex items-center gap-1.5 text-zinc-400 font-semibold text-[11px] uppercase tracking-wider">
                    <Building2 className="w-3.5 h-3.5" />
                    <span>Issued By</span>
                  </div>
                  <div className="font-bold text-zinc-900">{invoice.company?.name || 'CalServices Network'}</div>
                  <div className="text-zinc-600">{invoice.company?.address || 'Chennai, Tamil Nadu'}</div>
                  <div className="text-[11px] text-zinc-500">GSTIN: {invoice.company?.gstin || '33AABCC1234D1Z5'}</div>
                  <div className="text-[11px] text-zinc-500">Phone: {invoice.company?.phone || '+91 98765 43210'}</div>
                </div>

                <div className="p-3.5 bg-white border border-zinc-200 rounded-xl space-y-1.5">
                  <div className="flex items-center gap-1.5 text-zinc-400 font-semibold text-[11px] uppercase tracking-wider">
                    <User className="w-3.5 h-3.5" />
                    <span>Billed To</span>
                  </div>
                  <div className="font-bold text-zinc-900">{invoice.customer?.name || 'Customer'}</div>
                  <div className="text-zinc-600">{invoice.customer?.address || 'Registered Address'}</div>
                  <div className="text-[11px] text-zinc-500">Phone: {invoice.customer?.phone || 'N/A'}</div>
                  {invoice.technician?.name && (
                    <div className="text-[11px] text-zinc-500 flex items-center gap-1 mt-1 pt-1 border-t border-zinc-100">
                      <Wrench className="w-3 h-3 text-emerald-600" />
                      <span>Technician: <strong>{invoice.technician.name}</strong></span>
                    </div>
                  )}
                </div>
              </div>

              {/* Line Items Table */}
              <div className="border border-zinc-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-zinc-50 text-zinc-600 font-bold border-b border-zinc-200 text-[11px]">
                      <th className="py-2.5 px-4">Item & Description</th>
                      <th className="py-2.5 px-3 text-center">Qty</th>
                      <th className="py-2.5 px-3 text-right">Unit Rate</th>
                      <th className="py-2.5 px-4 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100">
                    {invoice.line_items?.map((item, idx) => (
                      <tr key={idx} className="hover:bg-zinc-50/50">
                        <td className="py-2.5 px-4">
                          <div className="font-semibold text-zinc-900">{item.item_name}</div>
                          {item.description && (
                            <div className="text-[11px] text-zinc-500">{item.description}</div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center text-zinc-700">
                          {item.quantity} {item.unit || ''}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-zinc-700">
                          ₹{Number(item.unit_price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2.5 px-4 text-right font-mono font-bold text-zinc-900">
                          ₹{Number(item.total).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Summary Totals */}
              <div className="flex justify-end">
                <div className="w-64 space-y-1.5 text-xs">
                  <div className="flex justify-between text-zinc-600">
                    <span>Subtotal:</span>
                    <span className="font-mono">
                      ₹{Number(invoice.subtotal).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between text-zinc-600">
                    <span>GST / Tax:</span>
                    <span className="font-mono">
                      ₹{Number(invoice.tax_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between pt-2 border-t border-zinc-200 text-sm font-extrabold text-zinc-900">
                    <span>Grand Total:</span>
                    <span className="font-mono text-emerald-700">
                      ₹{Number(invoice.total_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Payment Receipt / Reference info */}
              {invoice.payment?.payment_reference && (
                <div className="p-3 bg-emerald-50/60 border border-emerald-200/80 rounded-xl flex items-center justify-between text-xs text-emerald-900">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    <span>
                      Payment Ref: <strong className="font-mono">{invoice.payment.payment_reference}</strong> ({invoice.payment.payment_method})
                    </span>
                  </div>
                  <span className="text-[11px] font-semibold text-emerald-700 uppercase">
                    {invoice.payment.status}
                  </span>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-zinc-100 bg-zinc-50 flex items-center justify-between text-xs">
          <span className="text-zinc-500 text-[11px]">
            Authoritative relational record saved in <code className="text-zinc-700">settings_hub_invoice</code>
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              className="px-3 py-1.5 font-medium text-zinc-700 hover:text-zinc-900 hover:bg-zinc-200 rounded-lg flex items-center gap-1 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Open Full Page</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 font-semibold bg-white border border-zinc-300 text-zinc-800 hover:bg-zinc-100 rounded-lg transition-colors shadow-xs"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
