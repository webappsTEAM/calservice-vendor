import React, { useEffect, useState, useCallback } from 'react';
import { AppShell } from '../../../components/common/AppShell.jsx';
import {
  apiAdminGetAllWithdrawals,
  apiAdminProcessWithdrawal,
  apiAdminCompleteWithdrawal,
  apiAdminFailWithdrawal,
} from '../../../api/walletService.js';
import {
  ArrowDownCircle,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Building2,
  Filter,
  X,
  Send,
  AlertTriangle,
} from 'lucide-react';

function fmt(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(parseFloat(value || 0));
}

const STATUS_COLORS = {
  REQUESTED: 'bg-amber-50 text-amber-900 border-amber-200',
  PROCESSING: 'bg-zinc-100 text-zinc-900 border-zinc-200',
  COMPLETED: 'bg-emerald-50 text-emerald-900 border-emerald-200',
  FAILED: 'bg-rose-50 text-rose-900 border-rose-200',
  CANCELLED: 'bg-zinc-100 text-zinc-600 border-zinc-200',
};

export function WalletWithdrawalsPage() {
  const [withdrawals, setWithdrawals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Complete Modal
  const [completeModalItem, setCompleteModalItem] = useState(null);
  const [bankTxnId, setBankTxnId] = useState('');
  const [completeSubmitting, setCompleteSubmitting] = useState(false);

  // Fail Modal
  const [failModalItem, setFailModalItem] = useState(null);
  const [failReason, setFailReason] = useState('');
  const [failSubmitting, setFailSubmitting] = useState(false);

  const loadWithdrawals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (statusFilter) params.status = statusFilter;
      const res = await apiAdminGetAllWithdrawals(params);
      setWithdrawals(res || []);
    } catch (err) {
      setError(err?.message || 'Failed to load withdrawal requests.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadWithdrawals();
  }, [loadWithdrawals]);

  const handleProcess = async (id) => {
    try {
      await apiAdminProcessWithdrawal(id);
      setSuccessMsg('Withdrawal moved to PROCESSING.');
      setTimeout(() => setSuccessMsg(''), 4000);
      loadWithdrawals();
    } catch (err) {
      alert(err?.message || 'Failed to mark as processing.');
    }
  };

  const handleCompleteSubmit = async (e) => {
    e.preventDefault();
    if (!bankTxnId.trim()) return;
    try {
      setCompleteSubmitting(true);
      await apiAdminCompleteWithdrawal(completeModalItem.id, {
        bank_transaction_id: bankTxnId.trim(),
      });
      setCompleteModalItem(null);
      setBankTxnId('');
      setSuccessMsg('Withdrawal marked COMPLETED and balance finalized.');
      setTimeout(() => setSuccessMsg(''), 4500);
      loadWithdrawals();
    } catch (err) {
      alert(err?.message || 'Failed to complete withdrawal.');
    } finally {
      setCompleteSubmitting(false);
    }
  };

  const handleFailSubmit = async (e) => {
    e.preventDefault();
    if (!failReason.trim()) return;
    try {
      setFailSubmitting(true);
      await apiAdminFailWithdrawal(failModalItem.id, failReason.trim());
      setFailModalItem(null);
      setFailReason('');
      setSuccessMsg('Withdrawal marked FAILED. Funds returned to technician available balance.');
      setTimeout(() => setSuccessMsg(''), 4500);
      loadWithdrawals();
    } catch (err) {
      alert(err?.message || 'Failed to mark as failed.');
    } finally {
      setFailSubmitting(false);
    }
  };

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Wallets', to: '/workforce/admin/wallet/dashboard' }, { label: 'Payouts' }]}>
      <div className="space-y-4 text-xs">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-zinc-200/90 p-5 rounded-md shadow-card">
          <div>
            <h1 className="text-base sm:text-lg font-bold text-zinc-950 flex items-center gap-2 tracking-tight">
              <ArrowDownCircle className="w-5 h-5 text-zinc-800" />
              <span>Technician Payout Requests</span>
            </h1>
            <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
              Review and process bank transfer payouts requested by technicians (minimum ₹5,000 threshold).
            </p>
          </div>
          <button
            onClick={loadWithdrawals}
            className="self-start sm:self-auto px-3.5 py-2 min-h-[38px] text-xs font-bold text-zinc-800 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 active:bg-zinc-100 flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-zinc-600" />
            <span>Refresh</span>
          </button>
        </div>

        {error && (
          <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-900 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-rose-700 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Filter Bar */}
        <div className="bg-white border border-zinc-200/90 rounded-md p-3.5 flex items-center gap-3 text-xs shadow-card">
          <Filter className="w-4 h-4 text-zinc-400" />
          <span className="font-bold text-zinc-700">Filter by Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 min-h-[38px] border border-zinc-300 rounded-lg bg-white text-zinc-800 text-xs outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
          >
            <option value="">All Requests</option>
            <option value="REQUESTED">Requested (Action Required)</option>
            <option value="PROCESSING">Processing</option>
            <option value="COMPLETED">Completed</option>
            <option value="FAILED">Failed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>

        {/* Withdrawals List */}
        <div className="bg-white border border-zinc-200/90 rounded-md shadow-card overflow-hidden text-xs">
          {loading ? (
            <div className="py-16 text-center text-zinc-500 text-xs flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-zinc-500" />
              <span>Loading payout requests...</span>
            </div>
          ) : withdrawals.length === 0 ? (
            <div className="py-16 text-center text-zinc-500 text-xs">
              No payout requests found matching your filter.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-zinc-50/60 text-zinc-500 uppercase text-[11px] font-bold border-b border-zinc-200">
                  <tr>
                    <th className="px-5 py-3.5">Request</th>
                    <th className="px-5 py-3.5">Technician</th>
                    <th className="px-5 py-3.5">Destination Bank Account</th>
                    <th className="px-5 py-3.5 text-right">Amount</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5 text-center">Disbursement Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 font-medium text-zinc-700">
                  {withdrawals.map((w) => {
                    return (
                      <tr key={w.id} className="hover:bg-zinc-50/80 transition-colors">
                        <td className="px-5 py-4 font-mono text-zinc-500 whitespace-nowrap">
                          #{w.id}
                          <div className="text-[10px] text-zinc-400 mt-0.5">
                            {new Date(w.requested_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <div className="font-bold text-zinc-950">
                            {w.payout_account_display?.account_holder_name || `Employee #${w.employee_id || w.employee}`}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          {w.payout_account_display ? (
                            <div>
                              <span className="font-bold text-zinc-900">{w.payout_account_display.bank_name}</span>
                              <div className="font-mono text-[11px] text-zinc-500 mt-0.5">
                                •••• •••• {w.payout_account_display.account_number_last4}
                              </div>
                            </div>
                          ) : (
                            <span className="text-zinc-400 italic">No account details</span>
                          )}
                        </td>
                        <td className="px-5 py-4 text-right font-mono font-bold text-sm text-zinc-950 whitespace-nowrap">
                          {fmt(w.amount)}
                        </td>
                        <td className="px-5 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${STATUS_COLORS[w.status] || 'bg-zinc-100 text-zinc-700'}`}>
                            {w.status}
                          </span>
                          {w.bank_transaction_id && (
                            <div className="text-[10px] font-mono text-zinc-500 mt-0.5">
                              UTR: {w.bank_transaction_id}
                            </div>
                          )}
                        </td>
                        <td className="px-5 py-4 text-center whitespace-nowrap">
                          <div className="flex items-center justify-center gap-1.5 flex-wrap">
                            {w.status === 'REQUESTED' && (
                              <button
                                onClick={() => handleProcess(w.id)}
                                className="px-3 py-1.5 min-h-[32px] bg-zinc-100 hover:bg-zinc-200 text-zinc-900 border border-zinc-300 font-bold rounded-lg text-xs transition-all shadow-xs cursor-pointer"
                              >
                                Start Processing
                              </button>
                            )}
                            {w.status === 'PROCESSING' && (
                              <>
                                <button
                                  onClick={() => {
                                    setCompleteModalItem(w);
                                    setBankTxnId('');
                                  }}
                                  className="px-3 py-1.5 min-h-[32px] bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white font-bold rounded-lg text-xs shadow-xs transition-all cursor-pointer"
                                >
                                  Mark Completed
                                </button>
                                <button
                                  onClick={() => {
                                    setFailModalItem(w);
                                    setFailReason('');
                                  }}
                                  className="px-3 py-1.5 min-h-[32px] bg-rose-50 hover:bg-rose-100 text-rose-900 border border-rose-300 font-bold rounded-lg text-xs transition-all shadow-xs cursor-pointer"
                                >
                                  Mark Failed
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Complete Modal */}
        {completeModalItem && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-4 text-xs">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  Confirm Payout Completion
                </h3>
                <button onClick={() => setCompleteModalItem(null)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="bg-slate-50 p-3 rounded-xl space-y-1">
                <div className="text-slate-500">Payout Amount:</div>
                <div className="text-lg font-bold font-mono text-slate-900">{fmt(completeModalItem.amount)}</div>
              </div>

              <form onSubmit={handleCompleteSubmit} className="space-y-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Bank Reference / UTR Number *</label>
                  <input
                    type="text"
                    value={bankTxnId}
                    onChange={(e) => setBankTxnId(e.target.value)}
                    placeholder="e.g. UTR1234567890"
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                  />
                </div>
                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setCompleteModalItem(null)}
                    className="px-4 py-2 border border-slate-300 rounded-lg font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={completeSubmitting}
                    className="px-5 py-2 bg-emerald-600 text-white font-bold rounded-lg hover:bg-emerald-700"
                  >
                    {completeSubmitting ? 'Saving...' : 'Confirm Completed'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Fail Modal */}
        {failModalItem && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-4 text-xs">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-rose-700 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  Mark Payout as Failed
                </h3>
                <button onClick={() => setFailModalItem(null)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <p className="text-slate-600">
                Marking this withdrawal failed will automatically reverse the debit and return{' '}
                <strong>{fmt(failModalItem.amount)}</strong> back to the technician's available wallet balance.
              </p>

              <form onSubmit={handleFailSubmit} className="space-y-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Failure Reason *</label>
                  <textarea
                    value={failReason}
                    onChange={(e) => setFailReason(e.target.value)}
                    placeholder="e.g. Invalid beneficiary IFSC code, bank rejected transfer"
                    required
                    rows={3}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>
                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setFailModalItem(null)}
                    className="px-4 py-2 border border-slate-300 rounded-lg font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={failSubmitting}
                    className="px-5 py-2 bg-rose-600 text-white font-bold rounded-lg hover:bg-rose-700"
                  >
                    {failSubmitting ? 'Reversing...' : 'Confirm Failure & Refund'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
