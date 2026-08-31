import React, { useState, useEffect } from 'react';
import { apiGetMyWallet, apiUpdateWalletPayoutDetails } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { Wallet, Landmark, ShieldCheck, ArrowUpCircle } from 'lucide-react';

// SEVO business plan Section 1/2: a provider business's shared "head
// wallet" -- every job any of this company's workers completes credits
// this single account. This page is the provider admin's self-service
// view of it: current balance, KYC tier, and payout destination
// (bank/UPI) management, backed by GET/PATCH /workforce/wallet/*.
export function AdminWalletPage() {
  const [wallet, setWallet] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);

  const [form, setForm] = useState({
    bank_account_name: '',
    bank_account_number: '',
    ifsc: '',
    upi_id: '',
  });
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  const load = async () => {
    try {
      setIsLoading(true);
      setError('');
      setNotFound(false);
      const res = await apiGetMyWallet();
      setWallet(res);
      setForm({
        bank_account_name: res.payout_bank_account_name || '',
        bank_account_number: res.payout_bank_account_number_masked || '',
        ifsc: res.payout_ifsc || '',
        upi_id: res.payout_upi_id || '',
      });
    } catch (err) {
      if (err.status === 404 || /404/.test(err.message || '')) {
        setNotFound(true);
      } else {
        setError(err.message || 'Failed to load wallet.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setSaveMessage('');
      setError('');
      const res = await apiUpdateWalletPayoutDetails(form);
      setWallet(res);
      setSaveMessage('Payout details saved.');
    } catch (err) {
      setError(err.message || 'Failed to save payout details.');
    } finally {
      setSaving(false);
    }
  };

  const money = (v) => `₹${Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Wallet' }]}>
        <LoadingState message="Loading wallet..." />
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Wallet' }]}>
      <div className="space-y-4 max-w-3xl mx-auto">
        {error && <ErrorState message={error} onDismiss={() => setError('')} />}

        {notFound ? (
          <div className="bg-white border border-slate-200 rounded p-6 text-center text-xs text-slate-500">
            No wallet has been provisioned for this account yet. This is created automatically
            when your business registers -- contact support if this persists.
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="bg-white border border-slate-200 rounded p-3.5 shadow-sm space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Balance</span>
                  <div className="p-1 rounded bg-slate-50 border border-slate-100 text-slate-600">
                    <Wallet className="w-3.5 h-3.5" />
                  </div>
                </div>
                <div className="text-xl font-bold text-slate-900 font-mono">{money(wallet?.balance)}</div>
                <p className="text-[10px] text-slate-500">Withdrawable now</p>
              </div>
              <div className="bg-white border border-slate-200 rounded p-3.5 shadow-sm space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">KYC Tier</span>
                  <div className="p-1 rounded bg-slate-50 border border-slate-100 text-slate-600">
                    <ShieldCheck className="w-3.5 h-3.5" />
                  </div>
                </div>
                <div className="text-xl font-bold text-slate-900">{(wallet?.kyc_tier || '').replace('TIER_', 'Tier ')}</div>
                <p className="text-[10px] text-slate-500">Add payout details to reach Tier 1</p>
              </div>
              <div className="bg-white border border-slate-200 rounded p-3.5 shadow-sm space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Daily Limit</span>
                  <div className="p-1 rounded bg-slate-50 border border-slate-100 text-slate-600">
                    <ArrowUpCircle className="w-3.5 h-3.5" />
                  </div>
                </div>
                <div className="text-xl font-bold text-slate-900 font-mono">
                  {wallet?.withdrawal_limit == null ? 'No cap' : money(wallet.withdrawal_limit)}
                </div>
                <p className="text-[10px] text-slate-500">Per withdrawal, by KYC tier</p>
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
              <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center gap-2">
                <Landmark className="w-4 h-4 text-blue-500" />
                <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Payout Destination</h2>
              </div>
              <form onSubmit={handleSave} className="p-4 space-y-3 text-xs">
                <p className="text-[11px] text-slate-500">
                  Provide either a UPI ID, or your full bank account details. This is where withdrawals
                  are sent via RazorpayX.
                </p>
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">UPI ID</label>
                  <input
                    type="text"
                    placeholder="business@upi"
                    value={form.upi_id}
                    onChange={(e) => setForm({ ...form, upi_id: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wider text-center py-1">or bank account</div>
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="col-span-2">
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">Account Holder Name</label>
                    <input
                      type="text"
                      value={form.bank_account_name}
                      onChange={(e) => setForm({ ...form, bank_account_name: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">Account Number</label>
                    <input
                      type="text"
                      value={form.bank_account_number}
                      onChange={(e) => setForm({ ...form, bank_account_number: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">IFSC Code</label>
                    <input
                      type="text"
                      value={form.ifsc}
                      onChange={(e) => setForm({ ...form, ifsc: e.target.value.toUpperCase() })}
                      className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                {saveMessage && <p className="text-[11px] text-emerald-600 font-semibold">{saveMessage}</p>}
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save Payout Details'}
                </button>
              </form>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
