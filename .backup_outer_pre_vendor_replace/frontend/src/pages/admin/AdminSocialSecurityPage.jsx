import React, { useState, useEffect } from 'react';
import { apiAdminListSocialSecurity, apiAdminMarkSocialSecurityRegistered } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { ShieldCheck, Landmark } from 'lucide-react';

// SEVO business plan Section 8: the admin-facing worklist for Social
// Security Code (2020) registration -- individual workers only, since
// SEVO's aggregator obligation runs to them, not to a provider's own
// team. Registration itself is a manual action taken on the government
// Shram Suvidha portal outside this app; this page tracks who's eligible
// (90+ days worked in the current financial year) and records that the
// submission actually happened (GET/POST /workforce/admin/social-security/*).
export function AdminSocialSecurityPage() {
  const [rows, setRows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('');
  const [openRowId, setOpenRowId] = useState(null);
  const [portalRef, setPortalRef] = useState('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      setIsLoading(true);
      setError('');
      const res = await apiAdminListSocialSecurity(filter || undefined);
      setRows(res.results || []);
    } catch (err) {
      setError(err.message || 'Failed to load Social Security registrations.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const statusBadge = (s) => {
    const styles = {
      NOT_YET_ELIGIBLE: 'bg-slate-50 border-slate-200 text-slate-500',
      ELIGIBLE_PENDING: 'bg-amber-50 border-amber-300 text-amber-800',
      REGISTERED: 'bg-emerald-50 border-emerald-300 text-emerald-800',
    };
    const labels = {
      NOT_YET_ELIGIBLE: 'Not Yet Eligible',
      ELIGIBLE_PENDING: 'Eligible — Pending',
      REGISTERED: 'Registered',
    };
    return (
      <span className={`inline-flex px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wide ${styles[s] || styles.NOT_YET_ELIGIBLE}`}>
        {labels[s] || s}
      </span>
    );
  };

  const handleMarkRegistered = async (registrationId) => {
    if (!portalRef.trim()) {
      setError('A portal reference ID is required to mark a worker as registered.');
      return;
    }
    try {
      setSaving(true);
      setError('');
      await apiAdminMarkSocialSecurityRegistered(registrationId, portalRef.trim());
      setOpenRowId(null);
      setPortalRef('');
      await load();
    } catch (err) {
      setError(err.message || 'Failed to record registration.');
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Social Security' }]}>
        <LoadingState message="Loading Social Security registrations..." />
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Social Security' }]}>
      <div className="space-y-4 max-w-6xl mx-auto">
        {error && <ErrorState message={error} onDismiss={() => setError('')} />}

        <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
          <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-500" />
              Social Security Code Registrations ({rows.length})
            </h2>
            <div className="flex items-center gap-2">
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="px-2 py-1.5 border border-slate-300 rounded text-[11px]"
              >
                <option value="">All statuses</option>
                <option value="NOT_YET_ELIGIBLE">Not Yet Eligible</option>
                <option value="ELIGIBLE_PENDING">Eligible — Pending</option>
                <option value="REGISTERED">Registered</option>
              </select>
              <button
                type="button"
                onClick={load}
                className="text-[11px] font-semibold text-blue-600 hover:underline"
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="px-4 py-2.5 bg-blue-50/60 border-b border-blue-100 text-[10px] text-blue-900 flex items-start gap-1.5">
            <Landmark className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <p>
              Individual workers only -- SEVO is the "aggregator" under the Code on Social Security, 2020
              for this channel and must register eligible workers on the Shram Suvidha portal itself. This
              page tracks eligibility (90+ days worked this financial year) and records that the manual
              portal submission actually happened; it does not submit anything automatically.
            </p>
          </div>

          {rows.length === 0 ? (
            <div className="py-12 px-4 text-center text-xs text-slate-500">
              No individual worker registrations to show.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase tracking-wider text-slate-500">
                    <th className="text-left px-4 py-2 font-semibold">Worker</th>
                    <th className="text-left px-4 py-2 font-semibold">Status</th>
                    <th className="text-right px-4 py-2 font-semibold">Days Worked (FY)</th>
                    <th className="text-left px-4 py-2 font-semibold">FY Start</th>
                    <th className="text-left px-4 py-2 font-semibold">Portal Reference</th>
                    <th className="text-right px-4 py-2 font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((r) => (
                    <React.Fragment key={r.registration_id}>
                      <tr className="hover:bg-slate-50/50">
                        <td className="px-4 py-2.5 font-semibold text-slate-800">{r.employee_name || `Employee #${r.employee_id}`}</td>
                        <td className="px-4 py-2.5">{statusBadge(r.status)}</td>
                        <td className="px-4 py-2.5 text-right font-mono">{r.days_worked_current_fy}</td>
                        <td className="px-4 py-2.5 text-slate-500">{r.financial_year_start}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-500">{r.portal_reference_id || '—'}</td>
                        <td className="px-4 py-2.5 text-right">
                          {r.status !== 'REGISTERED' && (
                            <button
                              type="button"
                              onClick={() => {
                                setOpenRowId(openRowId === r.registration_id ? null : r.registration_id);
                                setPortalRef('');
                                setError('');
                              }}
                              className="text-[11px] font-semibold text-blue-600 hover:underline"
                            >
                              {openRowId === r.registration_id ? 'Cancel' : 'Mark Registered'}
                            </button>
                          )}
                        </td>
                      </tr>
                      {openRowId === r.registration_id && (
                        <tr className="bg-slate-50/70">
                          <td colSpan={6} className="px-4 py-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <input
                                type="text"
                                placeholder="Shram Suvidha portal reference ID"
                                value={portalRef}
                                onChange={(e) => setPortalRef(e.target.value)}
                                className="px-2.5 py-1.5 border border-slate-300 rounded text-xs w-64"
                              />
                              <button
                                type="button"
                                disabled={saving}
                                onClick={() => handleMarkRegistered(r.registration_id)}
                                className="px-3 py-1.5 bg-emerald-600 text-white rounded text-xs font-semibold hover:bg-emerald-700 disabled:opacity-50"
                              >
                                {saving ? 'Saving...' : 'Confirm Registration'}
                              </button>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
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

export default AdminSocialSecurityPage;
