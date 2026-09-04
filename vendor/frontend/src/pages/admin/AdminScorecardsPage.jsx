import React, { useState, useEffect } from 'react';
import { apiAdminListScorecards } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { Star, ShieldCheck, Sparkles } from 'lucide-react';

// SEVO business plan Section 4: admin-facing roster of every worker's/
// provider's persisted rating + SLA scorecard (GET /workforce/admin/scorecards/,
// WorkforceAdminScorecardsListView). Sorted worst-standing first server-side
// so the people needing attention are at the top, not buried.
export function AdminScorecardsPage() {
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setIsLoading(true);
      setError('');
      const res = await apiAdminListScorecards();
      setRows(res.results || []);
    } catch (err) {
      setError(err.message || 'Failed to load scorecards.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const tierBadge = (tier) => {
    const styles = {
      GOLD: 'bg-amber-50 border-amber-300 text-amber-800',
      SILVER: 'bg-slate-100 border-slate-300 text-slate-700',
      BRONZE: 'bg-orange-50 border-orange-300 text-orange-800',
      UNRATED: 'bg-slate-50 border-slate-200 text-slate-500',
    };
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wide ${styles[tier] || styles.UNRATED}`}>
        <Sparkles className="w-3 h-3" />
        {tier}
      </span>
    );
  };

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Scorecards' }]}>
        <LoadingState message="Loading scorecards..." />
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Scorecards' }]}>
      <div className="space-y-4 max-w-6xl mx-auto">
        {error && <ErrorState message={error} onDismiss={() => setError('')} />}

        <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
          <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-500" />
              Worker &amp; Provider Scorecards ({rows.length})
            </h2>
            <button
              type="button"
              onClick={load}
              className="text-[11px] font-semibold text-blue-600 hover:underline"
            >
              Refresh
            </button>
          </div>

          {rows.length === 0 ? (
            <div className="py-12 px-4 text-center text-xs text-slate-500">
              No employees found for this company yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase tracking-wider text-slate-500">
                    <th className="text-left px-4 py-2 font-semibold">Employee</th>
                    <th className="text-left px-4 py-2 font-semibold">Tier</th>
                    <th className="text-right px-4 py-2 font-semibold">Avg. Rating</th>
                    <th className="text-right px-4 py-2 font-semibold">SLA Score</th>
                    <th className="text-right px-4 py-2 font-semibold">Ratings</th>
                    <th className="text-right px-4 py-2 font-semibold">SLA Met / Breach</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((r) => (
                    <tr key={r.employee_id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-2.5 font-semibold text-slate-800">{r.employee_name || `Employee #${r.employee_id}`}</td>
                      <td className="px-4 py-2.5">{tierBadge(r.tier)}</td>
                      <td className="px-4 py-2.5 text-right font-mono">
                        {r.average_rating > 0 ? (
                          <span className="inline-flex items-center gap-1 justify-end">
                            {r.average_rating.toFixed(2)}
                            <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono">{r.rating_count > 0 ? `${r.sla_score}%` : '—'}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-slate-500">{r.rating_count}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-slate-500">
                        {r.sla_met_count} / {r.sla_breach_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

export default AdminScorecardsPage;
