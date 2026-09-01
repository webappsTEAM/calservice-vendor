import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { AppShell } from '../../../components/common/AppShell.jsx';
import {
  apiGetPayoutAccounts,
  apiCreatePayoutAccount,
  apiDeletePayoutAccount,
} from '../../../api/walletService.js';
import {
  CreditCard,
  ArrowLeft,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Building2,
  PlusCircle,
  Trash2,
  ShieldCheck,
  X,
} from 'lucide-react';

export function EmployeePayoutAccountsPage() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Add Account Modal
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    account_holder_name: '',
    bank_name: '',
    account_number: '',
    ifsc_code: '',
    account_type: 'SAVINGS',
  });
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');

  const loadAccounts = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const res = await apiGetPayoutAccounts();
      setAccounts(res || []);
    } catch (err) {
      setError(err?.message || 'Failed to load bank accounts.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setModalError('');
    if (!form.account_holder_name.trim() || !form.account_number.trim()) {
      setModalError('Account holder name and account number are required.');
      return;
    }

    try {
      setSubmitting(true);
      await apiCreatePayoutAccount(form);
      setShowModal(false);
      setForm({
        account_holder_name: '',
        bank_name: '',
        account_number: '',
        ifsc_code: '',
        account_type: 'SAVINGS',
      });
      setSuccessMsg('Bank account added successfully. Administration will verify it shortly.');
      setTimeout(() => setSuccessMsg(''), 4500);
      loadAccounts();
    } catch (err) {
      setModalError(err?.message || 'Failed to add bank account.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to remove this bank account?')) return;
    try {
      await apiDeletePayoutAccount(id);
      setSuccessMsg('Bank account removed.');
      setTimeout(() => setSuccessMsg(''), 4000);
      loadAccounts();
    } catch (err) {
      setError(err?.message || 'Failed to remove bank account.');
    }
  };

  return (
    <AppShell
      breadcrumbs={[
        { label: 'Home', href: '/workforce/employee/dashboard' },
        { label: 'My Wallet', href: '/workforce/employee/wallet' },
        { label: 'Bank Accounts' },
      ]}
    >
      <div className="space-y-5 max-w-5xl mx-auto text-xs">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-md border border-zinc-200/90 shadow-card">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <Link
                to="/workforce/employee/wallet"
                className="text-xs font-bold text-zinc-600 hover:text-zinc-950 flex items-center gap-1 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Wallet</span>
              </Link>
            </div>
            <h1 className="text-base sm:text-lg font-bold text-zinc-950 flex items-center gap-2 tracking-tight">
              <CreditCard className="w-5 h-5 text-zinc-800" />
              <span>Payout Bank Accounts</span>
            </h1>
            <p className="text-xs text-zinc-500 mt-1">
              Manage your linked bank accounts for direct commission withdrawals.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadAccounts}
              className="px-3.5 py-2 min-h-[38px] text-xs font-bold text-zinc-800 bg-white border border-zinc-300 rounded-lg hover:bg-zinc-50 active:bg-zinc-100 flex items-center gap-1.5 transition-all shadow-xs cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 min-h-[38px] text-xs font-bold text-white bg-slate-800 rounded-lg hover:bg-slate-700 active:bg-slate-900 flex items-center gap-2 shadow-xs transition-all cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Add Bank Account</span>
            </button>
          </div>
        </div>

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

        {/* Security Masking Notice */}
        <div className="p-4 rounded-md border border-zinc-200/90 bg-zinc-50/80 text-xs text-zinc-600 flex items-start gap-3 shadow-card">
          <ShieldCheck className="w-5 h-5 text-zinc-800 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-zinc-950">Secure Account Masking</p>
            <p className="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">
              Full bank account numbers are submitted via encrypted transport and discarded immediately after extracting the last 4 digits.
            </p>
          </div>
        </div>

        {/* Accounts Grid */}
        <div className="space-y-3.5">
          {loading ? (
            <div className="py-14 text-center text-zinc-400 text-xs flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-zinc-800" />
              <span>Loading bank accounts...</span>
            </div>
          ) : accounts.length === 0 ? (
            <div className="rounded-md border border-zinc-200/90 bg-white p-12 text-center text-zinc-400 text-xs space-y-3 shadow-card">
              <Building2 className="w-8 h-8 text-zinc-300 mx-auto" />
              <div>
                <p className="font-bold text-zinc-900 text-sm">No Bank Accounts Linked</p>
                <p className="text-zinc-500 text-xs mt-1">Add a verified bank account to enable self-service payouts.</p>
              </div>
              <button
                onClick={() => setShowModal(true)}
                className="px-4 py-2 min-h-[38px] bg-slate-800 text-white font-bold rounded-lg text-xs hover:bg-slate-700 cursor-pointer shadow-xs transition-all"
              >
                Add Bank Account
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {accounts.map((acc) => {
                const isVerified = acc.verification_status === 'VERIFIED';
                return (
                  <div
                    key={acc.id}
                    className="p-5 rounded-md border border-zinc-200/90 bg-white shadow-card space-y-3 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-zinc-800" />
                        <span className="font-bold text-zinc-950 text-sm">{acc.bank_name || 'Bank Account'}</span>
                      </div>
                      <span
                        className={`text-[9px] font-bold px-2.5 py-0.5 rounded-full border ${
                          isVerified
                            ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
                            : 'bg-amber-50 text-amber-900 border-amber-200'
                        }`}
                      >
                        {acc.verification_status}
                      </span>
                    </div>

                    <div className="p-3 bg-zinc-50 border border-zinc-200/80 rounded-lg space-y-0.5 font-mono">
                      <div className="text-zinc-400 text-[10px] uppercase font-bold">Account Number</div>
                      <div className="font-bold text-zinc-950 text-xs tracking-wider">
                        •••• •••• •••• {acc.account_number_last4}
                      </div>
                    </div>

                    <div className="space-y-1 text-[11px] text-slate-500">
                      <div className="flex justify-between">
                        <span>Account Holder:</span>
                        <span className="font-semibold text-slate-800">{acc.account_holder_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>IFSC Code:</span>
                        <span className="font-mono text-slate-700">{acc.ifsc_code || '—'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Account Type:</span>
                        <span className="text-slate-700">{acc.account_type}</span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex justify-end">
                      <button
                        onClick={() => handleDelete(acc.id)}
                        className="text-rose-600 hover:text-rose-700 font-semibold text-[11px] flex items-center gap-1"
                      >
                        <Trash2 className="w-3 h-3" />
                        Remove
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Add Modal */}
        {showModal && (
          <div className="fixed inset-0 z-50 bg-zinc-950/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-md shadow-modal max-w-md w-full p-6 space-y-4 border border-zinc-200/90">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <h3 className="text-sm font-bold text-zinc-950 flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-zinc-800" />
                  <span>Add Bank Account</span>
                </h3>
                <button onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-zinc-700 p-1 cursor-pointer">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {modalError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs font-semibold">
                  {modalError}
                </div>
              )}

              <form onSubmit={handleCreateSubmit} className="space-y-3.5 text-xs">
                <div>
                  <label className="block font-bold text-zinc-700 mb-1">Account Holder Name *</label>
                  <input
                    type="text"
                    value={form.account_holder_name}
                    onChange={(e) => setForm({ ...form, account_holder_name: e.target.value })}
                    placeholder="As per bank passbook / statement"
                    required
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                  />
                </div>

                <div>
                  <label className="block font-bold text-zinc-700 mb-1">Bank Name</label>
                  <input
                    type="text"
                    value={form.bank_name}
                    onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
                    placeholder="e.g. State Bank of India, HDFC Bank"
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                  />
                </div>

                <div>
                  <label className="block font-bold text-zinc-700 mb-1">Account Number *</label>
                  <input
                    type="password"
                    value={form.account_number}
                    onChange={(e) => setForm({ ...form, account_number: e.target.value })}
                    placeholder="Full account number"
                    required
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 font-mono shadow-xs"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-zinc-700 mb-1">IFSC Code</label>
                    <input
                      type="text"
                      value={form.ifsc_code}
                      onChange={(e) => setForm({ ...form, ifsc_code: e.target.value.toUpperCase() })}
                      placeholder="e.g. SBIN0001234"
                      className="w-full px-3 py-2 border border-zinc-300 rounded-lg outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 font-mono shadow-xs"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-zinc-700 mb-1">Account Type</label>
                    <select
                      value={form.account_type}
                      onChange={(e) => setForm({ ...form, account_type: e.target.value })}
                      className="w-full px-3 py-2 border border-zinc-300 rounded-lg outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs bg-white"
                    >
                      <option value="SAVINGS">Savings</option>
                      <option value="CURRENT">Current</option>
                    </select>
                  </div>
                </div>

                <div className="pt-3 flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 min-h-[38px] border border-zinc-300 text-zinc-700 font-bold rounded-lg hover:bg-zinc-50 transition-all cursor-pointer shadow-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 min-h-[38px] bg-slate-800 text-white font-bold rounded-lg hover:bg-slate-700 active:bg-slate-900 disabled:opacity-50 flex items-center gap-2 transition-all cursor-pointer shadow-xs"
                  >
                    {submitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
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
