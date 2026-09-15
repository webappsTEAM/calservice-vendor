import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthProvider.jsx';
import { apiGetMyPayslips } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import {
  Wallet,
  Calendar,
  TrendingUp,
  Receipt,
  MinusCircle,
  PlusCircle,
} from 'lucide-react';

// HS-B-02: "no technician earnings screen" -- the backend endpoint
// (GET /workforce/payroll/me/, WorkforceMyPayslipsView) already existed
// and the API client function (apiGetMyPayslips) was already defined,
// but nothing in the frontend ever called it -- the /earnings route was
// a stub that just redirected to the dashboard. This page is the missing
// consumer, following the same fetch/loading/error pattern as
// EmployeePerformancePage.jsx.
export function EmployeeEarningsPage() {
  const { user } = useAuth();
  const [payslips, setPayslips] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadPayslips = async () => {
    try {
      setIsLoading(true);
      setError('');
      const res = await apiGetMyPayslips();
      setPayslips(Array.isArray(res) ? res : res?.data || []);
    } catch (err) {
      setError(err.message || 'Failed to load earnings history from server.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPayslips();
  }, []);

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Earnings' }]}>
        <LoadingState message="Loading your earnings history..." />
      </AppShell>
    );
  }

  const money = (v) => {
    const n = Number(v || 0);
    return `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const latest = payslips[0] || null;
  const lifetimeNet = payslips.reduce((sum, p) => sum + Number(p.net_pay || 0), 0);

  return (
    <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Earnings' }]}>
      <div className="space-y-4 max-w-6xl mx-auto">
        {error && <ErrorState message={error} onDismiss={() => setError('')} />}

        {/* Summary strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="bg-white border border-slate-200 rounded p-3.5 shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Latest Payout</span>
              <div className="p-1 rounded bg-slate-50 border border-slate-100 text-slate-600">
                <Wallet className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="text-xl font-bold text-slate-900 font-mono">{latest ? money(latest.net_pay) : '—'}</div>
            <p className="text-[10px] text-slate-500 truncate">{latest ? latest.pay_period_name : 'No payslips yet'}</p>
          </div>
          <div className="bg-white border border-slate-200 rounded p-3.5 shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Lifetime Net Pay</span>
              <div className="p-1 rounded bg-slate-50 border border-slate-100 text-slate-600">
                <TrendingUp className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="text-xl font-bold text-slate-900 font-mono">{money(lifetimeNet)}</div>
            <p className="text-[10px] text-slate-500 truncate">{payslips.length} pay period(s)</p>
          </div>
          <div className="bg-white border border-slate-200 rounded p-3.5 shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Status</span>
              <div className="p-1 rounded bg-slate-50 border border-slate-100 text-slate-600">
                <Receipt className="w-3.5 h-3.5" />
              </div>
            </div>
            <div className="text-xl font-bold text-slate-900 font-mono">{latest ? latest.status : '—'}</div>
            <p className="text-[10px] text-slate-500 truncate">Most recent payslip</p>
          </div>
        </div>

        {/* Payslip history */}
        <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
          <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <Calendar className="w-4 h-4 text-blue-500" />
              Payslip History
            </h2>
          </div>
          {payslips.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No payslips have been generated yet. Payslips appear here once a pay period is processed.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {payslips.map((p) => (
                <div key={p.id} className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <div className="text-sm font-bold text-slate-800">{p.pay_period_name}</div>
                    <div className="text-[11px] text-slate-500">{p.start_date} to {p.end_date}</div>
                    <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-500">
                      <span className="flex items-center gap-1"><PlusCircle className="w-3 h-3 text-emerald-500" /> Base {money(p.base_earnings)}</span>
                      <span className="flex items-center gap-1"><PlusCircle className="w-3 h-3 text-emerald-500" /> Jobs {money(p.job_earnings)}</span>
                      {Number(p.adjustments || 0) !== 0 && (
                        <span className="flex items-center gap-1"><PlusCircle className="w-3 h-3 text-blue-500" /> Adj {money(p.adjustments)}</span>
                      )}
                      {Number(p.deductions || 0) !== 0 && (
                        <span className="flex items-center gap-1"><MinusCircle className="w-3 h-3 text-red-500" /> Deductions {money(p.deductions)}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-lg font-bold text-slate-900 font-mono">{money(p.net_pay)}</div>
                    <StatusBadge status={p.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
