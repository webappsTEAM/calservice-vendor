import React, { useState, useEffect } from 'react';
import {
  apiGetMyWallet,
  apiUpdateWalletPayoutDetails,
  apiGetWalletStatement,
  apiExportWalletLedgerCsv,
  apiWithdrawFromWallet,
  apiUpdateAutoWithdrawalSettings,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { Wallet, Landmark, ShieldCheck, ArrowUpCircle, FileText, Download, Bell, RefreshCw } from 'lucide-react';

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

  const now = new Date();
  const [statementYear, setStatementYear] = useState(now.getFullYear());
  const [statementMonth, setStatementMonth] = useState(now.getMonth() + 1);
  const [statement, setStatement] = useState(null);
  const [statementLoading, setStatementLoading] = useState(false);
  const [statementError, setStatementError] = useState('');
  const [exporting, setExporting] = useState(false);

  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawing, setWithdrawing] = useState(false);
  const [withdrawMessage, setWithdrawMessage] = useState('');
  const [withdrawError, setWithdrawError] = useState('');

  const [autoForm, setAutoForm] = useState({
    auto_withdrawal_enabled: false,
    auto_withdrawal_frequency: '',
    auto_withdrawal_day_of_week: '',
    minimum_balance_alert_threshold: '',
  });
  const [autoSaving, setAutoSaving] = useState(false);
  const [autoMessage, setAutoMessage] = useState('');
  const [autoError, setAutoError] = useState('');

  const applyWalletToAutoForm = (res) => {
    setAutoForm({
      auto_withdrawal_enabled: !!res.auto_withdrawal_enabled,
      auto_withdrawal_frequency: res.auto_withdrawal_frequency || '',
      auto_withdrawal_day_of_week:
        res.auto_withdrawal_day_of_week === null || res.auto_withdrawal_day_of_week === undefined
          ? ''
          : String(res.auto_withdrawal_day_of_week),
      minimum_balance_alert_threshold:
        res.minimum_balance_alert_threshold === null || res.minimum_balance_alert_threshold === undefined
          ? ''
          : String(res.minimum_balance_alert_threshold),
    });
  };

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
      applyWalletToAutoForm(res);
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

  // SEVO Section 1: on-demand self-service withdrawal -- shares the same
  // validation and RazorpayX execution path (services.withdrawals /
  // services.payouts) as the scheduled auto-payout below, so a manual
  // withdrawal behaves identically to a scheduled one.
  const handleWithdraw = async (e) => {
    e.preventDefault();
    try {
      setWithdrawing(true);
      setWithdrawMessage('');
      setWithdrawError('');
      const res = await apiWithdrawFromWallet(withdrawAmount);
      setWithdrawMessage(
        res.status === 'AWAITING_RAZORPAYX_ACTIVATION'
          ? `Withdrawal of ${money(res.amount)} queued -- payouts aren't live on this environment yet.`
          : `Withdrawal of ${money(res.amount)} requested (${res.status}).`
      );
      setWithdrawAmount('');
      await load();
    } catch (err) {
      setWithdrawError(err.message || 'Failed to request withdrawal.');
    } finally {
      setWithdrawing(false);
    }
  };

  // SEVO Section 1 (head-wallet specific features): the standing
  // daily/weekly auto-payout rule ("timed to their own wage-payment
  // day") and the minimum-balance alert floor ("alert me if my
  // withdrawable balance drops below X"), saved together via one PATCH.
  const handleSaveAutoSettings = async (e) => {
    e.preventDefault();
    try {
      setAutoSaving(true);
      setAutoMessage('');
      setAutoError('');
      const payload = {
        auto_withdrawal_enabled: autoForm.auto_withdrawal_enabled,
        auto_withdrawal_frequency: autoForm.auto_withdrawal_frequency,
        auto_withdrawal_day_of_week:
          autoForm.auto_withdrawal_frequency === 'WEEKLY' && autoForm.auto_withdrawal_day_of_week !== ''
            ? Number(autoForm.auto_withdrawal_day_of_week)
            : null,
        minimum_balance_alert_threshold:
          autoForm.minimum_balance_alert_threshold === '' ? null : autoForm.minimum_balance_alert_threshold,
      };
      const res = await apiUpdateAutoWithdrawalSettings(payload);
      setWallet(res);
      applyWalletToAutoForm(res);
      setAutoMessage('Auto-withdrawal and alert settings saved.');
    } catch (err) {
      setAutoError(err.message || 'Failed to save settings.');
    } finally {
      setAutoSaving(false);
    }
  };

  const money = (v) => `₹${Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // SEVO Section 6: monthly/annual earnings statement -- gross job value,
  // commission deducted, net credited. No tax is withheld or computed
  // here; this is the figure a wallet owner hands to their own accountant.
  const loadStatement = async (year, month) => {
    try {
      setStatementLoading(true);
      setStatementError('');
      const res = await apiGetWalletStatement(year, month);
      setStatement(res);
    } catch (err) {
      setStatementError(err.message || 'Failed to load statement.');
    } finally {
      setStatementLoading(false);
    }
  };

  useEffect(() => {
    if (!notFound) {
      loadStatement(statementYear, statementMonth);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notFound]);

  // SEVO Section 1: "exportable as a CSV/PDF wage register" -- CSV is
  // built server-side (services.tax_statements.export_ledger_csv) and
  // downloaded here via a Blob, since the browser sandbox this page may
  // render in blocks plain <a download> links.
  const handleExportCsv = async () => {
    try {
      setExporting(true);
      setStatementError('');
      const csvText = await apiExportWalletLedgerCsv();
      const blob = new Blob([csvText], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `wallet-${wallet?.id || 'ledger'}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setStatementError(err.message || 'Failed to export ledger CSV.');
    } finally {
      setExporting(false);
    }
  };

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

            <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
              <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center gap-2">
                <ArrowUpCircle className="w-4 h-4 text-emerald-500" />
                <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Withdraw Now</h2>
              </div>
              <form onSubmit={handleWithdraw} className="p-4 space-y-3 text-xs">
                {withdrawError && <ErrorState message={withdrawError} onDismiss={() => setWithdrawError('')} />}
                <p className="text-[11px] text-slate-500">
                  Send part or all of your withdrawable balance to your payout destination now, via RazorpayX.
                </p>
                <div className="flex flex-wrap items-end gap-2.5">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">Amount</label>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      placeholder="0.00"
                      value={withdrawAmount}
                      onChange={(e) => setWithdrawAmount(e.target.value)}
                      className="w-40 px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => setWithdrawAmount(String(wallet?.balance ?? ''))}
                    className="px-3 py-2 border border-slate-300 rounded text-xs font-semibold text-slate-600 hover:bg-slate-50"
                  >
                    Max
                  </button>
                  <button
                    type="submit"
                    disabled={withdrawing || !withdrawAmount}
                    className="px-4 py-2 bg-emerald-600 text-white rounded text-xs font-semibold hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {withdrawing ? 'Requesting...' : 'Withdraw'}
                  </button>
                </div>
                {withdrawMessage && <p className="text-[11px] text-emerald-600 font-semibold">{withdrawMessage}</p>}
              </form>
            </div>

            <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
              <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-blue-500" />
                <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Scheduled Withdrawals &amp; Alerts</h2>
              </div>
              <form onSubmit={handleSaveAutoSettings} className="p-4 space-y-3 text-xs">
                {autoError && <ErrorState message={autoError} onDismiss={() => setAutoError('')} />}
                <p className="text-[11px] text-slate-500">
                  Set a standing daily/weekly auto-payout timed to your own wage-payment day, and a
                  minimum-balance floor so you're alerted before you get caught short on a payday.
                </p>

                <label className="flex items-center gap-2 py-1">
                  <input
                    type="checkbox"
                    checked={autoForm.auto_withdrawal_enabled}
                    onChange={(e) => setAutoForm({ ...autoForm, auto_withdrawal_enabled: e.target.checked })}
                    className="w-3.5 h-3.5"
                  />
                  <span className="font-semibold text-slate-700">Enable standing auto-payout</span>
                </label>

                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">Frequency</label>
                    <select
                      value={autoForm.auto_withdrawal_frequency}
                      onChange={(e) => setAutoForm({ ...autoForm, auto_withdrawal_frequency: e.target.value })}
                      className="w-full px-2.5 py-2 border border-slate-300 rounded text-xs"
                    >
                      <option value="">Not set</option>
                      <option value="DAILY">Daily</option>
                      <option value="WEEKLY">Weekly</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">Day of Week (weekly only)</label>
                    <select
                      value={autoForm.auto_withdrawal_day_of_week}
                      onChange={(e) => setAutoForm({ ...autoForm, auto_withdrawal_day_of_week: e.target.value })}
                      disabled={autoForm.auto_withdrawal_frequency !== 'WEEKLY'}
                      className="w-full px-2.5 py-2 border border-slate-300 rounded text-xs disabled:opacity-50"
                    >
                      <option value="">--</option>
                      {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((d, i) => (
                        <option key={d} value={i}>{d}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 pt-1">
                  <Bell className="w-3.5 h-3.5 text-amber-500" />
                  <label className="text-[11px] font-bold text-slate-700">Minimum Balance Alert Threshold</label>
                </div>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="e.g. 5000.00"
                  value={autoForm.minimum_balance_alert_threshold}
                  onChange={(e) => setAutoForm({ ...autoForm, minimum_balance_alert_threshold: e.target.value })}
                  className="w-full sm:w-56 px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                />

                {autoMessage && <p className="text-[11px] text-emerald-600 font-semibold">{autoMessage}</p>}
                <div>
                  <button
                    type="submit"
                    disabled={autoSaving}
                    className="px-4 py-2 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700 disabled:opacity-50"
                  >
                    {autoSaving ? 'Saving...' : 'Save Settings'}
                  </button>
                </div>
              </form>
            </div>

            <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
              <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-500" />
                <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Earnings Statement</h2>
              </div>
              <div className="p-4 space-y-3 text-xs">
                {statementError && <ErrorState message={statementError} onDismiss={() => setStatementError('')} />}
                <div className="flex flex-wrap items-end gap-2.5">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">Month</label>
                    <select
                      value={statementMonth}
                      onChange={(e) => {
                        const m = Number(e.target.value);
                        setStatementMonth(m);
                        loadStatement(statementYear, m);
                      }}
                      className="px-2 py-1.5 border border-slate-300 rounded text-xs"
                    >
                      {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                        <option key={m} value={m}>
                          {new Date(2000, m - 1, 1).toLocaleString('en-US', { month: 'long' })}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">Year</label>
                    <select
                      value={statementYear}
                      onChange={(e) => {
                        const y = Number(e.target.value);
                        setStatementYear(y);
                        loadStatement(y, statementMonth);
                      }}
                      className="px-2 py-1.5 border border-slate-300 rounded text-xs"
                    >
                      {Array.from({ length: 5 }, (_, i) => now.getFullYear() - i).map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={handleExportCsv}
                    disabled={exporting}
                    className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 text-white rounded text-xs font-semibold hover:bg-slate-900 disabled:opacity-50"
                  >
                    <Download className="w-3.5 h-3.5" />
                    {exporting ? 'Exporting...' : 'Download Wage Register (CSV)'}
                  </button>
                </div>

                {statementLoading ? (
                  <p className="text-slate-500">Loading statement...</p>
                ) : statement ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1">
                    <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wide">Jobs</p>
                      <p className="font-bold font-mono text-slate-900">{statement.jobs_count}</p>
                    </div>
                    <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wide">Gross Job Value</p>
                      <p className="font-bold font-mono text-slate-900">{money(statement.gross_job_value)}</p>
                    </div>
                    <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wide">Commission Deducted</p>
                      <p className="font-bold font-mono text-slate-900">{money(statement.commission_deducted)}</p>
                    </div>
                    <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded col-span-2 sm:col-span-1">
                      <p className="text-[10px] text-emerald-700 uppercase tracking-wide">Net Credited</p>
                      <p className="font-bold font-mono text-emerald-800">{money(statement.net_credited)}</p>
                    </div>
                    <div className="p-2.5 bg-slate-50 border border-slate-200 rounded col-span-2 sm:col-span-2">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wide">{statement.income_category}</p>
                      <p className="text-slate-600">{statement.period_label}</p>
                    </div>
                  </div>
                ) : null}
                <p className="text-[10px] text-slate-400 pt-1">
                  This statement shows gross job value, commission deducted and net credited for the
                  selected period. It does not compute or withhold any tax -- share it with your own
                  accountant for that.
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
