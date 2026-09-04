import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  IndianRupee,
  AlertTriangle,
  Loader2,
  ChevronDown,
  Sparkles,
  Calendar,
  Wrench,
  FileText,
  CreditCard,
  Zap,
} from 'lucide-react';
import { apiReviseQuotation, apiCustomerDecide } from '../../api/vendorEstimationService.js';
import EstimationInvoiceModal from './EstimationInvoiceModal.jsx';

export default function CustomerDecisionPanel({
  estimation,
  onReviseQuote,
  onOpenFeeModal,
  onUpdate,
}) {
  const [revising, setRevising] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showSimMenu, setShowSimMenu] = useState(false);
  const [error, setError] = useState(null);

  // Modals
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);

  // Approval / Booking Schedule Form
  const todayStr = new Date().toISOString().split('T')[0];
  const [scheduledDate, setScheduledDate] = useState(todayStr);
  const [scheduledTime, setScheduledTime] = useState('10:00 AM - 01:00 PM');

  // Rejection / Cancellation Form
  const [rejectionReason, setRejectionReason] = useState('PRICE_TOO_HIGH');
  const [rejectionNote, setRejectionNote] = useState('');
  const [feePaymentMethod, setFeePaymentMethod] = useState('UPI');

  const quote = estimation?.latest_quotation || (estimation?.quotations && estimation.quotations[0]);
  const status = (quote?.status || estimation?.status || 'DRAFT').toUpperCase();
  const fee = estimation?.fee;
  const isSameDay = scheduledDate === todayStr;
  const techName = estimation?.inspection?.technician_name || estimation?.technician_name || 'Assigned Technician';

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

  const handleConfirmApproval = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await apiCustomerDecide(estimation.id, {
        decision: 'APPROVE',
        scheduled_date: scheduledDate,
        scheduled_time: scheduledTime,
      });
      setShowApproveModal(false);
      onUpdate?.(res?.data || res);
    } catch (err) {
      setError(err.message || 'Failed to approve quotation and book job.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmRejection = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await apiCustomerDecide(estimation.id, {
        decision: 'REJECT',
        rejection_reason: rejectionReason,
        rejection_note: rejectionNote,
        payment_method: feePaymentMethod,
      });
      setShowRejectModal(false);
      onUpdate?.(res?.data || res);
    } catch (err) {
      setError(err.message || 'Failed to reject estimation.');
    } finally {
      setSubmitting(false);
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
      {status === 'APPROVED' || estimation?.status === 'CUSTOMER_APPROVED' || estimation?.status === 'CONVERTED_TO_JOB' ? (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-3">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-bold text-emerald-900">
                  Customer Accepted Quotation #{quote?.quote_ref || ''} — Converted into Service Job
                </h4>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-extrabold rounded-full">
                  JOB CONVERTED
                </span>
              </div>
              <p className="text-xs text-emerald-700 leading-relaxed">
                Accepted total: <strong>₹{quote?.total_amount?.toLocaleString('en-IN')}</strong>. The ₹199 estimation visit fee is waived/credited towards the job. Only the service job payment will be collected upon completion.
              </p>
            </div>
          </div>
          <div className="pt-2.5 border-t border-emerald-200/80 flex items-center justify-between">
            <span className="text-[11px] text-emerald-800 font-medium">
              Scheduled with technician: <strong>{techName}</strong>
            </span>
            <button
              type="button"
              onClick={() => setShowInvoiceModal(true)}
              className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>View Invoice</span>
            </button>
          </div>
        </div>
      ) : status === 'REJECTED' || estimation?.status === 'CUSTOMER_REJECTED' || estimation?.status === 'CANCELLED' ? (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-3">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="space-y-1 flex-1">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-rose-900">
                  Estimation Cancelled / Quotation #{quote?.quote_ref || ''} Rejected
                </h4>
                {estimation?.invoice_id && (
                  <span className="text-[11px] font-mono text-rose-800 bg-rose-100 px-2 py-0.5 rounded-md font-semibold">
                    {estimation.invoice_id}
                  </span>
                )}
              </div>
              <p className="text-xs text-rose-700">
                Reason: <strong className="uppercase">{quote?.rejection_reason || 'PRICE_TOO_HIGH'}</strong>
                {quote?.rejection_note ? ` — "${quote.rejection_note}"` : ''}
              </p>
              <p className="text-[11px] text-zinc-600 mt-1">
                Diagnostic fee of ₹199 was collected. An official invoice is generated in the database and accessible by the customer.
              </p>
            </div>
          </div>
          <div className="pt-2 border-t border-rose-200 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setShowInvoiceModal(true)}
              className="px-3 py-1.5 bg-white border border-rose-300 hover:bg-rose-100 text-rose-800 font-bold text-xs rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
            >
              <FileText className="w-3.5 h-3.5 text-rose-600" />
              <span>Download / View Invoice</span>
            </button>

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
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-blue-600 animate-pulse shrink-0" />
              <div>
                <h4 className="text-xs font-bold text-blue-900">
                  Quotation #{quote?.quote_ref || ''} Sent — Awaiting Customer Decision
                </h4>
                <p className="text-[11px] text-blue-700">
                  Customer proposal total: <strong>₹{quote?.total_amount?.toLocaleString('en-IN')}</strong>.
                </p>
              </div>
            </div>

            {/* Quick Actions / Simulator Trigger */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowApproveModal(true)}
                className="px-3 py-1.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Customer Accepts & Books</span>
              </button>
              <button
                type="button"
                onClick={() => setShowRejectModal(true)}
                className="px-2.5 py-1.5 text-xs font-bold bg-white border border-rose-300 text-rose-700 hover:bg-rose-50 rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Customer Rejects</span>
              </button>
            </div>
          </div>

          <div className="text-[11px] text-blue-800 bg-blue-100/60 p-2.5 rounded-lg">
            <strong>Flow Note:</strong> When the customer accepts, the estimation is automatically converted into an active Job. The customer can reschedule or pick today's date (which auto-assigns the same technician).
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
                ? `Collected via ${fee.payment_method || 'UPI'}`
                : fee?.status === 'WAIVED'
                ? `Waived: "${fee.waived_reason || 'Credited towards accepted service booking'}"`
                : 'Fee collected if cancelled, or waived when customer accepts quotation and books job.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {(fee?.status === 'COLLECTED' || estimation?.invoice_id) && (
            <button
              type="button"
              onClick={() => setShowInvoiceModal(true)}
              className="px-3 py-1.5 text-xs font-semibold bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-800 rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
            >
              <FileText className="w-3.5 h-3.5 text-emerald-600" />
              <span>Invoice</span>
            </button>
          )}

          {fee?.status === 'PENDING' && (
            <button
              type="button"
              onClick={onOpenFeeModal}
              className="px-3 py-1.5 text-xs font-bold bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-800 rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
            >
              <IndianRupee className="w-3.5 h-3.5 text-emerald-600" />
              <span>Collect / Waive Fee</span>
            </button>
          )}
        </div>
      </div>

      {/* Customer Acceptance & Job Booking Modal */}
      {showApproveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-zinc-200 p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <h3 className="text-sm font-bold text-zinc-900">Accept Quotation & Book Job</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowApproveModal(false)}
                className="text-zinc-400 hover:text-zinc-700"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-200 space-y-1">
                <div className="flex justify-between font-bold text-zinc-800">
                  <span>Quotation: #{quote?.quote_ref}</span>
                  <span className="font-mono text-emerald-700">₹{Number(quote?.total_amount).toLocaleString('en-IN')}</span>
                </div>
                <p className="text-[11px] text-zinc-500">
                  Acceptance converts this estimation into an active service job.
                </p>
              </div>

              {/* Date Selection */}
              <div>
                <label className="block font-semibold text-zinc-700 mb-1">
                  Preferred Service Date (Reschedule / Book)
                </label>
                <div className="relative">
                  <input
                    type="date"
                    min={todayStr}
                    value={scheduledDate}
                    onChange={(e) => setScheduledDate(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-zinc-300 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500 font-medium"
                  />
                </div>
              </div>

              {/* Time Slot Selection */}
              <div>
                <label className="block font-semibold text-zinc-700 mb-1">
                  Preferred Time Slot
                </label>
                <select
                  value={scheduledTime}
                  onChange={(e) => setScheduledTime(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-zinc-300 rounded-lg text-xs focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="10:00 AM - 01:00 PM">10:00 AM - 01:00 PM (Morning)</option>
                  <option value="02:00 PM - 05:00 PM">02:00 PM - 05:00 PM (Afternoon)</option>
                  <option value="05:00 PM - 08:00 PM">05:00 PM - 08:00 PM (Evening)</option>
                </select>
              </div>

              {/* Same-Day vs Rescheduled Rule Explanation */}
              {isSameDay ? (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1 text-emerald-900">
                  <div className="flex items-center gap-1.5 font-bold">
                    <Zap className="w-3.5 h-3.5 text-amber-500" />
                    <span>Same-Day Assignment Rule:</span>
                  </div>
                  <p className="text-[11px] text-emerald-800 leading-relaxed">
                    Because this job is scheduled for today, it will be <strong>automatically assigned to the same technician ({techName})</strong> who performed the inspection!
                  </p>
                  <p className="text-[11px] text-emerald-700 font-medium mt-1">
                    ✓ The ₹199 diagnostic visit fee is waived. Only the actual job total (₹{quote?.total_amount}) will be collected upon job completion.
                  </p>
                </div>
              ) : (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl space-y-1 text-blue-900">
                  <div className="flex items-center gap-1.5 font-bold">
                    <Calendar className="w-3.5 h-3.5 text-blue-600" />
                    <span>Scheduled for Future Date:</span>
                  </div>
                  <p className="text-[11px] text-blue-800 leading-relaxed">
                    Job will be booked for <strong>{new Date(scheduledDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</strong>.
                  </p>
                  <p className="text-[11px] text-blue-700 font-medium mt-1">
                    ✓ The ₹199 diagnostic visit fee is waived.
                  </p>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-100">
              <button
                type="button"
                onClick={() => setShowApproveModal(false)}
                className="px-3.5 py-2 text-xs font-semibold text-zinc-600 hover:text-zinc-800 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={handleConfirmApproval}
                className="px-4 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm flex items-center gap-1.5 transition-colors"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                <span>Confirm & Convert to Job</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Customer Rejection / Cancellation Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl border border-zinc-200 p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
              <div className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-rose-600" />
                <h3 className="text-sm font-bold text-zinc-900">Cancel Estimation & Collect Visit Fee</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowRejectModal(false)}
                className="text-zinc-400 hover:text-zinc-700"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-zinc-700 mb-1">
                  Reason for Cancellation
                </label>
                <select
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-zinc-300 rounded-lg text-xs focus:ring-2 focus:ring-rose-500"
                >
                  <option value="PRICE_TOO_HIGH">Quotation Price Too High</option>
                  <option value="WILL_DO_LATER">Customer Postponed Work</option>
                  <option value="LOCAL_TECH_FOUND">Customer Found Alternative</option>
                  <option value="NO_REPAIR_NEEDED">No Repair Needed</option>
                  <option value="OTHER">Other Reason</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-zinc-700 mb-1">
                  Customer Notes / Feedback
                </label>
                <textarea
                  rows={2}
                  value={rejectionNote}
                  onChange={(e) => setRejectionNote(e.target.value)}
                  placeholder="Optional note explaining customer decision..."
                  className="w-full px-3 py-2 bg-white border border-zinc-300 rounded-lg text-xs focus:ring-2 focus:ring-rose-500"
                />
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-2 text-amber-900">
                <div className="flex items-center justify-between font-bold">
                  <span>Diagnostic Fee to Collect:</span>
                  <span className="font-mono text-sm">₹199.00</span>
                </div>
                <p className="text-[11px] text-amber-800">
                  Per policy, when estimation is cancelled, the ₹199 inspection visit fee is collected and a formal downloadable invoice is created in the database for the customer.
                </p>
                <div>
                  <label className="block text-[11px] font-semibold text-amber-950 mb-1">Payment Method</label>
                  <div className="grid grid-cols-3 gap-2">
                    {['UPI', 'CASH', 'ONLINE'].map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setFeePaymentMethod(m)}
                        className={`py-1.5 text-center rounded-lg font-bold text-[11px] border transition-colors ${
                          feePaymentMethod === m
                            ? 'bg-amber-600 text-white border-amber-600'
                            : 'bg-white text-zinc-700 border-zinc-300 hover:bg-zinc-50'
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-zinc-100">
              <button
                type="button"
                onClick={() => setShowRejectModal(false)}
                className="px-3.5 py-2 text-xs font-semibold text-zinc-600 hover:text-zinc-800 rounded-lg"
              >
                Back
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={handleConfirmRejection}
                className="px-4 py-2 text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white rounded-lg shadow-sm flex items-center gap-1.5 transition-colors"
              >
                {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CreditCard className="w-3.5 h-3.5" />}
                <span>Collect ₹199 & Cancel</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Invoice Viewer Modal */}
      <EstimationInvoiceModal
        isOpen={showInvoiceModal}
        onClose={() => setShowInvoiceModal(false)}
        estimationId={estimation?.id}
      />
    </div>
  );
}
