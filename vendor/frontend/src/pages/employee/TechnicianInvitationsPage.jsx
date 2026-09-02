import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { AppShell } from '../../components/common/AppShell.jsx';
import { apiRequest } from '../../api/client.js';
import {
  Mail,
  Check,
  X,
  Building2,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  MessageSquare,
  ShieldCheck,
  ArrowRight,
  Filter,
  LogOut,
} from 'lucide-react';

export function TechnicianInvitationsPage() {
  const [invitations, setInvitations] = useState([]);
  const [activeVendor, setActiveVendor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [actionInProgress, setActionInProgress] = useState(null);
  const [filterTab, setFilterTab] = useState('PENDING');
  const [relieveModalInfo, setRelieveModalInfo] = useState(null);

  const fetchInvitations = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await apiRequest('/workforce/technician/invitations/?status=ALL');
      setInvitations(data.invitations || []);
      setActiveVendor(data.active_vendor || null);
    } catch (err) {
      setError(err.message || 'Failed to load invitations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvitations();
  }, []);

  const handleRespond = async (inv, decision) => {
    // If attempting to accept while already active with a different vendor
    if (decision === 'ACCEPT' && activeVendor && activeVendor.vendor_id !== inv.vendor_id) {
      setRelieveModalInfo({
        newVendor: inv.vendor_name,
        currentVendor: activeVendor.vendor_name,
        invitationId: inv.id,
      });
      return;
    }

    try {
      setActionInProgress(inv.id);
      setError('');
      await apiRequest(`/workforce/technician/invitations/${inv.id}/respond/`, {
        method: 'POST',
        json: { decision },
      });

      if (decision === 'ACCEPT') {
        setSuccessMessage(`Invitation accepted! You are now assigned to ${inv.vendor_name}.`);
        setActiveVendor({
          vendor_id: inv.vendor_id,
          vendor_name: inv.vendor_name,
        });
      } else {
        setSuccessMessage(`Invitation declined.`);
      }

      // Update state locally for fast UI feedback
      setInvitations((prev) =>
        prev.map((i) =>
          i.id === inv.id
            ? { ...i, status: decision === 'ACCEPT' ? 'ACCEPTED' : 'REJECTED' }
            : i
        )
      );

      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      setError(err.message || `Failed to ${decision.toLowerCase()} invitation.`);
    } finally {
      setActionInProgress(null);
    }
  };

  const filtered = invitations.filter((inv) => {
    if (filterTab === 'ALL') return true;
    return inv.status === filterTab;
  });

  const pendingCount = invitations.filter((i) => i.status === 'PENDING').length;
  const acceptedCount = invitations.filter((i) => i.status === 'ACCEPTED').length;
  const rejectedCount = invitations.filter((i) => i.status === 'REJECTED').length;

  return (
    <AppShell>
      <div className="p-6 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Mail className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-slate-900">Vendor Invitations</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Private invitations received directly from verified service businesses.
            </p>
          </div>

          {activeVendor && (
            <NavLink
              to="/workforce/employee/vendor-network"
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold rounded-lg transition-colors"
            >
              <Building2 className="w-4 h-4 text-slate-500" />
              <span>My Vendor Assignment</span>
            </NavLink>
          )}
        </div>

        {/* Current Active Vendor Notice Banner */}
        {activeVendor ? (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-amber-500 text-white rounded-lg shrink-0 mt-0.5">
                <Building2 className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-xs font-bold text-amber-950 uppercase tracking-wider">
                  Currently Assigned to: {activeVendor.vendor_name}
                </h3>
                <p className="text-xs text-amber-800 mt-0.5">
                  You are actively partnered with this vendor. To accept an invitation from another organization, you must first relieve from {activeVendor.vendor_name}.
                </p>
              </div>
            </div>

            <NavLink
              to="/workforce/employee/vendor-network"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-lg shrink-0 transition-colors"
            >
              <span>Manage Assignment</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </NavLink>
          </div>
        ) : (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3.5 shadow-sm">
            <div className="p-2 bg-blue-600 text-white rounded-lg shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Independent Worker Status</h3>
              <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                You are currently free to accept an invitation and join any vendor's team. Once you accept, you will be dedicated to that vendor until you choose to relieve yourself.
              </p>
            </div>
          </div>
        )}

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

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2 text-xs font-semibold text-slate-600">
          <button
            onClick={() => setFilterTab('PENDING')}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              filterTab === 'PENDING' ? 'bg-blue-600 text-white' : 'hover:bg-slate-100 text-slate-600'
            }`}
          >
            <span>Pending</span>
            {pendingCount > 0 && (
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${filterTab === 'PENDING' ? 'bg-blue-800 text-white' : 'bg-blue-100 text-blue-700'}`}>
                {pendingCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setFilterTab('ACCEPTED')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              filterTab === 'ACCEPTED' ? 'bg-emerald-600 text-white' : 'hover:bg-slate-100 text-slate-600'
            }`}
          >
            Accepted ({acceptedCount})
          </button>
          <button
            onClick={() => setFilterTab('REJECTED')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              filterTab === 'REJECTED' ? 'bg-slate-900 text-white' : 'hover:bg-slate-100 text-slate-600'
            }`}
          >
            Declined ({rejectedCount})
          </button>
          <button
            onClick={() => setFilterTab('ALL')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              filterTab === 'ALL' ? 'bg-slate-900 text-white' : 'hover:bg-slate-100 text-slate-600'
            }`}
          >
            All History ({invitations.length})
          </button>
        </div>

        {/* Invitations List */}
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center text-slate-500">
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-2" />
            <p className="text-sm">Loading invitations...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
            <Mail className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-800">
              {filterTab === 'PENDING' ? 'No pending invitations' : 'No invitations found in this tab'}
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              {filterTab === 'PENDING'
                ? 'Keep your skills and availability updated. When vendors match with your profile, your invitations will appear here.'
                : 'Your past invitation decisions are recorded here.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((inv) => {
              const isPending = inv.status === 'PENDING';
              const isAccepted = inv.status === 'ACCEPTED';
              const isRejected = inv.status === 'REJECTED';
              const isAnotherVendorActive = activeVendor && activeVendor.vendor_id !== inv.vendor_id;

              const expiresDate = inv.expires_at
                ? new Date(inv.expires_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })
                : null;

              return (
                <div
                  key={inv.id}
                  className={`bg-white border rounded-xl p-5 shadow-sm transition-all ${
                    isPending ? 'border-blue-200 ring-1 ring-blue-50/50' : 'border-slate-200'
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                    {/* Left: Vendor & Details */}
                    <div className="space-y-3 flex-1">
                      <div className="flex items-start gap-3">
                        <div className="p-2.5 bg-slate-100 text-slate-700 rounded-xl shrink-0 mt-0.5">
                          <Building2 className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h2 className="text-base font-bold text-slate-900">{inv.vendor_name}</h2>
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider ${
                                isPending
                                  ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                  : isAccepted
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : isRejected
                                  ? 'bg-slate-100 text-slate-600'
                                  : 'bg-red-50 text-red-600'
                              }`}
                            >
                              {inv.status}
                            </span>
                          </div>
                          {inv.vendor_address && (
                            <p className="text-xs text-slate-500 mt-0.5">{inv.vendor_address}</p>
                          )}
                        </div>
                      </div>

                      {/* Personal Note from Vendor */}
                      {inv.message && (
                        <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-3 text-xs text-slate-700 flex items-start gap-2">
                          <MessageSquare className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold text-slate-900 block mb-0.5">Note from Vendor:</span>
                            <p className="italic text-slate-600">"{inv.message}"</p>
                          </div>
                        </div>
                      )}

                      {/* Matched Criteria */}
                      {inv.matched_criteria && inv.matched_criteria.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600 pt-1">
                          <span className="text-[11px] font-medium text-slate-400 uppercase">Target Requirements:</span>
                          {inv.matched_criteria.map((c, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 bg-blue-50 border border-blue-200 text-blue-800 rounded text-[11px] font-medium"
                            >
                              {c.attribute}: {Array.isArray(c.value) ? c.value.join(', ') : String(c.value)}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Metadata / Timestamps */}
                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          Received on{' '}
                          {new Date(inv.created_at).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                          })}
                        </span>
                        {isPending && expiresDate && (
                          <span className="text-amber-600 font-medium">
                            Expires on {expiresDate}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Right: Actions */}
                    {isPending && (
                      <div className="flex md:flex-col items-center gap-2 shrink-0 pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
                        <button
                          type="button"
                          disabled={actionInProgress === inv.id}
                          onClick={() => handleRespond(inv, 'ACCEPT')}
                          className="flex-1 md:w-36 py-2 px-4 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-1.5"
                        >
                          <Check className="w-4 h-4" />
                          <span>{actionInProgress === inv.id ? 'Processing...' : 'Accept Offer'}</span>
                        </button>
                        <button
                          type="button"
                          disabled={actionInProgress === inv.id}
                          onClick={() => handleRespond(inv, 'REJECT')}
                          className="flex-1 md:w-36 py-2 px-4 bg-slate-100 hover:bg-red-50 hover:text-red-700 text-slate-700 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5"
                        >
                          <X className="w-4 h-4" />
                          <span>Decline</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Relieve Needed Modal */}
        {relieveModalInfo && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-amber-100 text-amber-600 rounded-full">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Relieve Required to Switch
                  </h3>
                  <p className="text-xs text-slate-500">
                    You are currently assigned to {relieveModalInfo.currentVendor}.
                  </p>
                </div>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                To accept the offer from <strong>{relieveModalInfo.newVendor}</strong>, platform policy requires you to first relieve yourself from <strong>{relieveModalInfo.currentVendor}</strong>.
              </p>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setRelieveModalInfo(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <NavLink
                  to="/workforce/employee/vendor-network"
                  className="px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm flex items-center gap-1.5"
                >
                  <span>Go to Relieve</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </NavLink>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
