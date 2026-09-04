import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { AppShell } from '../../../components/common/AppShell.jsx';
import { LoadingState } from '../../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../../components/enterprise/ErrorState.jsx';
import {
  apiGetWalletSummary,
  apiGetWalletTransactions,
  apiGetWalletWithdrawals,
  apiGetPayoutAccounts,
  apiRequestWithdrawal,
  apiCreatePayoutAccount,
  apiCancelWithdrawal,
} from '../../../api/walletService.js';
import { useAuth } from '../../../context/AuthProvider.jsx';
import {
  Wallet,
  ArrowDownCircle,
  Clock,
  CheckCircle2,
  AlertCircle,
  PlusCircle,
  Building2,
  TrendingUp,
  CreditCard,
  RefreshCw,
  X,
  ShieldCheck,
  ReceiptText,
  AlertTriangle,
  ChevronRight,
} from 'lucide-react';

function fmt(value) {
  const num = parseFloat(value || 0);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(num);
}

function StatCard({ icon: Icon, label, value, sub, loading }) {
  return (
    <div className="p-4 sm:p-5 rounded-md border border-zinc-200/90 bg-white shadow-card flex items-start gap-3.5">
      <div className="p-2.5 rounded-lg border border-zinc-200 bg-zinc-100 text-zinc-900 shadow-2xs">
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">{label}</p>
        {loading ? (
          <div className="h-6 w-28 bg-zinc-200 animate-pulse rounded-md mt-1" />
        ) : (
          <p className="text-xl font-extrabold text-zinc-950 mt-0.5 truncate font-mono tracking-tight">{value}</p>
        )}
        {sub && !loading && <p className="text-[11px] text-zinc-500 font-medium mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export function EmployeeWalletDashboardPage() {
  const { user, employee, registrationStatus } = useAuth();

  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [withdrawals, setWithdrawals] = useState([]);
  const [payoutAccounts, setPayoutAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modals
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [withdrawSubmitting, setWithdrawSubmitting] = useState(false);
  const [withdrawError, setWithdrawError] = useState('');

  const [showAccountModal, setShowAccountModal] = useState(false);
  const [accountForm, setAccountForm] = useState({
    account_holder_name: '',
    bank_name: '',
    account_number: '',
    ifsc_code: '',
    account_type: 'SAVINGS',
  });
  const [accountSubmitting, setAccountSubmitting] = useState(false);
  const [accountError, setAccountError] = useState('');

  const isKycApproved = registrationStatus === 'approved';
  const verifiedAccounts = payoutAccounts.filter((a) => a.verification_status === 'VERIFIED');
  const availableNum = parseFloat(summary?.available_balance || '0');
  const canWithdraw = isKycApproved && verifiedAccounts.length > 0 && availableNum >= 5000;

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const [sumRes, txnRes, wRes, accRes] = await Promise.all([
        apiGetWalletSummary().catch(() => null),
        apiGetWalletTransactions({ page_size: 5 }).catch(() => ({ results: [] })),
        apiGetWalletWithdrawals().catch(() => []),
        apiGetPayoutAccounts().catch(() => []),
      ]);
      setSummary(sumRes);
      setTransactions(txnRes?.results || txnRes || []);
      setWithdrawals(wRes || []);
      setPayoutAccounts(accRes || []);
    } catch (err) {
      setError(err?.message || 'Failed to load wallet data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleWithdrawSubmit = async (e) => {
    e.preventDefault();
    setWithdrawError('');
    const amt = parseFloat(withdrawAmount);
    if (!amt || amt < 5000) {
      setWithdrawError('Minimum withdrawal amount is ₹5,000.');
      return;
    }
    if (amt > availableNum) {
      setWithdrawError(`Requested amount ₹${amt.toLocaleString('en-IN')} exceeds available balance ₹${availableNum.toLocaleString('en-IN')}.`);
      return;
    }

    try {
      setWithdrawSubmitting(true);
      await apiRequestWithdrawal({
        amount: withdrawAmount,
        payout_account_id: selectedAccountId ? parseInt(selectedAccountId, 10) : undefined,
      });
      setShowWithdrawModal(false);
      setWithdrawAmount('');
      setSuccessMsg('Withdrawal request submitted successfully! Funds will be disbursed to your bank.');
      setTimeout(() => setSuccessMsg(''), 4500);
      loadData();
    } catch (err) {
      setWithdrawError(err?.message || 'Withdrawal failed.');
    } finally {
      setWithdrawSubmitting(false);
    }
  };

  const handleCreateAccountSubmit = async (e) => {
    e.preventDefault();
    setAccountError('');
    if (!accountForm.account_holder_name.trim() || !accountForm.account_number.trim()) {
      setAccountError('Account holder name and account number are required.');
      return;
    }
    try {
      setAccountSubmitting(true);
      await apiCreatePayoutAccount(accountForm);
      setShowAccountModal(false);
      setAccountForm({
        account_holder_name: '',
        bank_name: '',
        account_number: '',
        ifsc_code: '',
        account_type: 'SAVINGS',
      });
      setSuccessMsg('Bank account added! Administration will verify it shortly.');
      setTimeout(() => setSuccessMsg(''), 4500);
      loadData();
    } catch (err) {
      setAccountError(err?.message || 'Failed to add bank account.');
    } finally {
      setAccountSubmitting(false);
    }
  };

  const handleCancelWithdrawal = async (id) => {
    if (!window.confirm('Are you sure you want to cancel this withdrawal request? The funds will return to your available balance.')) return;
    try {
      await apiCancelWithdrawal(id);
      setSuccessMsg('Withdrawal request cancelled.');
      setTimeout(() => setSuccessMsg(''), 4000);
      loadData();
    } catch (err) {
      setError(err?.message || 'Failed to cancel withdrawal.');
    }
  };

  return (
    <AppShell breadcrumbs={[{ label: 'Home', href: '/workforce/employee/dashboard' }, { label: 'My Wallet & Earnings' }]}>
      <div className="space-y-5 max-w-7xl mx-auto text-xs">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-md border border-zinc-200/90 shadow-card">
          <div>
            <h1 className="text-base sm:text-lg font-bold text-zinc-950 flex items-center gap-2 tracking-tight">
              <Wallet className="w-5 h-5 text-zinc-800" />
              <span>Technician Earnings & Wallet</span>
            </h1>
            <p className="text-xs text-zinc-500 mt-1">
              Authoritative 60% job commission earnings, T+7 settlement releases, and bank payouts.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadData}
              className="px-3.5 py-2 min-h-[38px] text-xs font-bold text-zinc-800 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 active:bg-zinc-100 flex items-center gap-1.5 transition-all shadow-xs cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => setShowWithdrawModal(true)}
              disabled={!canWithdraw}
              className={`px-4 py-2 min-h-[38px] text-xs font-bold rounded-lg flex items-center gap-2 shadow-xs transition-all cursor-pointer ${
                canWithdraw
                  ? 'bg-slate-800 text-white hover:bg-slate-700 active:bg-slate-900'
                  : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
              }`}
            >
              <ArrowDownCircle className="w-4 h-4" />
              <span>Withdraw Funds</span>
            </button>
          </div>
        </div>

        {/* Notifications */}
        {error && (
          <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-900 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-700 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-900 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* KYC / Eligibility Notice */}
        {!isKycApproved && (
          <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 flex items-start gap-2.5 text-xs">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-amber-950">KYC Verification Required for Payouts</p>
              <p className="text-amber-800 mt-0.5">
                Your onboarding status is <strong>{registrationStatus || 'Under Review'}</strong>.
                Self-service payouts unlock once administration approves your mandatory verification documents.
              </p>
            </div>
          </div>
        )}

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          <StatCard
            icon={CheckCircle2}
            label="Available Balance"
            value={fmt(summary?.available_balance)}
            sub="Ready for withdrawal (min ₹5,000)"
            color="green"
            loading={loading}
          />
          <StatCard
            icon={Clock}
            label="Pending Settlement"
            value={fmt(summary?.pending_balance)}
            sub={summary?.next_settlement_date
              ? `Next release on ${new Date(summary.next_settlement_date).toLocaleDateString('en-IN')}`
              : 'T+7 settlement hold'}
            color="amber"
            loading={loading}
          />
          <StatCard
            icon={TrendingUp}
            label="Lifetime Commission"
            value={fmt(summary?.lifetime_earnings)}
            sub="Cumulative 60% earnings"
            color="blue"
            loading={loading}
          />
          <StatCard
            icon={ArrowDownCircle}
            label="Total Withdrawn"
            value={fmt(summary?.total_withdrawn)}
            sub="Disbursed to bank accounts"
            color="slate"
            loading={loading}
          />
        </div>

        {/* Two-Column Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left Column (2 spans): Recent Activity & Withdrawals */}
          <div className="lg:col-span-2 space-y-5">
            {/* Recent Withdrawals */}
            {withdrawals.length > 0 && (
              <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
                  <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-1.5">
                    <ArrowDownCircle className="w-4 h-4 text-zinc-800" />
                    <span>Recent Withdrawal Requests</span>
                  </h2>
                  <Link
                    to="/workforce/employee/wallet/withdrawals"
                    className="text-xs font-bold text-zinc-700 hover:text-zinc-950 hover:underline flex items-center gap-1"
                  >
                    <span>View All ({withdrawals.length})</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                <div className="space-y-2">
                  {withdrawals.slice(0, 3).map((w) => {
                    const statusBadges = {
                      REQUESTED: 'bg-amber-50 text-amber-900 border-amber-200',
                      PROCESSING: 'bg-zinc-100 text-zinc-900 border-zinc-200',
                      COMPLETED: 'bg-emerald-50 text-emerald-900 border-emerald-200',
                      FAILED: 'bg-rose-50 text-rose-900 border-rose-200',
                      CANCELLED: 'bg-zinc-100 text-zinc-600 border-zinc-200',
                    };
                    return (
                      <div
                        key={w.id}
                        className="p-3.5 rounded-lg border border-zinc-200 bg-zinc-50/50 flex items-center justify-between gap-3 text-xs"
                      >
                        <div>
                          <div className="font-bold text-zinc-950 font-mono text-sm">
                            {fmt(w.amount)}
                          </div>
                          <p className="text-[11px] text-zinc-500 mt-0.5">
                            Requested on {new Date(w.requested_at).toLocaleDateString('en-IN')}
                            {w.payout_account_display && ` • ${w.payout_account_display.bank_name} (****${w.payout_account_display.account_number_last4})`}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${statusBadges[w.status] || 'bg-zinc-100 text-zinc-700'}`}>
                            {w.status}
                          </span>
                          {w.status === 'REQUESTED' && (
                            <button
                              onClick={() => handleCancelWithdrawal(w.id)}
                              className="text-[11px] text-rose-600 hover:text-rose-800 hover:underline font-bold"
                            >
                              Cancel
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Financial Ledger Activity */}
            <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
                <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-1.5">
                  <ReceiptText className="w-4 h-4 text-zinc-800" />
                  <span>Recent Ledger Entries</span>
                </h2>
                <Link
                  to="/workforce/employee/wallet/transactions"
                  className="text-xs font-bold text-zinc-700 hover:text-zinc-950 hover:underline flex items-center gap-1"
                >
                  <span>Full Ledger</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {transactions.length === 0 ? (
                <div className="py-8 text-center text-zinc-400 text-xs">
                  No transactions recorded yet. Complete customer jobs to earn commission.
                </div>
              ) : (
                <div className="divide-y divide-zinc-100">
                  {transactions.map((t) => {
                    const isCredit = t.direction === 'CREDIT';
                    return (
                      <div key={t.id} className="py-3 flex items-center justify-between gap-3 text-xs">
                        <div className="space-y-0.5">
                          <p className="font-bold text-zinc-900">{t.description || t.transaction_type}</p>
                          <p className="text-[10px] text-zinc-500">
                            {new Date(t.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                            {t.status === 'PENDING_SETTLEMENT' && (
                              <span className="ml-2 font-bold text-amber-900 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                                T+7 Pending
                              </span>
                            )}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className={`font-mono font-bold text-xs ${isCredit ? 'text-emerald-600' : 'text-zinc-950'}`}>
                            {isCredit ? '+' : '-'}{fmt(t.amount)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right Column (1 span): Bank Accounts & Guidelines */}
          <div className="space-y-5">
            {/* Linked Bank Accounts */}
            <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
                <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-1.5">
                  <CreditCard className="w-4 h-4 text-zinc-800" />
                  <span>Bank Accounts</span>
                </h2>
                <button
                  onClick={() => setShowAccountModal(true)}
                  className="text-xs font-bold text-zinc-800 hover:text-zinc-950 flex items-center gap-1 cursor-pointer"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Add</span>
                </button>
              </div>

              {payoutAccounts.length === 0 ? (
                <div className="p-6 text-center border border-dashed border-zinc-300 rounded-lg space-y-3 text-xs text-zinc-500">
                  <Building2 className="w-7 h-7 text-zinc-400 mx-auto" />
                  <p className="font-bold text-zinc-800">No bank accounts linked</p>
                  <button
                    onClick={() => setShowAccountModal(true)}
                    className="px-3.5 py-2 min-h-[36px] bg-slate-800 text-white font-bold rounded-lg text-xs hover:bg-slate-700 shadow-xs cursor-pointer"
                  >
                    Add Bank Account
                  </button>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {payoutAccounts.map((acc) => (
                    <div
                      key={acc.id}
                      className="p-3 rounded-md border border-slate-200 bg-slate-50/50 space-y-1.5 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">{acc.bank_name || 'Bank Account'}</span>
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${
                            acc.verification_status === 'VERIFIED'
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : 'bg-amber-50 text-amber-800 border-amber-200'
                          }`}
                        >
                          {acc.verification_status}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-700 font-mono">
                        •••• •••• •••• {acc.account_number_last4}
                      </div>
                      <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100">
                        <span>{acc.account_holder_name}</span>
                        <span>{acc.ifsc_code}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Financial Model Explainer */}
            <div className="enterprise-card p-4 sm:p-5 rounded-lg border border-slate-200 bg-slate-50 text-xs text-slate-600 space-y-2">
              <h3 className="font-bold text-slate-900 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                Commission & Payout Policy
              </h3>
              <ul className="space-y-1.5 list-disc pl-4 text-[11px] text-slate-600">
                <li>Technicians receive <strong>60% of gross payment</strong> on completed jobs.</li>
                <li>Company retains <strong>40%</strong> covering platform & GST obligations.</li>
                <li>Settlements move from Pending to Available in <strong>7 days (T+7)</strong>.</li>
                <li>Minimum payout threshold: <strong>₹5,000 INR</strong>.</li>
              </ul>
            </div>
          </div>
        </div>

        {/* ── Withdraw Modal ─────────────────────────────────────────────────── */}
        {showWithdrawModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <ArrowDownCircle className="w-4 h-4 text-blue-600" />
                  Request Direct Payout
                </h3>
                <button
                  onClick={() => setShowWithdrawModal(false)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {withdrawError && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 rounded text-xs">
                  {withdrawError}
                </div>
              )}

              <form onSubmit={handleWithdrawSubmit} className="space-y-3 text-xs">
                <div className="bg-slate-50 p-2.5 rounded border border-slate-200 flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Available Balance:</span>
                  <span className="font-bold text-sm text-slate-900 font-mono">
                    {fmt(availableNum)}
                  </span>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Withdrawal Amount (₹ INR) *
                  </label>
                  <input
                    type="number"
                    min="5000"
                    step="1"
                    max={availableNum}
                    value={withdrawAmount}
                    onChange={(e) => setWithdrawAmount(e.target.value)}
                    placeholder="Min. 5000"
                    required
                    className="w-full px-3 py-1.5 border border-slate-300 rounded text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                  <p className="text-[10px] text-slate-400 mt-0.5">Minimum payout is ₹5,000.</p>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Destination Bank Account *
                  </label>
                  <select
                    value={selectedAccountId}
                    onChange={(e) => setSelectedAccountId(e.target.value)}
                    className="w-full px-3 py-1.5 border border-slate-300 rounded text-xs focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {verifiedAccounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.bank_name} (****{acc.account_number_last4}) — {acc.account_holder_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="pt-3 flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowWithdrawModal(false)}
                    className="px-4 py-2 min-h-[38px] border border-zinc-300 text-zinc-700 font-bold rounded-lg hover:bg-zinc-50 transition-all cursor-pointer shadow-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={withdrawSubmitting}
                    className="px-4 py-2 min-h-[38px] bg-slate-800 text-white font-bold rounded-lg hover:bg-slate-700 active:bg-slate-900 disabled:opacity-50 flex items-center gap-2 transition-all cursor-pointer shadow-xs"
                  >
                    {withdrawSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>Confirm Withdrawal</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── Add Bank Account Modal ─────────────────────────────────────────── */}
        {showAccountModal && (
          <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-md border border-slate-200/90 shadow-card max-w-md w-full p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-950 flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-slate-800" />
                  <span>Link Bank Account</span>
                </h3>
                <button
                  onClick={() => setShowAccountModal(false)}
                  className="text-slate-400 hover:text-slate-700 p-1 rounded-lg transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {accountError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-900 rounded-lg text-xs font-semibold">
                  {accountError}
                </div>
              )}

              <form onSubmit={handleCreateAccountSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Account Holder Name *</label>
                  <input
                    type="text"
                    value={accountForm.account_holder_name}
                    onChange={(e) => setAccountForm({ ...accountForm, account_holder_name: e.target.value })}
                    placeholder="As per bank passbook / statement"
                    required
                    className="w-full px-3 py-2 min-h-[38px] border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-slate-800/10 focus:border-slate-700 shadow-xs text-slate-900"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Bank Name</label>
                  <input
                    type="text"
                    value={accountForm.bank_name}
                    onChange={(e) => setAccountForm({ ...accountForm, bank_name: e.target.value })}
                    placeholder="e.g. State Bank of India, HDFC Bank"
                    className="w-full px-3 py-2 min-h-[38px] border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-slate-800/10 focus:border-slate-700 shadow-xs text-slate-900"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Account Number *</label>
                  <input
                    type="password"
                    value={accountForm.account_number}
                    onChange={(e) => setAccountForm({ ...accountForm, account_number: e.target.value })}
                    placeholder="Full account number"
                    required
                    className="w-full px-3 py-2 min-h-[38px] border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-slate-800/10 focus:border-slate-700 shadow-xs text-slate-900 font-mono"
                  />
                  <p className="text-[10px] text-slate-400 mt-1">
                    Securely masked; only last 4 digits are retained for display.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">IFSC Code</label>
                    <input
                      type="text"
                      value={accountForm.ifsc_code}
                      onChange={(e) => setAccountForm({ ...accountForm, ifsc_code: e.target.value.toUpperCase() })}
                      placeholder="e.g. SBIN0001234"
                      className="w-full px-3 py-2 min-h-[38px] border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-slate-800/10 focus:border-slate-700 shadow-xs text-slate-900 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Account Type</label>
                    <select
                      value={accountForm.account_type}
                      onChange={(e) => setAccountForm({ ...accountForm, account_type: e.target.value })}
                      className="w-full px-3 py-2 min-h-[38px] border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-slate-800/10 focus:border-slate-700 shadow-xs text-slate-900 bg-white"
                    >
                      <option value="SAVINGS">Savings</option>
                      <option value="CURRENT">Current</option>
                    </select>
                  </div>
                </div>

                <div className="pt-3 flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowAccountModal(false)}
                    className="px-4 py-2 min-h-[38px] border border-slate-300 text-slate-700 font-bold rounded-lg hover:bg-slate-50 transition-all cursor-pointer shadow-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={accountSubmitting}
                    className="px-4 py-2 min-h-[38px] bg-slate-800 text-white font-bold rounded-lg hover:bg-slate-700 active:bg-slate-900 disabled:opacity-50 flex items-center gap-2 transition-all cursor-pointer shadow-xs"
                  >
                    {accountSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>Save Account</span>
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
