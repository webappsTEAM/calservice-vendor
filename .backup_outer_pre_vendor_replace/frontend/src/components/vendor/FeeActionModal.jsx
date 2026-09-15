import React, { useState } from 'react';
import { X, IndianRupee, CheckCircle2, ShieldOff, AlertCircle, Loader2 } from 'lucide-react';
import { apiCollectFee, apiWaiveFee } from '../../api/vendorEstimationService.js';

export default function FeeActionModal({ estimation, isOpen, onClose, onSuccess }) {
  const [actionTab, setActionTab] = useState('COLLECT'); // 'COLLECT' | 'WAIVE'
  const [paymentMethod, setPaymentMethod] = useState('CASH'); // 'CASH' | 'UPI'
  const [reference, setReference] = useState('');
  const [waiveReason, setWaiveReason] = useState('Customer approved major repair work quotation.');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      let res;
      if (actionTab === 'COLLECT') {
        res = await apiCollectFee(estimation.id, {
          payment_method: paymentMethod,
          payment_reference: reference.trim(),
        });
      } else {
        res = await apiWaiveFee(estimation.id, {
          reason: waiveReason.trim(),
        });
      }
      onSuccess?.(res);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to update fee record.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/60 backdrop-blur-xs animate-in fade-in">
      <div className="relative w-full max-w-sm bg-white rounded-xl shadow-2xl border border-zinc-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-100 bg-zinc-50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
              <IndianRupee className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-900">Inspection Fee: ₹199</h3>
              <p className="text-[11px] text-zinc-500">Job #{estimation?.request_id || estimation?.id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Toggle */}
        <div className="flex border-b border-zinc-100 bg-zinc-50/50 p-1">
          <button
            type="button"
            onClick={() => setActionTab('COLLECT')}
            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
              actionTab === 'COLLECT'
                ? 'bg-white text-emerald-700 shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900'
            }`}
          >
            Collect Payment
          </button>
          <button
            type="button"
            onClick={() => setActionTab('WAIVE')}
            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
              actionTab === 'WAIVE'
                ? 'bg-white text-purple-700 shadow-xs'
                : 'text-zinc-500 hover:text-zinc-900'
            }`}
          >
            Waive Fee
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
              <span>{error}</span>
            </div>
          )}

          {actionTab === 'COLLECT' ? (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">
                  Collection Method
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('CASH')}
                    className={`p-2.5 rounded-lg border text-xs font-bold text-center transition-all ${
                      paymentMethod === 'CASH'
                        ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                        : 'bg-white border-zinc-200 text-zinc-600'
                    }`}
                  >
                    💵 Cash
                  </button>
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('UPI')}
                    className={`p-2.5 rounded-lg border text-xs font-bold text-center transition-all ${
                      paymentMethod === 'UPI'
                        ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                        : 'bg-white border-zinc-200 text-zinc-600'
                    }`}
                  >
                    📱 UPI / QR
                  </button>
                </div>
              </div>

              {paymentMethod === 'UPI' && (
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">
                    UPI Transaction ID / Ref
                  </label>
                  <input
                    type="text"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    placeholder="e.g. 328901239840"
                    className="w-full text-xs px-3 py-2 border border-zinc-200 rounded-lg"
                  />
                </div>
              )}
            </div>
          ) : (
            <div>
              <label className="block text-xs font-semibold text-zinc-700 mb-1">
                Reason for Waiving ₹199 Fee <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={3}
                value={waiveReason}
                onChange={(e) => setWaiveReason(e.target.value)}
                required
                className="w-full text-xs p-2.5 border border-zinc-200 rounded-lg"
              />
              <p className="text-[10px] text-zinc-500 mt-1">
                Typically waived when the customer accepts an extensive repair quotation.
              </p>
            </div>
          )}

          <div className="pt-2 flex items-center justify-end gap-2.5 border-t border-zinc-100">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`px-4 py-1.5 text-xs font-bold text-white rounded-lg shadow-sm flex items-center gap-1.5 transition-colors ${
                actionTab === 'COLLECT'
                  ? 'bg-emerald-600 hover:bg-emerald-700'
                  : 'bg-purple-600 hover:bg-purple-700'
              }`}
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
              <span>{actionTab === 'COLLECT' ? 'Mark as Collected' : 'Confirm Waiver'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
