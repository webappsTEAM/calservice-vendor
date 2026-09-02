import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { AppShell } from '../../../components/common/AppShell.jsx';
import {
  apiAdminGetAllWallets,
  apiAdminGetAllWithdrawals,
  apiAdminFreezeWallet,
} from '../../../api/walletService.js';
import {
  Wallet,
  Users,
  Clock,
  TrendingUp,
  ArrowDownCircle,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Search,
  Building2,
  Lock,
  Unlock,
} from 'lucide-react';

function fmt(value) {
  const num = parseFloat(value || 0);
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2 }).format(num);
}

export function WalletDashboardPage() {
  const [wallets, setWallets] = useState([]);
  const [withdrawals, setWithdrawals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [walletsRes, wdRes] = await Promise.all([
        apiAdminGetAllWallets().catch(() => []),
        apiAdminGetAllWithdrawals().catch(() => []),
      ]);
      setWallets(walletsRes || []);
      setWithdrawals(wdRes || []);
    } catch (err) {
      setError(err?.message || 'Failed to load technician wallet data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleToggleFreeze = async (wallet) => {
    const isCurrentlyActive = wallet.status === 'ACTIVE';
    const nextStatus = isCurrentlyActive ? 'LOCKED' : 'ACTIVE';
    const actionDesc = isCurrentlyActive ? 'Lock (pause payouts & credits)' : 'Unlock (restore normal operations)';
    
    if (!window.confirm(`Are you sure you want to ${actionDesc} for ${wallet.employee_name || 'this technician'}?`)) return;

    try {
      await apiAdminFreezeWallet(wallet.employee_id, nextStatus, `Admin toggle ${nextStatus}`);
      loadData();
    } catch (err) {
      alert(err?.message || 'Failed to update wallet status.');
    }
  };

  const filteredWallets = wallets.filter((w) => {
    const nameMatch = (w.employee_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                      String(w.employee_id).includes(searchTerm);
    const statusMatch = !statusFilter || w.status === statusFilter;
    return nameMatch && statusMatch;
  });

  const totalAvailable = wallets.reduce((acc, w) => acc + parseFloat(w.available_balance || 0), 0);
  const totalPending = wallets.reduce((acc, w) => acc + parseFloat(w.pending_balance || 0), 0);
  const totalWithdrawn = wallets.reduce((acc, w) => acc + parseFloat(w.total_withdrawn || 0), 0);
  const pendingWithdrawalCount = withdrawals.filter((w) => w.status === 'REQUESTED' || w.status === 'PROCESSING').length;

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Wallets & Finance' }]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-zinc-200/90 p-5 rounded-md shadow-card">
          <div>
            <h1 className="text-base sm:text-lg font-bold text-zinc-950 flex items-center gap-2 tracking-tight">
              <Wallet className="w-5 h-5 text-zinc-800" />
              <span>Technician Wallets & Financial Oversight</span>
            </h1>
            <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
              Monitor technician earnings (60% commission share), pending T+7 settlements, and payout disbursements.
            </p>
          </div>
          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={loadData}
              className="px-3.5 py-2 min-h-[38px] text-xs font-bold text-zinc-800 bg-white hover:bg-zinc-50 active:bg-zinc-100 border border-zinc-300 rounded-lg flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5 text-zinc-600" />
              <span>Refresh</span>
            </button>
            <Link
              to="/workforce/admin/wallet/withdrawals"
              className="px-4 py-2 min-h-[38px] text-xs font-bold text-white bg-zinc-900 rounded-lg hover:bg-zinc-800 active:bg-zinc-950 flex items-center gap-2 shadow-xs transition-all cursor-pointer"
            >
              <ArrowDownCircle className="w-4 h-4 text-zinc-200" />
              <span>Manage Payouts ({pendingWithdrawalCount})</span>
            </Link>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-900 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-rose-700 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Aggregate KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white border border-zinc-200/90 p-5 rounded-md shadow-card space-y-2">
            <div className="flex items-center justify-between text-zinc-500">
              <span className="text-xs font-bold uppercase tracking-wider text-zinc-600">Technicians</span>
              <Users className="w-4 h-4 text-zinc-700" />
            </div>
            <div className="text-2xl font-extrabold text-zinc-950 font-mono">
              {wallets.length}
            </div>
            <p className="text-[11px] text-zinc-500 font-medium">Total active technician wallets</p>
          </div>

          <div className="bg-white border border-zinc-200/90 p-5 rounded-md shadow-card space-y-2">
            <div className="flex items-center justify-between text-zinc-500">
              <span className="text-xs font-bold uppercase tracking-wider text-zinc-600">Total Available</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-extrabold text-emerald-800 font-mono">
              {fmt(totalAvailable)}
            </div>
            <p className="text-[11px] text-zinc-500 font-medium">Withdrawable technician balances</p>
          </div>

          <div className="bg-white border border-zinc-200/90 p-5 rounded-md shadow-card space-y-2">
            <div className="flex items-center justify-between text-zinc-500">
              <span className="text-xs font-bold uppercase tracking-wider text-zinc-600">In T+7 Hold</span>
              <Clock className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-2xl font-extrabold text-zinc-950 font-mono">
              {fmt(totalPending)}
            </div>
            <p className="text-[11px] text-zinc-500 font-medium">Pending settlement release</p>
          </div>

          <div className="bg-white border border-zinc-200/90 p-5 rounded-md shadow-card space-y-2">
            <div className="flex items-center justify-between text-zinc-500">
              <span className="text-xs font-bold uppercase tracking-wider text-zinc-600">Total Disbursed</span>
              <TrendingUp className="w-4 h-4 text-zinc-700" />
            </div>
            <div className="text-2xl font-extrabold text-zinc-950 font-mono">
              {fmt(totalWithdrawn)}
            </div>
            <p className="text-[11px] text-zinc-500 font-medium">Lifetime payouts to technicians</p>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="bg-white border border-zinc-200/90 rounded-md p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-card">
          <div className="flex items-center gap-2 flex-1 max-w-sm">
            <Search className="w-4 h-4 text-zinc-400 shrink-0" />
            <input
              type="text"
              placeholder="Search technician name or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 text-xs shadow-xs transition-all"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 min-h-[38px] border border-zinc-300 rounded-lg bg-white text-zinc-800 text-xs outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="LOCKED">Locked</option>
              <option value="SUSPENDED">Suspended</option>
            </select>
          </div>
        </div>

        {/* Technician Wallets Table */}
        <div className="bg-white border border-zinc-200/90 rounded-md shadow-card overflow-hidden text-xs">
          <div className="px-5 py-3.5 border-b border-zinc-200/80 bg-zinc-50/80 font-bold text-zinc-950 text-xs flex items-center justify-between">
            <span>Active Technician Wallets ({filteredWallets.length})</span>
            <Link to="/workforce/admin/wallet/transactions" className="text-zinc-900 hover:underline font-bold text-xs">
              View All Transactions →
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-zinc-50/60 text-zinc-500 uppercase text-[11px] font-bold border-b border-zinc-200">
                <tr>
                  <th className="px-5 py-3.5">Technician</th>
                  <th className="px-5 py-3.5 text-right">Available Balance</th>
                  <th className="px-5 py-3.5 text-right">T+7 Pending</th>
                  <th className="px-5 py-3.5 text-right">Total Earned</th>
                  <th className="px-5 py-3.5 text-right">Total Withdrawn</th>
                  <th className="px-5 py-3.5 text-center">Status</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-12 text-center text-zinc-500">
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="w-4 h-4 animate-spin text-zinc-500" />
                        <span>Loading technician wallet ledger...</span>
                      </div>
                    </td>
                  </tr>
                ) : filteredWallets.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-12 text-center text-zinc-500">
                      No technician wallets matched current search criteria.
                    </td>
                  </tr>
                ) : (
                  filteredWallets.map((w) => {
                    const isActive = w.status === 'ACTIVE';
                    return (
                      <tr key={w.id || w.employee_id} className="hover:bg-zinc-50/80 transition-colors">
                        <td className="px-5 py-4">
                          <div className="font-bold text-zinc-950">{w.employee_name || 'Technician'}</div>
                          <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
                            ID: {w.employee_display_id || w.employee_id}
                          </div>
                        </td>
                        <td className="px-5 py-4 text-right font-mono font-bold text-emerald-800 text-sm">
                          {fmt(w.available_balance)}
                        </td>
                        <td className="px-5 py-4 text-right font-mono text-zinc-700 font-semibold">
                          {fmt(w.pending_balance)}
                        </td>
                        <td className="px-5 py-4 text-right font-mono text-zinc-900 font-bold">
                          {fmt(w.total_earned)}
                        </td>
                        <td className="px-5 py-4 text-right font-mono text-zinc-500">
                          {fmt(w.total_withdrawn)}
                        </td>
                        <td className="px-5 py-4 text-center">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              isActive
                                ? 'bg-emerald-50 text-emerald-900 border border-emerald-200'
                                : 'bg-rose-50 text-rose-900 border border-rose-200'
                            }`}
                          >
                            {w.status || 'ACTIVE'}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleToggleFreeze(w)}
                              className={`px-2.5 py-1.5 min-h-[32px] rounded-lg text-xs font-bold border transition-all flex items-center gap-1 cursor-pointer shadow-xs ${
                                isActive
                                  ? 'border-zinc-300 text-zinc-700 bg-white hover:bg-zinc-50'
                                  : 'border-emerald-300 text-emerald-900 bg-emerald-50 hover:bg-emerald-100'
                              }`}
                              title={isActive ? 'Lock wallet' : 'Unlock wallet'}
                            >
                              {isActive ? (
                                <>
                                  <Lock className="w-3 h-3 text-zinc-600" />
                                  <span>Lock</span>
                                </>
                              ) : (
                                <>
                                  <Unlock className="w-3 h-3 text-emerald-700" />
                                  <span>Unlock</span>
                                </>
                              )}
                            </button>
                            <Link
                              to={`/workforce/admin/wallet/transactions?employee_id=${w.employee_id}`}
                              className="px-2.5 py-1.5 min-h-[32px] rounded-lg text-xs font-bold bg-zinc-100 hover:bg-zinc-200 active:bg-zinc-300 text-zinc-900 transition-all shadow-xs"
                            >
                              Ledger
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default WalletDashboardPage;
