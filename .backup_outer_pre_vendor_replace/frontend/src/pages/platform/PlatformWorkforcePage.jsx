import React, { useState, useEffect } from 'react';
import { useSearchParams, NavLink } from 'react-router-dom';
import { AppShell } from '../../components/common/AppShell.jsx';
import { apiRequest } from '../../api/client.js';
import {
  Users,
  Building2,
  Search,
  Mail,
  Phone,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  UserCheck,
  Briefcase,
  Filter,
  Layers,
  ArrowRight,
  Sparkles,
  Link as LinkIcon,
  Unlink,
  RefreshCw,
  X,
  FileCheck2,
  FileText,
  Clock,
  Scale,
  Calendar,
  ShieldCheck,
} from 'lucide-react';

export function PlatformWorkforcePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialVendorId = searchParams.get('vendor_id') || '';

  const [workers, setWorkers] = useState([]);
  const [counts, setCounts] = useState({ all: 0, solo: 0, tied: 0 });
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [filterType, setFilterType] = useState('ALL'); // 'ALL' | 'SOLO' | 'TIED' | 'RELIEVING_AUDITS'
  const [selectedVendorId, setSelectedVendorId] = useState(initialVendorId);
  const [searchTerm, setSearchTerm] = useState('');

  // Tie / Untie Modal State
  const [activeModalWorker, setActiveModalWorker] = useState(null);
  const [targetVendorId, setTargetVendorId] = useState('');
  const [engagementType, setEngagementType] = useState('PER_JOB');
  const [notes, setNotes] = useState('');
  const [modalSubmitting, setModalSubmitting] = useState(false);

  // Relieving Audit Queue State
  const [relievingRequests, setRelievingRequests] = useState([]);
  const [pendingAuditCount, setPendingAuditCount] = useState(0);
  const [selectedRelievingForAudit, setSelectedRelievingForAudit] = useState(null);
  const [auditNotes, setAuditNotes] = useState(
    'Verified all platform job commissions, customer bookings, and billings have settled.'
  );
  const [auditSubmitting, setAuditSubmitting] = useState(false);

  const fetchWorkforce = async () => {
    try {
      setLoading(true);
      setError('');
      const params = new URLSearchParams();
      if (filterType !== 'ALL' && filterType !== 'RELIEVING_AUDITS') {
        params.append('type', filterType);
      }
      if (selectedVendorId) params.append('vendor_id', selectedVendorId);
      if (searchTerm) params.append('search', searchTerm);

      const [workforceData, relievingData] = await Promise.all([
        apiRequest(`/workforce/platform/workforce/?${params.toString()}`),
        apiRequest('/workforce/platform/relieving-requests/').catch(() => ({
          relieving_requests: [],
          pending_sevo_count: 0,
        })),
      ]);

      setWorkers(workforceData.workers || []);
      if (workforceData.counts) setCounts(workforceData.counts);

      setRelievingRequests(relievingData.relieving_requests || []);
      setPendingAuditCount(relievingData.pending_sevo_count || 0);
    } catch (err) {
      setError(err.message || 'Failed to load platform workforce.');
    } finally {
      setLoading(false);
    }
  };

  const fetchVendorsList = async () => {
    try {
      const data = await apiRequest('/workforce/platform/vendors/');
      setVendors(data.vendors || []);
    } catch (_) {}
  };

  useEffect(() => {
    fetchVendorsList();
  }, []);

  useEffect(() => {
    fetchWorkforce();
  }, [filterType, selectedVendorId]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchWorkforce();
  };

  const openTieModal = (worker) => {
    setActiveModalWorker(worker);
    setTargetVendorId(worker.tied_vendor ? String(worker.tied_vendor.id) : '');
    setEngagementType('PER_JOB');
    setNotes('');
  };

  const handleTieWorker = async (e) => {
    e.preventDefault();
    if (!activeModalWorker || !targetVendorId) return;

    try {
      setModalSubmitting(true);
      setError('');
      const res = await apiRequest(`/workforce/platform/workforce/${activeModalWorker.id}/tie-vendor/`, {
        method: 'POST',
        json: {
          vendor_id: targetVendorId,
          engagement_type: engagementType,
          notes,
        },
      });

      setSuccessMessage(res.message || `Technician tied to ${res.vendor_name}.`);
      setActiveModalWorker(null);
      fetchWorkforce();
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      setError(err.message || 'Failed to tie technician to vendor.');
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleUntieWorker = async () => {
    if (!activeModalWorker) return;

    try {
      setModalSubmitting(true);
      setError('');
      const res = await apiRequest(`/workforce/platform/workforce/${activeModalWorker.id}/untie-vendor/`, {
        method: 'POST',
      });

      setSuccessMessage(res.message || 'Technician relieved and converted to Solo Worker.');
      setActiveModalWorker(null);
      fetchWorkforce();
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err) {
      setError(err.message || 'Failed to untie technician.');
    } finally {
      setModalSubmitting(false);
    }
  };

  // SEVO Platform Audit Approval Handler
  const handleApprovePlatformAudit = async (e) => {
    e.preventDefault();
    if (!selectedRelievingForAudit) return;

    try {
      setAuditSubmitting(true);
      setError('');
      const res = await apiRequest(
        `/workforce/platform/relieving-requests/${selectedRelievingForAudit.id}/approve/`,
        {
          method: 'POST',
          json: { audit_notes: auditNotes },
        }
      );

      setSuccessMessage(
        res.message ||
          `Relieving request #${selectedRelievingForAudit.id} approved by SEVO Platform. Clearance complete.`
      );
      setSelectedRelievingForAudit(null);
      fetchWorkforce();
      setTimeout(() => setSuccessMessage(''), 6000);
    } catch (err) {
      setError(err.message || 'Failed to approve platform relieving audit.');
    } finally {
      setAuditSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Users className="w-6 h-6 text-indigo-600" />
              <h1 className="text-2xl font-bold text-slate-900">Workforce Oversight (Solo & Tied Workers)</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              SEVO Platform Admin: Manage all technicians, directly tie solo workers to any vendor, audit resignations, and relieve workers.
            </p>
          </div>

          <NavLink
            to="/workforce/platform/vendors"
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold rounded-lg transition-colors"
          >
            <Building2 className="w-4 h-4 text-slate-500" />
            <span>Manage Vendor Companies</span>
          </NavLink>
        </div>

        {/* Global Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Technicians</span>
            <div className="text-2xl font-bold text-slate-900 mt-1">{counts.all}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">Solo Workers</span>
            <div className="text-2xl font-bold text-blue-600 mt-1">{counts.solo}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Tied Workers</span>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{counts.tied}</div>
          </div>
          <div
            onClick={() => setFilterType('RELIEVING_AUDITS')}
            className={`border rounded-xl p-4 shadow-sm cursor-pointer transition-all ${
              filterType === 'RELIEVING_AUDITS'
                ? 'bg-purple-50 border-purple-300 ring-2 ring-purple-400'
                : 'bg-white border-slate-200 hover:border-purple-200'
            }`}
          >
            <span className="text-xs font-semibold text-purple-700 uppercase tracking-wider flex items-center justify-between">
              <span>Pending Relieving Audits</span>
              {pendingAuditCount > 0 && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-600 text-white animate-pulse">
                  Action Required
                </span>
              )}
            </span>
            <div className="text-2xl font-bold text-purple-700 mt-1">{pendingAuditCount}</div>
          </div>
        </div>

        {/* Error / Success Alerts */}
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

        {/* Controls / Filter Bar */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* Filter Tabs */}
            <div className="flex items-center gap-2 text-xs font-semibold flex-wrap">
              <button
                type="button"
                onClick={() => setFilterType('ALL')}
                className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                  filterType === 'ALL' ? 'bg-indigo-600 text-white' : 'hover:bg-slate-100 text-slate-600'
                }`}
              >
                <span>All Workforce</span>
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                    filterType === 'ALL' ? 'bg-indigo-800 text-white' : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {counts.all}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setFilterType('SOLO')}
                className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                  filterType === 'SOLO' ? 'bg-blue-600 text-white' : 'hover:bg-slate-100 text-slate-600'
                }`}
              >
                <span>Solo Workers</span>
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                    filterType === 'SOLO' ? 'bg-blue-800 text-white' : 'bg-blue-100 text-blue-700'
                  }`}
                >
                  {counts.solo}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setFilterType('TIED')}
                className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                  filterType === 'TIED' ? 'bg-emerald-600 text-white' : 'hover:bg-slate-100 text-slate-600'
                }`}
              >
                <span>Tied Workers</span>
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                    filterType === 'TIED' ? 'bg-emerald-800 text-white' : 'bg-emerald-100 text-emerald-700'
                  }`}
                >
                  {counts.tied}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setFilterType('RELIEVING_AUDITS')}
                className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                  filterType === 'RELIEVING_AUDITS'
                    ? 'bg-purple-600 text-white'
                    : 'hover:bg-purple-50 text-purple-700 border border-purple-200'
                }`}
              >
                <Scale className="w-3.5 h-3.5" />
                <span>Resignation Audits</span>
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                    filterType === 'RELIEVING_AUDITS'
                      ? 'bg-purple-800 text-white'
                      : pendingAuditCount > 0
                      ? 'bg-purple-600 text-white'
                      : 'bg-purple-100 text-purple-700'
                  }`}
                >
                  {pendingAuditCount}
                </span>
              </button>
            </div>

            {/* Vendor Filter Dropdown */}
            {filterType !== 'RELIEVING_AUDITS' && (
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-slate-400 shrink-0" />
                <select
                  value={selectedVendorId}
                  onChange={(e) => {
                    setSelectedVendorId(e.target.value);
                    setSearchParams(e.target.value ? { vendor_id: e.target.value } : {});
                  }}
                  className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="">Filter by Vendor (All Vendors)</option>
                  {vendors.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.company_name} ({v.tied_workers_count} tied)
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Search Form (when viewing workforce list) */}
          {filterType !== 'RELIEVING_AUDITS' && (
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search technician by name, ID (e.g. EMP-...), email, phone..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white"
                />
              </div>
              <button
                type="submit"
                className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition-colors"
              >
                Search
              </button>
            </form>
          )}
        </div>

        {/* VIEW 1: SEVO Platform Resignation & Relieving Audits Table */}
        {filterType === 'RELIEVING_AUDITS' ? (
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden space-y-0">
            <div className="p-4 bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-purple-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-purple-700" />
                <div>
                  <h2 className="text-sm font-bold text-slate-900">
                    SEVO Platform Relieving & Settlement Audit Queue
                  </h2>
                  <p className="text-xs text-slate-500">
                    Verify all vendor job settlements and platform earnings before approving technician's solo worker conversion.
                  </p>
                </div>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 bg-white border border-purple-200 text-purple-700 rounded-lg">
                Total Requests: {relievingRequests.length}
              </span>
            </div>

            {loading ? (
              <div className="py-16 flex flex-col items-center justify-center text-slate-500">
                <div className="w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mb-2" />
                <p className="text-sm">Loading resignation audits...</p>
              </div>
            ) : relievingRequests.length === 0 ? (
              <div className="py-16 text-center space-y-2">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                <h3 className="text-sm font-bold text-slate-800">No Pending Relieving Audits</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  All technician resignations and vendor clearances have been audited and completed.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="px-5 py-3">Technician</th>
                      <th className="px-4 py-3">Vendor Company</th>
                      <th className="px-4 py-3">Resignation Details</th>
                      <th className="px-4 py-3">Vendor Settlement</th>
                      <th className="px-4 py-3">Audit Status</th>
                      <th className="px-5 py-3 text-right">SEVO Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {relievingRequests.map((req) => {
                      const isVendorApproved = req.status === 'VENDOR_APPROVED';
                      const isCompleted = req.status === 'COMPLETED';

                      return (
                        <tr key={req.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2.5">
                              <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-xs shrink-0">
                                {req.technician_name.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <span className="font-bold text-slate-900 block">{req.technician_name}</span>
                                <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                                  <span>{req.technician_email}</span>
                                  {req.technician_phone && <span>• {req.technician_phone}</span>}
                                </div>
                              </div>
                            </div>
                          </td>

                          <td className="px-4 py-4">
                            <div className="flex items-center gap-1.5">
                              <Building2 className="w-4 h-4 text-slate-400" />
                              <span className="font-bold text-slate-800">{req.vendor_name}</span>
                            </div>
                            <span className="text-[10px] text-slate-400 block mt-0.5 font-mono">
                              Request #{req.id}
                            </span>
                          </td>

                          <td className="px-4 py-4 max-w-xs">
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 mb-1">
                              {req.reason_display || req.reason_category}
                            </span>
                            {req.resignation_notes && (
                              <p className="text-[11px] text-slate-600 line-clamp-2">
                                "{req.resignation_notes}"
                              </p>
                            )}
                            <span className="text-[10px] text-slate-400 flex items-center gap-1 mt-1">
                              <Calendar className="w-3 h-3" />
                              Effective: {req.desired_relieving_date || 'Immediate'}
                            </span>
                          </td>

                          <td className="px-4 py-4 max-w-xs">
                            {req.vendor_settlement_notes ? (
                              <div className="space-y-1">
                                <p className="text-[11px] text-slate-700 font-medium line-clamp-2">
                                  {req.vendor_settlement_notes}
                                </p>
                                <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                                  <CheckCircle2 className="w-3 h-3" />
                                  Vendor Approved {req.vendor_approved_at ? new Date(req.vendor_approved_at).toLocaleDateString() : ''}
                                </span>
                              </div>
                            ) : (
                              <span className="text-[11px] text-amber-600 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                Awaiting Vendor Dues Clearance
                              </span>
                            )}
                          </td>

                          <td className="px-4 py-4">
                            {isCompleted ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Relieved (Solo Worker)</span>
                              </span>
                            ) : isVendorApproved ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200 animate-pulse">
                                <Scale className="w-3 h-3" />
                                <span>Pending SEVO Audit</span>
                              </span>
                            ) : req.status === 'SEVO_APPROVED' ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                                <ShieldCheck className="w-3 h-3" />
                                <span>Audit Approved</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                                <Clock className="w-3 h-3" />
                                <span>Requested</span>
                              </span>
                            )}
                          </td>

                          <td className="px-5 py-4 text-right">
                            {isVendorApproved ? (
                              <button
                                type="button"
                                onClick={() => setSelectedRelievingForAudit(req)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold shadow-sm transition-colors"
                              >
                                <FileCheck2 className="w-3.5 h-3.5" />
                                <span>Audit & Clear</span>
                              </button>
                            ) : isCompleted ? (
                              <span className="text-[11px] font-bold text-slate-400">
                                Solo Wallet Active
                              </span>
                            ) : (
                              <button
                                type="button"
                                disabled
                                className="px-3 py-1 text-slate-400 bg-slate-100 rounded text-[11px] font-semibold cursor-not-allowed"
                                title="Waiting for vendor admin to sign off on equipment and dues"
                              >
                                Vendor Pending
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
        ) : (
          /* VIEW 2: Standard Workforce Oversight Table */
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            {loading ? (
              <div className="py-16 flex flex-col items-center justify-center text-slate-500">
                <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mb-2" />
                <p className="text-sm">Loading workforce...</p>
              </div>
            ) : workers.length === 0 ? (
              <div className="py-16 text-center">
                <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-slate-800">No technicians found</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  No workers match your filter criteria.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="px-5 py-3">Technician</th>
                      <th className="px-4 py-3">Workforce Classification</th>
                      <th className="px-4 py-3">Trade Skills</th>
                      <th className="px-4 py-3">Contact</th>
                      <th className="px-4 py-3">Location</th>
                      <th className="px-5 py-3 text-right">Vendor Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {workers.map((w) => {
                      const isTied = w.workforce_type === 'TIED';
                      const isResigned = w.last_relationship_status === 'RESIGNED';

                      return (
                        <tr key={w.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 font-bold text-xs shrink-0">
                                {w.name.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <span className="font-bold text-slate-900 text-sm block">{w.name}</span>
                                <span className="text-[11px] text-slate-400 font-mono">
                                  ID: {w.employee_id || `#${w.id}`}
                                </span>
                              </div>
                            </div>
                          </td>

                          <td className="px-4 py-4">
                            {isTied && w.tied_vendor ? (
                              <div className="space-y-1">
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  <Building2 className="w-3 h-3" />
                                  <span>Tied Worker</span>
                                </span>
                                <span className="text-xs font-semibold text-slate-800 block">
                                  {w.tied_vendor.company_name}
                                </span>
                              </div>
                            ) : (
                              <div>
                                <span
                                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                                    isResigned
                                      ? 'bg-purple-50 text-purple-700 border-purple-200'
                                      : 'bg-blue-50 text-blue-700 border-blue-200'
                                  }`}
                                >
                                  <UserCheck className="w-3 h-3" />
                                  <span>{isResigned ? 'Resigned (Solo Worker)' : 'Solo / Independent'}</span>
                                </span>
                                <span className="text-[11px] text-slate-400 block mt-0.5">
                                  {isResigned ? 'Relieved from previous vendor' : 'Independent worker'}
                                </span>
                              </div>
                            )}
                          </td>

                          <td className="px-4 py-4">
                            <div className="flex flex-wrap gap-1 max-w-xs">
                              {w.skills && w.skills.length > 0 ? (
                                w.skills.slice(0, 3).map((s, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-medium"
                                  >
                                    {s}
                                  </span>
                                ))
                              ) : (
                                <span className="text-slate-400 italic">General Technician</span>
                              )}
                              {w.skills && w.skills.length > 3 && (
                                <span className="px-1.5 py-0.5 text-slate-400 text-[10px]">
                                  +{w.skills.length - 3} more
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="px-4 py-4">
                            <div className="text-[11px] text-slate-600 flex flex-col gap-0.5">
                              {w.email && (
                                <span className="flex items-center gap-1">
                                  <Mail className="w-3 h-3 text-slate-400" />
                                  {w.email}
                                </span>
                              )}
                              {w.phone && (
                                <span className="flex items-center gap-1">
                                  <Phone className="w-3 h-3 text-slate-400" />
                                  {w.phone}
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="px-4 py-4 text-slate-600">
                            <div className="flex items-center gap-1">
                              <MapPin className="w-3.5 h-3.5 text-slate-400" />
                              <span>{w.city || '—'}</span>
                            </div>
                          </td>

                          <td className="px-5 py-4 text-right">
                            {isTied ? (
                              <button
                                type="button"
                                onClick={() => openTieModal(w)}
                                className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-700 hover:text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 px-3 py-1.5 rounded-lg transition-colors"
                              >
                                <RefreshCw className="w-3.5 h-3.5" />
                                <span>Reassign / Untie</span>
                              </button>
                            ) : (
                              <button
                                type="button"
                                onClick={() => openTieModal(w)}
                                className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-3 py-1.5 rounded-lg transition-colors"
                              >
                                <LinkIcon className="w-3.5 h-3.5" />
                                <span>Tie to Vendor</span>
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
        )}

        {/* MODAL 1: Tie / Reassign Modal */}
        {activeModalWorker && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4 relative">
              <button
                type="button"
                onClick={() => setActiveModalWorker(null)}
                className="absolute top-4 right-4 text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-3">
                <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
                  <LinkIcon className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    {activeModalWorker.workforce_type === 'TIED'
                      ? 'Reassign / Manage Vendor Tie'
                      : 'Tie Solo Worker to Vendor'}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Technician: <strong>{activeModalWorker.name}</strong> (
                    {activeModalWorker.employee_id || `#${activeModalWorker.id}`})
                  </p>
                </div>
              </div>

              {activeModalWorker.workforce_type === 'TIED' && activeModalWorker.tied_vendor && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
                  <span className="font-semibold text-slate-700 block">Current Assignment:</span>
                  <p className="text-slate-900 font-bold flex items-center gap-1.5">
                    <Building2 className="w-4 h-4 text-emerald-600" />
                    <span>{activeModalWorker.tied_vendor.company_name}</span>
                  </p>
                </div>
              )}

              <form onSubmit={handleTieWorker} className="space-y-3 pt-1">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Select Target Vendor Company *
                  </label>
                  <select
                    required
                    value={targetVendorId}
                    onChange={(e) => setTargetVendorId(e.target.value)}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="">-- Select a Vendor Business --</option>
                    {vendors.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.company_name} (ID: #{v.id} • {v.city || 'Regional'})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Engagement Model</label>
                  <select
                    value={engagementType}
                    onChange={(e) => setEngagementType(e.target.value)}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="PER_JOB">Per Job (Commission / Rate per task)</option>
                    <option value="FULL_TIME">Full Time (Retained Dedicated Staff)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Admin Assignment Notes (Optional)
                  </label>
                  <textarea
                    rows={2}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="e.g. Assigned by platform ops to cover North Hosur HVAC..."
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex items-center justify-between gap-3 pt-3 border-t border-slate-100">
                  {activeModalWorker.workforce_type === 'TIED' ? (
                    <button
                      type="button"
                      disabled={modalSubmitting}
                      onClick={handleUntieWorker}
                      className="px-3 py-2 text-xs font-bold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-lg transition-colors flex items-center gap-1"
                    >
                      <Unlink className="w-3.5 h-3.5" />
                      <span>Untie to Solo</span>
                    </button>
                  ) : (
                    <div />
                  )}

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={modalSubmitting}
                      onClick={() => setActiveModalWorker(null)}
                      className="px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={modalSubmitting || !targetVendorId}
                      className="px-4 py-2 text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
                    >
                      {modalSubmitting ? 'Saving...' : 'Confirm Tie'}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL 2: SEVO Platform Resignation & Relieving Audit Modal */}
        {selectedRelievingForAudit && (
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 relative border border-slate-100">
              <button
                type="button"
                onClick={() => setSelectedRelievingForAudit(null)}
                className="absolute top-4 right-4 text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-3">
                <div className="p-3 bg-purple-50 text-purple-700 rounded-xl">
                  <Scale className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    SEVO Platform Relieving Audit Clearance
                  </h3>
                  <p className="text-xs text-slate-500">
                    Formal multi-party clearance & Solo Worker wallet provisioning
                  </p>
                </div>
              </div>

              {/* Request Overview Card */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-slate-400 font-semibold block uppercase text-[10px]">Technician</span>
                    <span className="font-bold text-slate-800 text-sm">
                      {selectedRelievingForAudit.technician_name}
                    </span>
                    <span className="text-slate-500 block text-[11px]">
                      {selectedRelievingForAudit.technician_email}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 font-semibold block uppercase text-[10px]">Vendor Organization</span>
                    <span className="font-bold text-slate-800 text-sm">
                      {selectedRelievingForAudit.vendor_name}
                    </span>
                    <span className="text-slate-500 block text-[11px]">
                      Request #{selectedRelievingForAudit.id}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-200/80">
                  <span className="text-slate-500 font-semibold block">Resignation Reason:</span>
                  <p className="text-slate-800 font-medium mt-0.5">
                    <strong>{selectedRelievingForAudit.reason_display}</strong>
                    {selectedRelievingForAudit.resignation_notes && (
                      <span className="italic"> — "{selectedRelievingForAudit.resignation_notes}"</span>
                    )}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-200/80">
                  <span className="text-slate-500 font-semibold block">Vendor Settlement Statement:</span>
                  <p className="text-slate-700 mt-0.5 bg-white p-2 rounded border border-slate-200 text-[11px]">
                    {selectedRelievingForAudit.vendor_settlement_notes ||
                      'All dues, advances, and company equipment have been confirmed settled.'}
                  </p>
                </div>
              </div>

              {/* SEVO Platform Compliance Checklist */}
              <div className="p-3 bg-purple-50/70 border border-purple-200 rounded-xl space-y-1.5 text-xs text-purple-900">
                <span className="font-bold flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-purple-700" />
                  <span>Platform Automated Compliance Verification</span>
                </span>
                <ul className="text-[11px] space-y-1 list-disc pl-4 text-purple-800">
                  <li>Zero pending customer disputes or incomplete in-flight service requests.</li>
                  <li>All platform service commissions and billings have been reconciled.</li>
                  <li>
                    Upon approval, technician will transition to <strong>Resigned / Solo Worker</strong> and receive an individual wallet.
                  </li>
                </ul>
              </div>

              <form onSubmit={handleApprovePlatformAudit} className="space-y-3 pt-1">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    SEVO Superadmin Audit Remarks
                  </label>
                  <textarea
                    required
                    rows={2}
                    value={auditNotes}
                    onChange={(e) => setAuditNotes(e.target.value)}
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    disabled={auditSubmitting}
                    onClick={() => setSelectedRelievingForAudit(null)}
                    className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={auditSubmitting}
                    className="px-4 py-2 text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
                  >
                    <FileCheck2 className="w-4 h-4" />
                    <span>{auditSubmitting ? 'Approving Clearance...' : 'Approve Platform Audit & Clear'}</span>
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
