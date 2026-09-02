import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { AppShell } from '../../components/common/AppShell.jsx';
import { apiRequest } from '../../api/client.js';
import {
  Users,
  Search,
  Filter,
  UserPlus,
  Compass,
  Star,
  CheckCircle2,
  AlertTriangle,
  MoreVertical,
  PauseCircle,
  PlayCircle,
  XCircle,
  Phone,
  Mail,
  Briefcase,
  Layers,
  FileText,
  FileCheck2,
  Check,
  Clock,
  LogOut,
} from 'lucide-react';

export function VendorTechnicianNetworkPage() {
  const [technicians, setTechnicians] = useState([]);
  const [relievingRequests, setRelievingRequests] = useState([]);
  const [counts, setCounts] = useState({ all: 0, active: 0, suspended: 0, terminated: 0, resigned: 0, resignation_requested: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [actionLoadingId, setActionLoadingId] = useState(null);

  // Approval Modal State
  const [selectedRelievingForApproval, setSelectedRelievingForApproval] = useState(null);
  const [settlementNotes, setSettlementNotes] = useState('All job dues, advances, and company equipment have been settled.');
  const [approvingRelieving, setApprovingRelieving] = useState(false);

  const fetchRosterAndRequests = async () => {
    try {
      setLoading(true);
      setError('');
      const params = new URLSearchParams();
      if (statusFilter !== 'ALL') params.append('status', statusFilter);
      if (searchQuery) params.append('search', searchQuery);

      const [rosterRes, relievingRes] = await Promise.all([
        apiRequest(`/workforce/vendor/network/?${params.toString()}`),
        apiRequest('/workforce/vendor/relieving-requests/').catch(() => ({ relieving_requests: [] })),
      ]);

      setTechnicians(rosterRes.technicians || []);
      if (rosterRes.counts) setCounts(rosterRes.counts);
      setRelievingRequests(relievingRes.relieving_requests || []);
    } catch (err) {
      setError(err.message || 'Failed to load technician roster.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRosterAndRequests();
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchRosterAndRequests();
  };

  const handleUpdateStatus = async (relId, action, techName) => {
    try {
      setActionLoadingId(relId);
      setError('');
      await apiRequest(`/workforce/vendor/network/${relId}/status/`, {
        method: 'POST',
        json: { action },
      });
      setSuccessMessage(`Technician ${techName} updated to ${action.toLowerCase()}d.`);
      fetchRosterAndRequests();
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      setError(err.message || 'Failed to update technician status.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleApproveRelieving = async (e) => {
    e.preventDefault();
    if (!selectedRelievingForApproval) return;
    try {
      setApprovingRelieving(true);
      setError('');
      const res = await apiRequest(`/workforce/vendor/relieving-requests/${selectedRelievingForApproval.id}/approve/`, {
        method: 'POST',
        json: { settlement_notes: settlementNotes },
      });
      setSuccessMessage(res.message || 'Vendor settlement clearance approved.');
      setSelectedRelievingForApproval(null);
      fetchRosterAndRequests();
      setTimeout(() => setSuccessMessage(''), 6000);
    } catch (err) {
      setError(err.message || 'Failed to approve relieving request.');
    } finally {
      setApprovingRelieving(false);
    }
  };

  const pendingRelievingCount = relievingRequests.filter((r) => r.status === 'REQUESTED').length;

  return (
    <AppShell>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Users className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-slate-900">My Tied Technicians</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Technicians roster dedicated to your vendor organization. Review operational status, manage partnerships, and approve formal resignations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <NavLink
              to="/workforce/admin/vendor-invitations"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              <span>Send / View Invitations</span>
            </NavLink>
          </div>
        </div>

        {/* Feedback Alerts */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {successMessage && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Pending Resignation / Relieving Banner */}
        {pendingRelievingCount > 0 && (
          <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-200 text-amber-900 rounded-lg shrink-0">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-amber-900">
                  {pendingRelievingCount} Pending Resignation Request(s)
                </h3>
                <p className="text-xs text-amber-700 mt-0.5">
                  Technicians have requested formal relieving. Please verify job dues, accounts, and equipment to grant settlement clearance.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                const firstPending = relievingRequests.find((r) => r.status === 'REQUESTED');
                if (firstPending) setSelectedRelievingForApproval(firstPending);
              }}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-lg transition-colors shrink-0 shadow-sm"
            >
              Review Relieving Requests
            </button>
          </div>
        )}

        {/* Roster Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">All Members</span>
            <div className="text-2xl font-bold text-slate-900 mt-1">{counts.all}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Active</span>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{counts.active}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Resigned</span>
            <div className="text-2xl font-bold text-blue-600 mt-1">{counts.resigned || 0}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-amber-600 uppercase tracking-wider">Suspended</span>
            <div className="text-2xl font-bold text-amber-600 mt-1">{counts.suspended}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Terminated</span>
            <div className="text-2xl font-bold text-slate-700 mt-1">{counts.terminated}</div>
          </div>
        </div>

        {/* Controls: Search and Filters */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white p-3 border border-slate-200 rounded-xl shadow-sm">
          {/* Status Tabs */}
          <div className="flex flex-wrap items-center gap-1 text-xs font-semibold text-slate-600">
            {['ALL', 'ACTIVE', 'RESIGNED', 'SUSPENDED', 'TERMINATED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg transition-colors capitalize ${
                  statusFilter === st
                    ? 'bg-slate-900 text-white font-bold'
                    : 'hover:bg-slate-100 text-slate-600'
                }`}
              >
                {st.toLowerCase().replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by name, skill, email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg w-64 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
            >
              Filter
            </button>
          </form>
        </div>

        {/* Technician Roster Table */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center text-slate-500">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-2" />
              <p className="text-sm">Loading technician network...</p>
            </div>
          ) : technicians.length === 0 ? (
            <div className="py-16 text-center">
              <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-800">No technicians found</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                No technicians match this view. Use "Send / View Invitations" to invite certified workers to your vendor team.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-5 py-3">Technician</th>
                    <th className="px-4 py-3">Skills & Services</th>
                    <th className="px-4 py-3">Rating & Tier</th>
                    <th className="px-4 py-3">Engagement</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {technicians.map((t) => {
                    const isActive = t.status === 'ACTIVE';
                    const isSuspended = t.status === 'SUSPENDED';
                    const isResigned = t.status === 'RESIGNED';
                    const isResignRequested = t.status === 'RESIGNATION_REQUESTED';
                    const isTerminated = t.status === 'TERMINATED';

                    const matchingRelievingReq = relievingRequests.find(
                      (r) => r.relationship_id === t.relationship_id && r.status === 'REQUESTED'
                    );

                    return (
                      <tr key={t.relationship_id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full font-bold flex items-center justify-center text-xs ${
                              isResigned ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-700'
                            }`}>
                              {t.name.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <span className="font-bold text-slate-900 block">{t.name}</span>
                              <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                                <span>{t.email}</span>
                                {t.phone && <span>• {t.phone}</span>}
                                {t.state && <span>• {t.state}</span>}
                              </div>
                            </div>
                          </div>
                        </td>

                        <td className="px-4 py-3.5">
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {t.scope_skills && t.scope_skills.length > 0 ? (
                              t.scope_skills.slice(0, 3).map((s, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-medium"
                                >
                                  {s}
                                </span>
                              ))
                            ) : (
                              <span className="text-slate-400 italic text-[11px]">General</span>
                            )}
                            {t.scope_skills && t.scope_skills.length > 3 && (
                              <span className="text-[10px] text-slate-500 self-center">
                                +{t.scope_skills.length - 3} more
                              </span>
                            )}
                          </div>
                        </td>

                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-1.5">
                            <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                            <span className="font-bold text-slate-800">
                              {t.average_rating > 0 ? t.average_rating.toFixed(1) : 'New'}
                            </span>
                            {t.rating_count > 0 && (
                              <span className="text-slate-400 text-[10px]">({t.rating_count})</span>
                            )}
                            {t.tier && t.tier !== 'UNRATED' && (
                              <span className="ml-1 px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200 text-[9px] font-semibold">
                                {t.tier}
                              </span>
                            )}
                          </div>
                        </td>

                        <td className="px-4 py-3.5">
                          <div className="text-slate-700 capitalize">
                            {t.engagement_type.replace('_', ' ').toLowerCase()}
                          </div>
                          <span className="text-[10px] text-slate-400 block">
                            Tied Vendor Settlement
                          </span>
                        </td>

                        <td className="px-4 py-3.5">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                              isActive
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : isResignRequested
                                ? 'bg-amber-50 text-amber-800 border-amber-300 animate-pulse'
                                : isResigned
                                ? 'bg-blue-50 text-blue-700 border-blue-200'
                                : isSuspended
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : 'bg-slate-100 text-slate-600 border-slate-200'
                            }`}
                          >
                            {isResignRequested
                              ? 'Resignation Pending'
                              : isResigned
                              ? 'Resigned'
                              : t.status}
                          </span>
                        </td>

                        <td className="px-5 py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {matchingRelievingReq && (
                              <button
                                type="button"
                                onClick={() => setSelectedRelievingForApproval(matchingRelievingReq)}
                                className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-bold transition-colors flex items-center gap-1 shadow-sm"
                                title="Review and clear resignation"
                              >
                                <FileCheck2 className="w-3.5 h-3.5" />
                                <span>Clear Resignation</span>
                              </button>
                            )}

                            {isActive && (
                              <button
                                disabled={actionLoadingId === t.relationship_id}
                                onClick={() => handleUpdateStatus(t.relationship_id, 'SUSPEND', t.name)}
                                className="px-2.5 py-1 text-slate-600 hover:text-amber-700 hover:bg-amber-50 rounded text-xs font-semibold transition-colors flex items-center gap-1"
                                title="Temporarily pause job offers"
                              >
                                <PauseCircle className="w-3.5 h-3.5 text-amber-600" />
                                <span>Suspend</span>
                              </button>
                            )}

                            {isSuspended && (
                              <button
                                disabled={actionLoadingId === t.relationship_id}
                                onClick={() => handleUpdateStatus(t.relationship_id, 'REACTIVATE', t.name)}
                                className="px-2.5 py-1 text-emerald-700 hover:bg-emerald-50 rounded text-xs font-semibold transition-colors flex items-center gap-1"
                                title="Resume active partnership"
                              >
                                <PlayCircle className="w-3.5 h-3.5 text-emerald-600" />
                                <span>Reactivate</span>
                              </button>
                            )}

                            {!isResigned && !isTerminated && (
                              <button
                                disabled={actionLoadingId === t.relationship_id}
                                onClick={() => handleUpdateStatus(t.relationship_id, 'TERMINATE', t.name)}
                                className="px-2 py-1 text-slate-400 hover:text-red-700 hover:bg-red-50 rounded text-xs transition-colors"
                                title="Involuntarily terminate partnership"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                              </button>
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

        {/* Vendor Resignation Settlement Clearance Modal */}
        {selectedRelievingForApproval && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-5">
              <div className="flex items-center gap-3 border-b border-slate-100 pb-3">
                <div className="p-3 bg-amber-100 text-amber-800 rounded-xl">
                  <FileCheck2 className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Vendor Resignation Dues Clearance
                  </h3>
                  <p className="text-xs text-slate-500">
                    Technician: <strong>{selectedRelievingForApproval.technician_name}</strong>
                  </p>
                </div>
              </div>

              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="font-semibold text-slate-500">Reason Category:</span>
                  <span className="font-bold text-slate-800">{selectedRelievingForApproval.reason_display}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-semibold text-slate-500">Desired Relieving Date:</span>
                  <span className="font-bold text-slate-800">{selectedRelievingForApproval.desired_relieving_date}</span>
                </div>
                {selectedRelievingForApproval.resignation_notes && (
                  <div className="pt-1">
                    <span className="font-semibold text-slate-500 block mb-0.5">Technician's Explanation:</span>
                    <p className="p-2 bg-white rounded border border-slate-200 text-slate-700 italic">
                      "{selectedRelievingForApproval.resignation_notes}"
                    </p>
                  </div>
                )}
              </div>

              <form onSubmit={handleApproveRelieving} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Settlement & Dues Remarks *
                  </label>
                  <textarea
                    rows={3}
                    value={settlementNotes}
                    onChange={(e) => setSettlementNotes(e.target.value)}
                    placeholder="Document equipment return and job dues confirmation..."
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    required
                  />
                </div>

                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 flex items-start gap-2">
                  <Check className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                  <span>
                    By approving, you confirm that all internal company advances, tools, and completed jobs under your vendor organization have been settled. Request will be forwarded for SEVO Platform Audit.
                  </span>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    disabled={approvingRelieving}
                    onClick={() => setSelectedRelievingForApproval(null)}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={approvingRelieving}
                    className="px-5 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
                  >
                    {approvingRelieving ? 'Approving...' : 'Approve Settlement Clearance'}
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
