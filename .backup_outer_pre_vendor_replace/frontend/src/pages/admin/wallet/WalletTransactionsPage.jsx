import React, { useEffect, useState, useRef, useCallback } from 'react';
import { AppShell } from '../../../components/common/AppShell.jsx';
import { LoadingState } from '../../../components/enterprise/LoadingState.jsx';
import { apiGetWalletTransactions } from '../../../api/walletService.js';
import { RefreshCw, ChevronLeft, ChevronRight, Search, Filter, X } from 'lucide-react';

function fmt(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', minimumFractionDigits: 2,
  }).format(parseFloat(value || 0));
}

const TXN_TYPES = [
  '', 'SERVICE_EARNING', 'PLATFORM_COMMISSION', 'REFUND', 'RECOVERY_DEBIT',
  'WITHDRAWAL', 'ADJUSTMENT_CREDIT', 'ADJUSTMENT_DEBIT', 'SETTLEMENT_RELEASE',
];
const DIRECTIONS = ['', 'CREDIT', 'DEBIT'];
const STATUSES = ['', 'COMPLETED', 'PENDING_SETTLEMENT', 'REVERSED', 'FAILED'];

function DetailModal({ txn, onClose }) {
  if (!txn) return null;
  const rows = [
    ['ID', txn.id],
    ['Reference Type', txn.reference_type],
    ['Reference ID', txn.reference_id],
    ['Type', txn.transaction_type],
    ['Direction', txn.direction],
    ['Amount', fmt(txn.amount)],
    ['Gross Amount', txn.gross_amount ? fmt(txn.gross_amount) : '—'],
    ['Commission Rate', txn.commission_rate_snapshot ? `${(txn.commission_rate_snapshot * 100).toFixed(2)}%` : '—'],
    ['Commission Amount', txn.commission_amount ? fmt(txn.commission_amount) : '—'],
    ['Balance Before', fmt(txn.balance_before)],
    ['Balance After', fmt(txn.balance_after)],
    ['Balance Type', txn.balance_type],
    ['Status', txn.status],
    ['Settlement Release', txn.settlement_release_at ? new Date(txn.settlement_release_at).toLocaleString('en-IN') : '—'],
    ['Released At', txn.released_at ? new Date(txn.released_at).toLocaleString('en-IN') : '—'],
    ['Service Request ID', txn.service_request_id || '—'],
    ['Payment ID', txn.job_payment_id || '—'],
    ['Description', txn.description || '—'],
    ['Created At', new Date(txn.created_at).toLocaleString('en-IN')],
  ];
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-800">Transaction Detail — #{txn.id}</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100 text-slate-400"><X size={14} /></button>
        </div>
        <div className="overflow-y-auto flex-1 p-4">
          <table className="w-full text-xs">
            <tbody>
              {rows.map(([label, val]) => (
                <tr key={label} className="border-b border-slate-50">
                  <td className="py-1.5 pr-4 font-semibold text-slate-500 w-40 shrink-0">{label}</td>
                  <td className="py-1.5 text-slate-800 break-all">{val}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {txn.metadata && Object.keys(txn.metadata).length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Metadata</p>
              <pre className="text-[10px] bg-slate-50 rounded p-2 overflow-x-auto text-slate-700">
                {JSON.stringify(txn.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function WalletTransactionsPage() {
  const [data, setData] = useState({ results: [], count: 0, page: 1, total_pages: 1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [filters, setFilters] = useState({
    page: 1, page_size: 20,
    type: '', direction: '', status: '',
    date_from: '', date_to: '', search: '',
  });

  const fetchedRef = useRef(false);

  const loadData = useCallback(async (f = filters) => {
    try {
      setLoading(true);
      setError(null);
      const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v !== ''));
      const result = await apiGetWalletTransactions(params);
      setData(result || { results: [], count: 0, page: 1, total_pages: 1 });
    } catch {
      setError('Failed to load transactions.');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    loadData();
  }, []);

  const applyFilters = () => {
    const newFilters = { ...filters, page: 1 };
    setFilters(newFilters);
    loadData(newFilters);
  };

  const changePage = (p) => {
    const newFilters = { ...filters, page: p };
    setFilters(newFilters);
    loadData(newFilters);
  };

  const clearFilters = () => {
    const reset = { page: 1, page_size: 20, type: '', direction: '', status: '', date_from: '', date_to: '', search: '' };
    setFilters(reset);
    loadData(reset);
  };

  const hasFilters = filters.type || filters.direction || filters.status || filters.date_from || filters.date_to || filters.search;

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Wallets', to: '/workforce/admin/wallet/dashboard' }, { label: 'Ledger' }]}>
      <div className="space-y-4 text-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-zinc-200/90 p-5 rounded-md shadow-card">
          <div>
            <h1 className="text-base sm:text-lg font-bold text-zinc-950 tracking-tight">Transaction Ledger</h1>
            <p className="text-xs text-zinc-500 mt-1">{data.count} total records · immutable financial audit trail</p>
          </div>
          <button
            onClick={() => loadData()}
            className="p-2 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 border border-zinc-200 transition-all cursor-pointer"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        {/* Filters */}
        <div className="bg-white border border-zinc-200/90 p-4 rounded-md shadow-card space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
              <input
                type="text"
                placeholder="Search description / ref…"
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-zinc-300 min-h-[38px] focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                value={filters.search}
                onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
                onKeyDown={(e) => e.key === 'Enter' && applyFilters()}
              />
            </div>
            <select
              className="text-xs rounded-lg border border-zinc-300 py-2 px-3 min-h-[38px] bg-white text-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
              value={filters.type}
              onChange={(e) => setFilters(f => ({ ...f, type: e.target.value }))}
            >
              {TXN_TYPES.map(t => <option key={t} value={t}>{t || 'All Types'}</option>)}
            </select>
            <select
              className="text-xs rounded-lg border border-zinc-300 py-2 px-3 min-h-[38px] bg-white text-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
              value={filters.direction}
              onChange={(e) => setFilters(f => ({ ...f, direction: e.target.value }))}
            >
              {DIRECTIONS.map(d => <option key={d} value={d}>{d || 'All Directions'}</option>)}
            </select>
            <select
              className="text-xs rounded-lg border border-zinc-300 py-2 px-3 min-h-[38px] bg-white text-zinc-800 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
              value={filters.status}
              onChange={(e) => setFilters(f => ({ ...f, status: e.target.value }))}
            >
              {STATUSES.map(s => <option key={s} value={s}>{s?.replace('_', ' ') || 'All Statuses'}</option>)}
            </select>
            <input
              type="date"
              className="text-xs rounded-lg border border-zinc-300 py-2 px-3 min-h-[38px] bg-white text-zinc-800 shadow-xs"
              value={filters.date_from}
              onChange={(e) => setFilters(f => ({ ...f, date_from: e.target.value }))}
              title="From date"
            />
            <input
              type="date"
              className="text-xs rounded-lg border border-zinc-300 py-2 px-3 min-h-[38px] bg-white text-zinc-800 shadow-xs"
              value={filters.date_to}
              onChange={(e) => setFilters(f => ({ ...f, date_to: e.target.value }))}
              title="To date"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={applyFilters}
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2 min-h-[38px] text-xs font-bold bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white rounded-lg transition-all shadow-xs cursor-pointer flex-1"
              >
                <Filter size={12} />
                <span>Apply</span>
              </button>
              {hasFilters && (
                <button
                  onClick={clearFilters}
                  className="px-3 py-2 min-h-[38px] text-xs font-bold text-zinc-600 hover:text-zinc-900 border border-zinc-300 rounded-lg hover:bg-zinc-50 flex items-center gap-1 transition-all cursor-pointer"
                >
                  <X size={12} />
                  <span>Clear</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white border border-zinc-200/90 rounded-md shadow-card overflow-hidden text-xs">
          {loading ? (
            <LoadingState message="Loading transactions…" />
          ) : error ? (
            <div className="p-8 text-center text-rose-700">{error}</div>
          ) : data.results.length === 0 ? (
            <div className="p-12 text-center text-zinc-500">No transactions found matching the filter criteria.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-zinc-50/60 text-zinc-500 uppercase text-[11px] font-bold border-b border-zinc-200">
                  <tr>
                    <th className="px-5 py-3.5">ID</th>
                    <th className="px-5 py-3.5">Type</th>
                    <th className="px-5 py-3.5">Direction</th>
                    <th className="px-5 py-3.5 text-right">Amount</th>
                    <th className="px-5 py-3.5 text-right">Balance After</th>
                    <th className="px-5 py-3.5 text-center">Status</th>
                    <th className="px-5 py-3.5">Date</th>
                    <th className="px-5 py-3.5 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 font-medium text-zinc-800">
                  {data.results.map((txn) => (
                    <tr key={txn.id} className="hover:bg-zinc-50/80 transition-colors">
                      <td className="px-5 py-3.5 font-mono font-bold text-zinc-950">#{txn.id}</td>
                      <td className="px-5 py-3.5 font-semibold text-zinc-900">{txn.transaction_type}</td>
                      <td className="px-5 py-3.5">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          txn.direction === 'CREDIT' ? 'bg-emerald-50 text-emerald-900 border border-emerald-200' : 'bg-rose-50 text-rose-900 border border-rose-200'
                        }`}>
                          {txn.direction}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right font-mono font-bold text-zinc-950">
                        {fmt(txn.amount)}
                      </td>
                      <td className="px-5 py-3.5 text-right font-mono text-zinc-600">
                        {fmt(txn.balance_after)}
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          txn.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-900 border border-emerald-200' :
                          txn.status === 'PENDING_SETTLEMENT' ? 'bg-amber-50 text-amber-900 border border-amber-200' :
                          txn.status === 'REVERSED' ? 'bg-rose-50 text-rose-900 border border-rose-200' :
                          'bg-zinc-100 text-zinc-700 border border-zinc-200'
                        }`}>
                          {txn.status?.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-zinc-500 font-mono">{new Date(txn.created_at).toLocaleDateString('en-IN')}</td>
                      <td className="px-5 py-3.5 text-center">
                        <button
                          onClick={() => setSelected(txn)}
                          className="px-2.5 py-1 text-xs font-bold text-zinc-800 hover:text-zinc-950 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-between px-5 py-3.5 border-t border-zinc-100 bg-zinc-50/50">
              <p className="text-xs text-zinc-500 font-medium">
                Page <strong className="text-zinc-900">{data.page}</strong> of <strong className="text-zinc-900">{data.total_pages}</strong> · {data.count} records
              </p>
              <div className="flex items-center gap-1.5">
                <button
                  disabled={data.page <= 1}
                  onClick={() => changePage(data.page - 1)}
                  className="p-1.5 rounded-lg border border-zinc-300 disabled:opacity-40 hover:bg-white transition-colors cursor-pointer"
                >
                  <ChevronLeft size={14} />
                </button>
                <button
                  disabled={data.page >= data.total_pages}
                  onClick={() => changePage(data.page + 1)}
                  className="p-1.5 rounded-lg border border-zinc-300 disabled:opacity-40 hover:bg-white transition-colors cursor-pointer"
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>

        {selected && <DetailModal txn={selected} onClose={() => setSelected(null)} />}
      </div>
    </AppShell>
  );
}
