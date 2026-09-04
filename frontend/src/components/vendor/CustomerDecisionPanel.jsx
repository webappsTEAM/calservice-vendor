import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  IndianRupee,
  FileCheck,
  AlertTriangle,
  Send,
  Loader2,
  ChevronDown,
  Sparkles,
} from 'lucide-react';
import { apiReviseQuotation, apiCustomerDecide } from '../../api/vendorEstimationService.js';

export default function CustomerDecisionPanel({
  estimation,
  onReviseQuote,
  onOpenFeeModal,
  onUpdate,
}) {
  const [revising, setRevising] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [showSimMenu, setShowSimMenu] = useState(false);
  const [error, setError] = useState(null);

  const quote = estimation?.latest_quotation || (estimation?.quotations && estimation.quotations[0]);
  const status = (quote?.status || estimation?.status || 'DRAFT').toUpperCase();
  const fee = estimation?.fee;

  const handleRevise = async () => {
    if (!quote?.id) return;
    setRevising(true);
    setError(null);
    try {
      const res = await apiReviseQuotation(estimation.id, quote.id);
      onUpdate?.(res?.data || res);
      onReviseQuote?.();
    } catch (err) {
      setError(err.message || 'Failed to revise quotation.');
    } finally {
      setRevising(false);
    }
  };

  const handleSimulateDecision = async (decision, reason = 'PRICE_TOO_HIGH', note = 'Customer requested a lower price.') => {
    setSimulating(true);
    setError(null);
    setShowSimMenu(false);
    try {
      const res = await apiCustomerDecide(estimation.id, {
        decision,
        rejection_reason: reason,
        rejection_note: note,
      });
      onUpdate?.(res?.data || res);
    } catch (err) {
      setError(err.message || 'Simulation failed.');
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-xs text-red-700">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Decision Status Banners */}
      {status === 'APPROVED' || estimation?.status === 'CUSTOMER_APPROVED' ? (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-emerald-900">
              Customer Approved Quotation #{quote?.quote_ref || ''}
            </h4>
            <p className="text-xs text-emerald-700 leading-relaxed">
              Customer approved quotation of ₹{quote?.total_amount?.toLocaleString('en-IN')}. Ready to commence on-site repair work.
            </p>
          </div>
        </div>
      ) : status === 'REJECTED' || estimation?.status === 'CUSTOMER_REJECTED' ? (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-3">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-rose-900">
                Customer Rejected Quotation #{quote?.quote_ref || ''}
              </h4>
              <p className="text-xs text-rose-700">
                Reason: <strong className="uppercase">{quote?.rejection_reason || 'PRICE_TOO_HIGH'}</strong>
                {quote?.rejection_note ? ` — "${quote.rejection_note}"` : ''}
              </p>
            </div>
          </div>
          <div className="pt-2 border-t border-rose-200 flex items-center justify-between">
            <span className="text-[11px] text-rose-600">
              You can adjust item prices or apply a discount and re-send.
            </span>
            <button
              type="button"
              disabled={revising}
              onClick={handleRevise}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
            >
              {revising ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
              <span>Revise & Resend Quote</span>
            </button>
          </div>
        </div>
      ) : status === 'SENT' || estimation?.status === 'QUOTATION_SENT' ? (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-blue-600 animate-pulse shrink-0" />
            <div>
              <h4 className="text-xs font-bold text-blue-900">
                Quotation #{quote?.quote_ref || ''} Sent — Awaiting Customer Decision
              </h4>
              <p className="text-[11px] text-blue-700">
                Customer received proposal of ₹{quote?.total_amount?.toLocaleString('en-IN')}. The status will update automatically once decided.
              </p>
            </div>
          </div>

          {/* Test Decision Simulator Trigger */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowSimMenu(!showSimMenu)}
              className="px-2.5 py-1 text-[11px] font-semibold bg-white border border-blue-200 text-blue-700 rounded-lg hover:bg-blue-100 flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3 text-blue-500" />
              <span>Simulate Decision</span>
              <ChevronDown className="w-3 h-3" />
            </button>

            {showSimMenu && (
              <div className="absolute right-0 top-full mt-1 w-52 bg-white rounded-xl shadow-xl border border-zinc-200 py-1.5 z-20 animate-in fade-in">
                <button
                  type="button"
                  onClick={() => handleSimulateDecision('APPROVE')}
                  className="w-full text-left px-3 py-1.5 text-xs text-emerald-700 hover:bg-emerald-50 flex items-center gap-2 font-medium"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Customer Approves</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleSimulateDecision('REJECT', 'PRICE_TOO_HIGH', 'Competitor offered lower rate.')}
                  className="w-full text-left px-3 py-1.5 text-xs text-rose-700 hover:bg-rose-50 flex items-center gap-2 font-medium"
                >
                  <XCircle className="w-3.5 h-3.5 text-rose-600" />
                  <span>Customer Rejects (Price)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleSimulateDecision('REJECT', 'WILL_DO_LATER', 'Postponing to next month.')}
                  className="w-full text-left px-3 py-1.5 text-xs text-amber-700 hover:bg-amber-50 flex items-center gap-2 font-medium"
                >
                  <XCircle className="w-3.5 h-3.5 text-amber-600" />
                  <span>Customer Rejects (Later)</span>
                </button>
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* ₹199 Inspection Visit Fee Card */}
      <div className="p-4 bg-zinc-50 border border-zinc-200 rounded-xl flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center font-bold font-mono">
            ₹
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-zinc-900">
                Inspection Visit Fee: ₹{fee?.amount || 199}
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                  fee?.status === 'COLLECTED'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : fee?.status === 'WAIVED'
                    ? 'bg-purple-50 text-purple-700 border-purple-200'
                    : 'bg-amber-50 text-amber-700 border-amber-200'
                }`}
              >
                {fee?.status || 'PENDING'}
              </span>
            </div>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              {fee?.status === 'COLLECTED'
                ? `Collected via ${fee.payment_method || 'CASH'} on ${fee.collected_at ? new Date(fee.collected_at).toLocaleDateString() : 'today'}`
                : fee?.status === 'WAIVED'
                ? `Waived: "${fee.waived_reason || 'Approved major repair work'}"`
                : 'Mandatory standard visit fee due from customer upon inspection arrival.'}
            </p>
          </div>
        </div>

        {fee?.status === 'PENDING' && (
          <button
            type="button"
            onClick={onOpenFeeModal}
            className="px-3 py-1.5 text-xs font-bold bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-800 rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
          >
            <IndianRupee className="w-3.5 h-3.5 text-emerald-600" />
            <span>Collect or Waive Fee</span>
          </button>
        )}
      </div>
    </div>
  );
}
