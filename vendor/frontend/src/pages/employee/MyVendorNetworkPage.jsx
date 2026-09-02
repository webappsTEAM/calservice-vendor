import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { AppShell } from '../../components/common/AppShell.jsx';
import { apiRequest } from '../../api/client.js';
import {
  Building2,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Briefcase,
  Wallet,
  LogOut,
  Mail,
  ChevronRight,
  Sparkles,
  Info,
  Check,
  UserCheck,
  History,
  FileText,
  FileCheck2,
  Scale,
  Calendar,
} from 'lucide-react';

export function MyVendorNetworkPage() {
  const [relationships, setRelationships] = useState([]);
  const [activeVendor, setActiveVendor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Resignation & Relieving Lifecycle State
  const [relievingStatus, setRelievingStatus] = useState(null);
  const [showResignModal, setShowResignModal] = useState(false);
  const [submittingResign, setSubmittingResign] = useState(false);
  const [resignForm, setResignForm] = useState({
    reason_category: 'TRANSITION_TO_SOLO',
    resignation_notes: '',
    desired_relieving_date: new Date().toISOString().split('T')[0],
    legal_acknowledged: false,
  });

  const fetchNetworkAndStatus = async () => {
    try {
      setLoading(true);
      setError('');
      const [networkData, statusData] = await Promise.all([
        apiRequest('/workforce/technician/network/'),
        apiRequest('/workforce/technician/relieve/status/').catch(() => ({ has_active_request: false })),
      ]);
      setRelationships(networkData.relationships || []);
      setActiveVendor(networkData.active_vendor || null);
      setRelievingStatus(statusData);
    } catch (err) {
      setError(err.message || 'Failed to load your vendor network.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNetworkAndStatus();
  }, []);

  const handleSubmitResignation = async (e) => {
    e.preventDefault();
    if (!resignForm.legal_acknowledged) {
      setError('Please acknowledge the relieving clearance terms.');
      return;
    }

    try {
      setSubmittingResign(true);
      setError('');
      const res = await apiRequest('/workforce/technician/relieve/request/', {
        method: 'POST',
        json: {
          reason_category: resignForm.reason_category,
          resignation_notes: resignForm.resignation_notes,
          desired_relieving_date: resignForm.desired_relieving_date,
        },
      });
      setSuccessMessage(res.message || 'Formal resignation submitted successfully.');
      setShowResignModal(false);
      fetchNetworkAndStatus();
      setTimeout(() => setSuccessMessage(''), 8000);
    } catch (err) {
      setError(err.message || 'Failed to submit resignation request.');
    } finally {
      setSubmittingResign(false);
    }
  };

  const activeRel = relationships.find(
    (r) => r.status === 'ACTIVE' || r.status === 'RESIGNATION_REQUESTED'
  );
  const pastRels = relationships.filter(
    (r) => r.status !== 'ACTIVE' && r.status !== 'RESIGNATION_REQUESTED'
  );

  const activeRequest = relievingStatus?.request;
  const isResignationInProgress = relievingStatus?.has_active_request && activeRequest;

  return (
    <AppShell>
      <div className="p-6 max-w-5xl mx-auto space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Building2 className="w-6 h-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-slate-900">Vendor Assignment & Network</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Manage your current vendor assignment, review operational terms, or submit a formal resignation to transition to a Solo Worker.
            </p>
          </div>

          <NavLink
            to="/workforce/employee/invitations"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
          >
            <Mail className="w-4 h-4" />
            <span>View Invitations</span>
          </NavLink>
        </div>

        {/* Exclusive Single Vendor Assignment Rule Banner */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3.5 shadow-sm">
          <div className="p-2 bg-blue-600 text-white rounded-lg shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Private & Dedicated Vendor Partnership</h3>
            <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
              Your profile is private and operates under your dedicated vendor organization. You can be actively assigned to <strong>one vendor organization at a time</strong>. When resigning, a multi-party settlement clearance (Vendor dues review & SEVO Platform Audit) ensures all dues are settled before transitioning to an independent Solo Worker.
            </p>
          </div>
        </div>

        {/* Notifications */}
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

        {/* Resignation & Relieving Lifecycle Live Progress Tracker */}
        {isResignationInProgress && (
          <div className="bg-white border-2 border-amber-400/80 rounded-2xl p-6 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-amber-100 text-amber-800 rounded-xl">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Formal Resignation & Relieving in Progress
                  </h3>
                  <p className="text-xs text-slate-500">
                    Request ID #{activeRequest.id} • Target Vendor: <strong>{activeRequest.vendor_name}</strong>
                  </p>
                </div>
              </div>
              <span className="px-3 py-1 bg-amber-50 border border-amber-300 text-amber-800 rounded-full text-xs font-bold uppercase tracking-wider">
                {activeRequest.status.replace('_', ' ')}
              </span>
            </div>

            {/* Stepper tracker */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              {/* Step 1 */}
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-emerald-700 uppercase">1. Resignation</span>
                  <Check className="w-4 h-4 text-emerald-600" />
                </div>
                <div className="text-xs font-bold text-slate-800">Submitted</div>
                <p className="text-[11px] text-slate-500 truncate" title={activeRequest.reason_display}>
                  {activeRequest.reason_display}
                </p>
              </div>

              {/* Step 2 */}
              <div className={`p-3.5 rounded-xl space-y-1 border ${
                activeRequest.vendor_approved_at
                  ? 'bg-emerald-50 border-emerald-200'
                  : 'bg-amber-50 border-amber-200'
              }`}>
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-bold uppercase ${
                    activeRequest.vendor_approved_at ? 'text-emerald-700' : 'text-amber-700'
                  }`}>2. Vendor Clearance</span>
                  {activeRequest.vendor_approved_at ? (
                    <Check className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <Clock className="w-4 h-4 text-amber-600 animate-pulse" />
                  )}
                </div>
                <div className="text-xs font-bold text-slate-800">
                  {activeRequest.vendor_approved_at ? 'Dues Cleared' : 'Under Review'}
                </div>
                <p className="text-[11px] text-slate-500 truncate">
                  {activeRequest.vendor_settlement_notes || 'Pending vendor verification'}
                </p>
              </div>

              {/* Step 3 */}
              <div className={`p-3.5 rounded-xl space-y-1 border ${
                activeRequest.sevo_approved_at
                  ? 'bg-emerald-50 border-emerald-200'
                  : activeRequest.vendor_approved_at
                  ? 'bg-amber-50 border-amber-200'
                  : 'bg-slate-50 border-slate-200'
              }`}>
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-bold uppercase ${
                    activeRequest.sevo_approved_at
                      ? 'text-emerald-700'
                      : activeRequest.vendor_approved_at
                      ? 'text-amber-700'
                      : 'text-slate-400'
                  }`}>3. Platform Audit</span>
                  {activeRequest.sevo_approved_at ? (
                    <Check className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <Scale className="w-4 h-4 text-slate-400" />
                  )}
                </div>
                <div className="text-xs font-bold text-slate-800">
                  {activeRequest.sevo_approved_at ? 'Audit Approved' : 'Pending Clearance'}
                </div>
                <p className="text-[11px] text-slate-500 truncate">
                  {activeRequest.sevo_audit_notes || 'SEVO General Check'}
                </p>
              </div>

              {/* Step 4 */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">4. Solo Conversion</span>
                  <Wallet className="w-4 h-4 text-slate-400" />
                </div>
                <div className="text-xs font-bold text-slate-800">Solo Wallet</div>
                <p className="text-[11px] text-slate-500">Auto-provisioned upon clearance</p>
              </div>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-600 flex items-center gap-2">
              <Info className="w-4 h-4 text-blue-600 shrink-0" />
              <span>
                Your request is currently progressing through the multi-party relieving clearance process. Once finalized by SEVO Platform Governance, your status will automatically transition to <strong>Resigned / Solo Worker</strong> and your personal wallet will activate.
              </span>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="py-16 flex flex-col items-center justify-center text-slate-500">
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-2" />
            <p className="text-sm">Loading your vendor status...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Section 1: Current Active Vendor Assignment */}
            <div className="space-y-3">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Current Active Assignment
              </h2>

              {activeRel ? (
                <div className="bg-white border-2 border-emerald-500/80 rounded-2xl p-6 shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-emerald-600 text-white text-[11px] font-bold px-4 py-1 rounded-bl-xl uppercase tracking-wider flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" />
                    <span>
                      {activeRel.status === 'RESIGNATION_REQUESTED' ? 'Resignation In Progress' : 'Actively Assigned'}
                    </span>
                  </div>

                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
                    <div className="space-y-4 flex-1">
                      <div className="flex items-start gap-4">
                        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl shrink-0">
                          <Building2 className="w-6 h-6" />
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-slate-900">{activeRel.vendor_name}</h3>
                          {activeRel.vendor_address && (
                            <p className="text-xs text-slate-500 mt-0.5">{activeRel.vendor_address}</p>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                        <div className="bg-slate-50 border border-slate-100 rounded-xl p-3">
                          <span className="text-[10px] font-semibold text-slate-400 uppercase">Engagement Model</span>
                          <p className="text-xs font-bold text-slate-800 mt-0.5 capitalize">
                            {activeRel.engagement_type.replace('_', ' ').toLowerCase()}
                          </p>
                        </div>

                        <div className="bg-slate-50 border border-slate-100 rounded-xl p-3">
                          <span className="text-[10px] font-semibold text-slate-400 uppercase">Payment Channel</span>
                          <p className="text-xs font-bold text-slate-800 mt-0.5">
                            Tied Vendor Company Wallet
                          </p>
                        </div>

                        <div className="bg-slate-50 border border-slate-100 rounded-xl p-3">
                          <span className="text-[10px] font-semibold text-slate-400 uppercase">Assigned Since</span>
                          <p className="text-xs font-bold text-slate-800 mt-0.5">
                            {new Date(activeRel.started_at).toLocaleDateString(undefined, {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Resignation / Relieve Action Panel */}
                    <div className="md:w-64 bg-slate-50 border border-slate-200/80 rounded-xl p-4 flex flex-col justify-between shrink-0 space-y-3">
                      <div>
                        <span className="text-xs font-bold text-slate-900 block">Leaving Organization?</span>
                        <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                          Submit a formal resignation request to initiate dues settlement clearance and transition to a Solo Worker.
                        </p>
                      </div>

                      {!isResignationInProgress ? (
                        <button
                          type="button"
                          onClick={() => setShowResignModal(true)}
                          className="w-full py-2.5 px-3 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-1.5"
                        >
                          <LogOut className="w-3.5 h-3.5" />
                          <span>Request Resignation</span>
                        </button>
                      ) : (
                        <div className="text-center py-2 px-3 bg-amber-100/70 border border-amber-300 text-amber-900 rounded-lg text-xs font-semibold">
                          Resignation Pending Clearance
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
                    <UserCheck className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Independent Solo Worker</h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                      You are operating as an independent solo worker on the SEVO Platform. You have direct personal wallet access and full freedom to receive direct jobs or accept new vendor invitations.
                    </p>
                  </div>
                  <div className="pt-2 flex items-center justify-center gap-3">
                    <NavLink
                      to="/workforce/employee/wallet"
                      className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-4 py-2 rounded-lg transition-colors border border-emerald-200"
                    >
                      <Wallet className="w-4 h-4" />
                      <span>My Solo Wallet</span>
                    </NavLink>
                    <NavLink
                      to="/workforce/employee/invitations"
                      className="inline-flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-4 py-2 rounded-lg transition-colors"
                    >
                      <span>Check Invitations</span>
                      <ChevronRight className="w-4 h-4" />
                    </NavLink>
                  </div>
                </div>
              )}
            </div>

            {/* Section 2: Previous / Relieved Vendors History */}
            {pastRels.length > 0 && (
              <div className="space-y-3 pt-4">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <History className="w-4 h-4" />
                  <span>Previous Vendor Connections ({pastRels.length})</span>
                </div>

                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <div className="divide-y divide-slate-100 text-xs">
                    {pastRels.map((rel) => {
                      const isResigned = rel.status === 'RESIGNED';
                      return (
                        <div key={rel.relationship_id} className="p-4 flex items-center justify-between gap-4">
                          <div>
                            <span className="font-bold text-slate-800 block">{rel.vendor_name}</span>
                            <span className="text-[11px] text-slate-400">
                              Connected from{' '}
                              {new Date(rel.started_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}
                              {rel.ended_at && ` to ${new Date(rel.ended_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}`}
                            </span>
                          </div>
                          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                            isResigned
                              ? 'bg-blue-50 text-blue-700 border-blue-200'
                              : 'bg-slate-100 text-slate-600 border-slate-200'
                          }`}>
                            {isResigned ? 'Resigned & Relieved' : rel.status}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Formal Resignation Wizard Modal */}
        {showResignModal && activeRel && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-5">
              <div className="flex items-center gap-3 border-b border-slate-100 pb-3">
                <div className="p-3 bg-amber-100 text-amber-700 rounded-xl">
                  <LogOut className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Formal Resignation Request
                  </h3>
                  <p className="text-xs text-slate-500">
                    Vendor: <strong>{activeRel.vendor_name}</strong>
                  </p>
                </div>
              </div>

              <form onSubmit={handleSubmitResignation} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Primary Reason for Leaving *
                  </label>
                  <select
                    value={resignForm.reason_category}
                    onChange={(e) => setResignForm({ ...resignForm, reason_category: e.target.value })}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium"
                    required
                  >
                    <option value="TRANSITION_TO_SOLO">Transitioning to Independent Solo Worker</option>
                    <option value="RELOCATION">Relocation / Moving</option>
                    <option value="PERSONAL">Personal / Family Reasons</option>
                    <option value="RATE_DISPUTE">Compensation / Rate Dispute</option>
                    <option value="CAREER_GROWTH">Career Growth / Alternative Opportunities</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Desired Relieving Date *
                  </label>
                  <input
                    type="date"
                    value={resignForm.desired_relieving_date}
                    onChange={(e) => setResignForm({ ...resignForm, desired_relieving_date: e.target.value })}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Explanation / Settlement Notes (Optional)
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Provide any details regarding pending job settlements or handovers..."
                    value={resignForm.resignation_notes}
                    onChange={(e) => setResignForm({ ...resignForm, resignation_notes: e.target.value })}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      id="legal_ack"
                      checked={resignForm.legal_acknowledged}
                      onChange={(e) => setResignForm({ ...resignForm, legal_acknowledged: e.target.checked })}
                      className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      required
                    />
                    <label htmlFor="legal_ack" className="text-xs text-amber-900 leading-snug cursor-pointer">
                      I confirm that all company equipment will be handed over. I acknowledge that formal relieving requires vendor settlement approval and SEVO platform audit clearance.
                    </label>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    disabled={submittingResign}
                    onClick={() => setShowResignModal(false)}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingResign || !resignForm.legal_acknowledged}
                    className="px-5 py-2 text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white rounded-lg shadow-sm transition-colors flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {submittingResign ? 'Submitting...' : 'Submit Formal Resignation'}
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
