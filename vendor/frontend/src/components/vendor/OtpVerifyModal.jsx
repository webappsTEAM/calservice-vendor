import React, { useState } from 'react';
import { X, KeyRound, ShieldCheck, AlertCircle, Loader2 } from 'lucide-react';
import { apiVerifyOtp } from '../../api/vendorEstimationService.js';

export default function OtpVerifyModal({ estimation, isOpen, onClose, onSuccess }) {
  const [otp, setOtp] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanOtp = otp.trim();
    if (!cleanOtp) {
      setError('Please enter the 6-digit OTP provided by customer.');
      return;
    }

    setVerifying(true);
    setError(null);
    try {
      const res = await apiVerifyOtp(estimation.id, cleanOtp);
      onSuccess?.(res?.data || res);
      onClose();
    } catch (err) {
      setError(err.message || 'Invalid OTP. Please verify with the customer.');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/60 backdrop-blur-xs animate-in fade-in">
      <div className="relative w-full max-w-sm bg-white rounded-xl shadow-2xl border border-zinc-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-100 bg-amber-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center border border-amber-200">
              <KeyRound className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-900">Verify Customer OTP</h3>
              <p className="text-[11px] text-zinc-500">Lead #{estimation?.request_id || estimation?.id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <p className="text-xs text-zinc-600 leading-relaxed">
            Please ask customer <strong className="text-zinc-900">{estimation?.customer_name || 'Customer'}</strong> for the 6-digit arrival start OTP shown on their app or SMS to commence inspection.
          </p>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-zinc-700 mb-1.5 text-center">
              Enter 6-Digit Start OTP
            </label>
            <input
              type="text"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              placeholder="• • • • • •"
              autoFocus
              className="w-full text-center tracking-[0.6em] text-xl font-mono font-bold py-2.5 px-3 border-2 border-amber-300 focus:border-amber-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500/20 bg-amber-50/20"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-2.5 border-t border-zinc-100">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={verifying || otp.trim().length < 4}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-lg shadow-sm flex items-center gap-1.5 transition-colors"
            >
              {verifying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
              <span>{verifying ? 'Verifying...' : 'Verify & Start Inspection'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
