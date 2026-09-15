import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { AppShell } from '../../components/common/AppShell.jsx';
import { apiRequest } from '../../api/client.js';
import {
  Mail,
  UserPlus,
  Send,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Search,
  Filter,
  Users,
  Compass,
  X,
} from 'lucide-react';

export function VendorInvitationsPage() {
  const [invitations, setInvitations] = useState([]);
  const [counts, setCounts] = useState({ all: 0, pending: 0, accepted: 0, rejected: 0, expired: 0, cancelled: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [filterTab, setFilterTab] = useState('PENDING');

  // Direct invite modal state
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteNote, setInviteNote] = useState('');
  const [sendingInvite, setSendingInvite] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const fetchInvitations = async () => {
    try {
      setLoading(true);
      setError('');
      const params = new URLSearchParams();
      if (filterTab !== 'ALL') params.append('status', filterTab);

      const res = await apiRequest(`/workforce/vendor/invitations/?${params.toString()}`);
      setInvitations(res.invitations || []);
      if (res.counts) setCounts(res.counts);
    } catch (err) {
      setError(err.message || 'Failed to load invitations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvitations();
  }, [filterTab]);

  const handleSendDirectInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;

    try {
      setSendingInvite(true);
      setError('');
      await apiRequest('/workforce/vendor/invitations/', {
        method: 'POST',
        json: {
          invited_email: inviteEmail.trim(),
          message: inviteNote.trim(),
          channel: 'DIRECT_EMAIL',
        },
      });

      setSuccessMessage(`Invitation successfully sent to ${inviteEmail}.`);
      setIsInviteModalOpen(false);
      setInviteEmail('');
      setInviteNote('');
      fetchInvitations();
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      setError(err.message || 'Failed to send invitation.');
    } finally {
      setSendingInvite(false);
    }
  };

  const handleCancelInvitation = async (invId) => {
    try {
      setActionLoadingId(invId);
      setError('');
      await apiRequest(`/workforce/vendor/invitations/${invId}/cancel/`, {
        method: 'POST',
      });
      setSuccessMessage('Invitation cancelled.');
      fetchInvitations();
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      setError(err.message || 'Failed to cancel invitation.');
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <AppShell>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Mail className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-slate-900">Sent Invitations</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Manage direct and search-matched invitations sent to technicians.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsInviteModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              <span>Invite by Email</span>
            </button>
          </div>
        </div>

        {/* Alerts */}
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

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
            <span className="text-[11px] font-semibold text-blue-600 uppercase tracking-wider">Pending</span>
            <div className="text-xl font-bold text-blue-700 mt-0.5">{counts.pending}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
            <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider">Accepted</span>
            <div className="text-xl font-bold text-emerald-700 mt-0.5">{counts.accepted}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Declined</span>
            <div className="text-xl font-bold text-slate-700 mt-0.5">{counts.rejected}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
            <span className="text-[11px] font-semibold text-amber-600 uppercase tracking-wider">Expired</span>
            <div className="text-xl font-bold text-amber-700 mt-0.5">{counts.expired}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Cancelled</span>
            <div className="text-xl font-bold text-slate-500 mt-0.5">{counts.cancelled}</div>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 border-b border-slate-200 pb-2 text-xs font-semibold text-slate-600 overflow-x-auto">
          {['PENDING', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'CANCELLED', 'ALL'].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilterTab(tab)}
              className={`px-3 py-1.5 rounded-lg transition-colors capitalize shrink-0 ${
                filterTab === tab
                  ? 'bg-slate-900 text-white font-bold'
                  : 'hover:bg-slate-100 text-slate-600'
              }`}
            >
              {tab.toLowerCase()}
            </button>
          ))}
        </div>

        {/* Invitations Table */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center text-slate-500">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-2" />
              <p className="text-sm">Loading invitations...</p>
            </div>
          ) : invitations.length === 0 ? (
            <div className="py-16 text-center">
              <Mail className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-800">No invitations found</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                No invitations found in this view. Use "Invite by Email" to reach out to certified technicians directly.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-5 py-3">Invitee / Email</th>
                    <th className="px-4 py-3">Channel</th>
                    <th className="px-4 py-3">Message Note</th>
                    <th className="px-4 py-3">Dates</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {invitations.map((inv) => {
                    const isPending = inv.status === 'PENDING';
                    const isAccepted = inv.status === 'ACCEPTED';

                    return (
                      <tr key={inv.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-5 py-3.5">
                          <div className="font-bold text-slate-900">{inv.invited_email}</div>
                          {inv.technician_name && (
                            <span className="text-[11px] text-blue-600 block">{inv.technician_name}</span>
                          )}
                        </td>

                        <td className="px-4 py-3.5">
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-semibold">
                            {inv.channel === 'DIRECT_EMAIL' ? 'Direct Email' : 'Match Search'}
                          </span>
                        </td>

                        <td className="px-4 py-3.5">
                          {inv.message ? (
                            <span className="text-slate-600 italic line-clamp-1 max-w-xs">
                              "{inv.message}"
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        <td className="px-4 py-3.5 text-slate-500">
                          <div>
                            Sent:{' '}
                            {new Date(inv.created_at).toLocaleDateString(undefined, {
                              month: 'short',
                              day: 'numeric',
                            })}
                          </div>
                          {isPending && inv.expires_at && (
                            <div className="text-[10px] text-amber-600">
                              Expires:{' '}
                              {new Date(inv.expires_at).toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                              })}
                            </div>
                          )}
                        </td>

                        <td className="px-4 py-3.5">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                              isPending
                                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                : isAccepted
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : inv.status === 'REJECTED'
                                ? 'bg-slate-100 text-slate-600'
                                : 'bg-red-50 text-red-600'
                            }`}
                          >
                            {inv.status}
                          </span>
                        </td>

                        <td className="px-5 py-3.5 text-right">
                          {isPending && (
                            <button
                              disabled={actionLoadingId === inv.id}
                              onClick={() => handleCancelInvitation(inv.id)}
                              className="px-2.5 py-1 text-slate-500 hover:text-red-700 hover:bg-red-50 rounded text-xs font-semibold transition-colors"
                            >
                              Cancel
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Direct Email Invite Modal */}
        {isInviteModalOpen && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <form onSubmit={handleSendDirectInvite} className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <UserPlus className="w-5 h-5 text-blue-600" />
                  <h3 className="text-base font-bold text-slate-900">Invite Technician by Email</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setIsInviteModalOpen(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  Technician Email Address <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  placeholder="technician@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  If the technician already has an account, the invite will appear in their dashboard immediately. If not, they will receive a registration link.
                </p>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  Personal Offer Message (Optional):
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. We are expanding our AC repair team in Bengaluru and would like to offer you priority dispatch on residential bookings."
                  value={inviteNote}
                  onChange={(e) => setInviteNote(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  disabled={sendingInvite}
                  onClick={() => setIsInviteModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sendingInvite}
                  className="px-5 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{sendingInvite ? 'Sending...' : 'Send Invitation'}</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </AppShell>
  );
}
