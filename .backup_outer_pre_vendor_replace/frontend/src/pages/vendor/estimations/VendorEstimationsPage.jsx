import React, { useState, useEffect, useCallback } from 'react';
import {
  Wind,
  Search,
  Filter,
  Calendar,
  MapPin,
  Phone,
  Clock,
  UserCheck,
  CheckCircle2,
  AlertCircle,
  Wrench,
  FileSpreadsheet,
  ChevronRight,
  RefreshCw,
  ExternalLink,
  Navigation,
  IndianRupee,
  Sparkles,
  Loader2,
  Send,
  Eye,
} from 'lucide-react';
import { AppShell } from '../../../components/common/AppShell.jsx';
import {
  apiGetVendorEstimations,
  apiGetVendorEstimationDetail,
  apiConfirmVendorEstimation,
  apiStartJourney,
  apiMarkArrived,
} from '../../../api/vendorEstimationService.js';
import TechnicianAssignModal from '../../../components/vendor/TechnicianAssignModal.jsx';
import OtpVerifyModal from '../../../components/vendor/OtpVerifyModal.jsx';
import TechnicianInspectionSheet from '../../../components/vendor/TechnicianInspectionSheet.jsx';
import VendorQuotationBuilder from '../../../components/vendor/VendorQuotationBuilder.jsx';
import CustomerDecisionPanel from '../../../components/vendor/CustomerDecisionPanel.jsx';
import FeeActionModal from '../../../components/vendor/FeeActionModal.jsx';

const FILTER_TABS = [
  { id: 'all', label: 'All Leads' },
  { id: 'requested', label: 'New Requests' },
  { id: 'assigned', label: 'Assigned' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'quotation_sent', label: 'Quotation Sent' },
  { id: 'completed', label: 'Completed' },
];

const STATUS_BADGES = {
  REQUESTED: 'bg-blue-50 text-blue-700 border-blue-200',
  VENDOR_CONFIRMED: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  TECHNICIAN_ASSIGNED: 'bg-purple-50 text-purple-700 border-purple-200',
  TECHNICIAN_ON_THE_WAY: 'bg-amber-50 text-amber-700 border-amber-200',
  TECHNICIAN_ARRIVED: 'bg-orange-50 text-orange-700 border-orange-200',
  INSPECTION_IN_PROGRESS: 'bg-teal-50 text-teal-700 border-teal-200',
  INSPECTION_COMPLETED: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  QUOTATION_SENT: 'bg-sky-50 text-sky-700 border-sky-200',
  CUSTOMER_APPROVED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  CUSTOMER_REJECTED: 'bg-rose-50 text-rose-700 border-rose-200',
  COMPLETED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  CANCELLED: 'bg-zinc-100 text-zinc-600 border-zinc-200',
};

export default function VendorEstimationsPage() {
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [leads, setLeads] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected lead for detail / modal actions
  const [selectedLead, setSelectedLead] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Action Modals State
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [otpModalOpen, setOtpModalOpen] = useState(false);
  const [inspectionModalOpen, setInspectionModalOpen] = useState(false);
  const [quotationModalOpen, setQuotationModalOpen] = useState(false);
  const [feeModalOpen, setFeeModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGetVendorEstimations({
        status: activeTab,
        date: dateFilter || undefined,
        search: searchQuery || undefined,
      });
      // Response format: { results: [...], metrics: {...} }
      if (res?.results) {
        setLeads(res.results);
        setMetrics(res.metrics || null);
      } else if (Array.isArray(res)) {
        setLeads(res);
      } else {
        setLeads([]);
      }
    } catch (err) {
      console.error('Failed to load estimation leads:', err);
      setError(err.message || 'Failed to load estimation leads.');
    } finally {
      setLoading(false);
    }
  }, [activeTab, dateFilter, searchQuery]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  const handleOpenDetail = async (lead) => {
    setSelectedLead(lead);
    setDetailLoading(true);
    try {
      const full = await apiGetVendorEstimationDetail(lead.id);
      setSelectedLead(full);
    } catch (err) {
      console.warn('Could not fetch full lead details:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const refreshSelectedDetail = async () => {
    if (!selectedLead?.id) return;
    try {
      const full = await apiGetVendorEstimationDetail(selectedLead.id);
      setSelectedLead(full);
      fetchLeads();
    } catch (err) {
      console.warn('Failed to refresh lead detail:', err);
    }
  };

  // State Machine CTA handlers
  const handleConfirmLead = async () => {
    if (!selectedLead?.id) return;
    setActionLoading(true);
    try {
      const res = await apiConfirmVendorEstimation(selectedLead.id);
      setSelectedLead(res?.data || res);
      fetchLeads();
    } catch (err) {
      alert(err.message || 'Failed to confirm lead.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartTrip = async () => {
    if (!selectedLead?.id) return;
    setActionLoading(true);
    try {
      const res = await apiStartJourney(selectedLead.id);
      setSelectedLead(res?.data || res);
      fetchLeads();
    } catch (err) {
      alert(err.message || 'Failed to start trip.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleMarkArrived = async () => {
    if (!selectedLead?.id) return;
    setActionLoading(true);
    try {
      const res = await apiMarkArrived(selectedLead.id);
      setSelectedLead(res?.data || res);
      fetchLeads();
    } catch (err) {
      alert(err.message || 'Failed to mark arrival.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <AppShell
      breadcrumbs={[
        { label: 'Operations', to: '/workforce/admin/jobs' },
        { label: 'AC Inspection & Estimation' },
      ]}
    >
      <div className="max-w-7xl mx-auto space-y-6 text-xs select-none">
        {/* Top Header & Metrics Banner */}
        <div className="bg-white p-5 rounded-2xl border border-zinc-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow-md">
              <Wind className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base sm:text-lg font-black text-zinc-900 tracking-tight">
                  AC Inspection & Quotation Manager
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                  Vendor Portal
                </span>
              </div>
              <p className="text-xs text-zinc-500 mt-0.5">
                Manage AC diagnostic leads, on-site technician inspections, and formal versioned quotations.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              onClick={fetchLeads}
              disabled={loading}
              className="px-3.5 py-2 rounded-xl bg-zinc-100 hover:bg-zinc-200 text-zinc-700 font-semibold flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Metrics Row */}
        {metrics && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: 'Total Leads', val: metrics.all, color: 'text-zinc-900', bg: 'bg-zinc-50' },
              { label: 'New Requests', val: metrics.requested, color: 'text-blue-600', bg: 'bg-blue-50/50' },
              { label: 'Assigned', val: metrics.assigned, color: 'text-purple-600', bg: 'bg-purple-50/50' },
              { label: 'In Progress', val: metrics.in_progress, color: 'text-amber-600', bg: 'bg-amber-50/50' },
              { label: 'Quotes Sent', val: metrics.quotation_sent, color: 'text-sky-600', bg: 'bg-sky-50/50' },
              { label: 'Completed', val: metrics.completed, color: 'text-emerald-600', bg: 'bg-emerald-50/50' },
            ].map((m, idx) => (
              <div key={idx} className={`p-3 rounded-xl border border-zinc-200/80 ${m.bg} shadow-xs`}>
                <span className="text-[11px] font-medium text-zinc-500 block truncate">{m.label}</span>
                <span className={`text-lg font-black font-mono ${m.color}`}>{m.val}</span>
              </div>
            ))}
          </div>
        )}

        {/* Filters and Search Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-zinc-200 shadow-xs">
          {/* Filter Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                  activeTab === tab.id
                    ? 'bg-zinc-900 text-white shadow-xs'
                    : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search & Date Filter */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1 md:w-56">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search customer, ID, brand..."
                className="w-full text-xs pl-8 pr-3 py-1.5 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
              />
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-2" />
            </div>

            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="text-xs px-2.5 py-1.5 border border-zinc-200 rounded-lg bg-white"
            />
            {dateFilter && (
              <button
                onClick={() => setDateFilter('')}
                className="text-zinc-400 hover:text-zinc-600 text-xs font-bold"
                title="Clear date"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2.5 text-red-700">
            <AlertCircle className="w-5 h-5 shrink-0 text-red-500" />
            <span className="font-medium">{error}</span>
          </div>
        )}

        {/* Leads Grid */}
        {loading ? (
          <div className="p-16 text-center bg-white rounded-2xl border border-zinc-200">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-3" />
            <p className="text-xs font-semibold text-zinc-600">Loading estimation leads...</p>
          </div>
        ) : leads.length === 0 ? (
          <div className="p-16 text-center bg-white rounded-2xl border border-zinc-200 space-y-3">
            <Wind className="w-10 h-10 text-zinc-300 mx-auto" />
            <h3 className="text-sm font-bold text-zinc-700">No Estimation Leads Found</h3>
            <p className="text-xs text-zinc-400 max-w-sm mx-auto">
              No matching AC inspection requests found for current filter criteria.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {leads.map((lead) => {
              const statusPill = STATUS_BADGES[lead.status] || STATUS_BADGES.REQUESTED;
              const isPendingConfirm = lead.status === 'REQUESTED' || lead.sr_status === 'requested';
              const feeStatus = lead.fee?.status || 'PENDING';

              return (
                <div
                  key={lead.id}
                  onClick={() => handleOpenDetail(lead)}
                  className="bg-white rounded-2xl border border-zinc-200 hover:border-blue-300 hover:shadow-md transition-all p-4 flex flex-col justify-between cursor-pointer group"
                >
                  <div className="space-y-3">
                    {/* Card Header: Job ID & Status Badge */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-zinc-900 text-xs">
                          {lead.request_id || `#${lead.id}`}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase border bg-zinc-50 text-zinc-600">
                          {lead.ac_details?.ac_type || 'AC'}
                        </span>
                      </div>
                      <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase border ${statusPill}`}>
                        {lead.status.replace(/_/g, ' ')}
                      </span>
                    </div>

                    {/* AC Specification & Brand */}
                    <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-100 flex items-center justify-between">
                      <div>
                        <h4 className="text-xs font-bold text-zinc-900">
                          {lead.ac_details?.ac_brand} {lead.ac_details?.ac_type}
                        </h4>
                        <span className="text-[11px] text-zinc-500">
                          Capacity: {lead.ac_details?.ac_capacity?.replace(/_/g, ' ') || '1.5 Ton'} • Qty: {lead.ac_details?.ac_quantity || 1}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase block">Visit Fee</span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                            feeStatus === 'COLLECTED'
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : feeStatus === 'WAIVED'
                              ? 'bg-purple-50 text-purple-700 border-purple-200'
                              : 'bg-amber-50 text-amber-700 border-amber-200'
                          }`}
                        >
                          ₹199 {feeStatus}
                        </span>
                      </div>
                    </div>

                    {/* Symptoms / Customer Notes */}
                    <p className="text-xs text-zinc-600 line-clamp-2 leading-relaxed">
                      "{lead.ac_details?.customer_symptom || 'General cooling inspection and checkup'}"
                    </p>

                    {/* Customer Location & Schedule */}
                    <div className="space-y-1.5 pt-1 text-zinc-500">
                      <div className="flex items-center gap-2 truncate">
                        <MapPin className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                        <span className="truncate">{lead.address || 'Address on file'}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                        <span>
                          {lead.preferred_date ? new Date(lead.preferred_date).toLocaleDateString() : 'Today'} • {lead.preferred_time || 'Morning'}
                        </span>
                      </div>
                      {lead.technician?.name && (
                        <div className="flex items-center gap-2 text-zinc-700 font-medium">
                          <UserCheck className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                          <span>Tech: {lead.technician.name}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Action Footer */}
                  <div className="pt-3 mt-3 border-t border-zinc-100 flex items-center justify-between">
                    <span className="text-zinc-500 font-medium">
                      Customer: <strong className="text-zinc-800">{lead.customer_name}</strong>
                    </span>
                    <button
                      type="button"
                      className="text-blue-600 group-hover:text-blue-700 font-bold flex items-center gap-1"
                    >
                      <span>Manage Job</span>
                      <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Estimation Detail & Action Modal Drawer */}
        {selectedLead && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-zinc-950/70 backdrop-blur-xs animate-in fade-in overflow-y-auto">
            <div className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl border border-zinc-200 overflow-hidden my-auto max-h-[94vh] flex flex-col">
              {/* Modal Header */}
              <div className="px-6 py-4 border-b border-zinc-100 bg-zinc-50 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
                    <Wind className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-sm sm:text-base font-black text-zinc-900">
                        Lead #{selectedLead.request_id || selectedLead.id}
                      </h2>
                      <span
                        className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase border ${
                          STATUS_BADGES[selectedLead.status] || STATUS_BADGES.REQUESTED
                        }`}
                      >
                        {selectedLead.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-500">
                      AC Inspection & Estimation Management Console
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setSelectedLead(null)}
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Modal Scrollable Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Primary Dynamic State CTA Banner */}
                <div className="p-4 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 rounded-2xl border border-blue-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
                  <div>
                    <span className="text-[10px] font-black uppercase tracking-wider text-blue-700 block">
                      Current Operational Stage
                    </span>
                    <h3 className="text-sm font-bold text-zinc-900 mt-0.5">
                      {selectedLead.status === 'REQUESTED'
                        ? 'New Lead Unconfirmed — Vendor Acceptance Required'
                        : selectedLead.status === 'VENDOR_CONFIRMED'
                        ? 'Confirmed — Assign On-site Field Technician'
                        : selectedLead.status === 'TECHNICIAN_ASSIGNED'
                        ? `Technician ${selectedLead.technician?.name || ''} Assigned — Ready for Journey`
                        : selectedLead.status === 'TECHNICIAN_ON_THE_WAY'
                        ? 'Technician In Transit to Customer Location'
                        : selectedLead.status === 'TECHNICIAN_ARRIVED'
                        ? 'Technician Arrived at Site — Customer Start OTP Required'
                        : selectedLead.status === 'INSPECTION_IN_PROGRESS'
                        ? 'Inspection In Progress — Record Structured Defect Findings'
                        : selectedLead.status === 'INSPECTION_COMPLETED'
                        ? 'Inspection Completed — Draft and Send Formal Quotation'
                        : selectedLead.status === 'QUOTATION_SENT'
                        ? 'Formal Quotation Sent — Awaiting Customer Approval'
                        : selectedLead.status === 'CUSTOMER_APPROVED'
                        ? 'Customer Approved — Collect Visit Fee & Commencing Work'
                        : selectedLead.status === 'CUSTOMER_REJECTED'
                        ? 'Customer Rejected Quote — Revise Pricing & Resend'
                        : 'Job Lifecycle Active'}
                    </h3>
                  </div>

                  {/* Progressive CTA Button */}
                  <div className="shrink-0 flex items-center gap-2">
                    {selectedLead.status === 'REQUESTED' && (
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={handleConfirmLead}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5 transition-colors"
                      >
                        {actionLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                        <span>Accept Lead</span>
                      </button>
                    )}

                    {selectedLead.status === 'VENDOR_CONFIRMED' && (
                      <button
                        type="button"
                        onClick={() => setAssignModalOpen(true)}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5 transition-colors"
                      >
                        <UserCheck className="w-3.5 h-3.5" />
                        <span>Assign Technician</span>
                      </button>
                    )}

                    {selectedLead.status === 'TECHNICIAN_ASSIGNED' && (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setAssignModalOpen(true)}
                          className="px-3 py-2 bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-700 font-semibold text-xs rounded-xl"
                        >
                          Reassign
                        </button>
                        <button
                          type="button"
                          disabled={actionLoading}
                          onClick={handleStartTrip}
                          className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5"
                        >
                          <Navigation className="w-3.5 h-3.5" />
                          <span>Start Trip</span>
                        </button>
                      </div>
                    )}

                    {selectedLead.status === 'TECHNICIAN_ON_THE_WAY' && (
                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={handleMarkArrived}
                        className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5"
                      >
                        <MapPin className="w-3.5 h-3.5" />
                        <span>Mark Arrived</span>
                      </button>
                    )}

                    {selectedLead.status === 'TECHNICIAN_ARRIVED' && (
                      <button
                        type="button"
                        onClick={() => setOtpModalOpen(true)}
                        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Enter Customer Start OTP</span>
                      </button>
                    )}

                    {selectedLead.status === 'INSPECTION_IN_PROGRESS' && (
                      <button
                        type="button"
                        onClick={() => setInspectionModalOpen(true)}
                        className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5"
                      >
                        <Wrench className="w-3.5 h-3.5" />
                        <span>Open Inspection Sheet</span>
                      </button>
                    )}

                    {selectedLead.status === 'INSPECTION_COMPLETED' && (
                      <button
                        type="button"
                        onClick={() => setQuotationModalOpen(true)}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5"
                      >
                        <FileSpreadsheet className="w-3.5 h-3.5" />
                        <span>Create Quotation</span>
                      </button>
                    )}

                    {['QUOTATION_SENT', 'CUSTOMER_APPROVED', 'CUSTOMER_REJECTED'].includes(selectedLead.status) && (
                      <button
                        type="button"
                        onClick={() => setQuotationModalOpen(true)}
                        className="px-3 py-2 bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-800 font-bold text-xs rounded-xl flex items-center gap-1.5"
                      >
                        <FileSpreadsheet className="w-3.5 h-3.5 text-blue-600" />
                        <span>View / Edit Quote</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Customer Contact & Navigation Card */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Customer Card */}
                  <div className="p-4 bg-zinc-50 rounded-2xl border border-zinc-200 space-y-3">
                    <span className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider block">
                      Customer Contact Information
                    </span>
                    <div>
                      <h4 className="text-sm font-bold text-zinc-900">{selectedLead.customer_name}</h4>
                      <p className="text-xs text-zinc-500">{selectedLead.phone} • {selectedLead.email || 'No email'}</p>
                    </div>
                    <div className="flex items-center gap-2 pt-1">
                      <a
                        href={`tel:${selectedLead.phone}`}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg flex items-center gap-1.5 shadow-xs"
                      >
                        <Phone className="w-3.5 h-3.5" />
                        <span>Call Customer</span>
                      </a>
                      {selectedLead.address && (
                        <a
                          href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                            selectedLead.address
                          )}`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-3 py-1.5 bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-700 font-bold text-xs rounded-lg flex items-center gap-1.5 shadow-xs"
                        >
                          <Navigation className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Google Maps</span>
                        </a>
                      )}
                    </div>
                  </div>

                  {/* AC Specifications Card */}
                  <div className="p-4 bg-zinc-50 rounded-2xl border border-zinc-200 space-y-3">
                    <span className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider block">
                      Air Conditioner Specifications
                    </span>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-[10px] text-zinc-400 block font-semibold">Brand</span>
                        <strong className="text-zinc-900">{selectedLead.ac_details?.ac_brand}</strong>
                      </div>
                      <div>
                        <span className="text-[10px] text-zinc-400 block font-semibold">Type</span>
                        <strong className="text-zinc-900">{selectedLead.ac_details?.ac_type}</strong>
                      </div>
                      <div>
                        <span className="text-[10px] text-zinc-400 block font-semibold">Capacity</span>
                        <strong className="text-zinc-900">{selectedLead.ac_details?.ac_capacity?.replace(/_/g, ' ')}</strong>
                      </div>
                      <div>
                        <span className="text-[10px] text-zinc-400 block font-semibold">Units</span>
                        <strong className="text-zinc-900">{selectedLead.ac_details?.ac_quantity || 1}</strong>
                      </div>
                    </div>
                    {selectedLead.ac_details?.customer_symptom && (
                      <p className="text-[11px] text-zinc-600 italic bg-white p-2 rounded-lg border border-zinc-100">
                        "{selectedLead.ac_details.customer_symptom}"
                      </p>
                    )}
                  </div>
                </div>

                {/* Customer Decision & Visit Fee Component */}
                <CustomerDecisionPanel
                  estimation={selectedLead}
                  onReviseQuote={() => setQuotationModalOpen(true)}
                  onOpenFeeModal={() => setFeeModalOpen(true)}
                  onUpdate={refreshSelectedDetail}
                />

                {/* Inspection Findings Section */}
                {selectedLead.findings && selectedLead.findings.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-zinc-900 uppercase tracking-wider">
                        Inspection Findings ({selectedLead.findings.length})
                      </span>
                      <button
                        type="button"
                        onClick={() => setInspectionModalOpen(true)}
                        className="text-blue-600 font-bold text-xs hover:underline"
                      >
                        Edit Findings
                      </button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {selectedLead.findings.map((f, fIdx) => (
                        <div key={fIdx} className="p-3 bg-white border border-zinc-200 rounded-xl space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-zinc-900 text-xs">{f.title}</span>
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700">
                              {f.severity}
                            </span>
                          </div>
                          <p className="text-[11px] text-zinc-600">{f.description}</p>
                          {f.recommended_action && (
                            <p className="text-[11px] text-blue-700 font-medium">
                              Fix: {f.recommended_action}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-4 border-t border-zinc-100 bg-zinc-50 flex items-center justify-between shrink-0">
                <span className="text-[11px] text-zinc-400">
                  Lead Created: {selectedLead.created_at ? new Date(selectedLead.created_at).toLocaleString() : ''}
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedLead(null)}
                  className="px-4 py-1.5 text-xs font-semibold text-zinc-600 hover:bg-zinc-200 rounded-xl transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Child Workflow Modals */}
        <TechnicianAssignModal
          estimation={selectedLead}
          isOpen={assignModalOpen}
          onClose={() => setAssignModalOpen(false)}
          onSuccess={refreshSelectedDetail}
        />

        <OtpVerifyModal
          estimation={selectedLead}
          isOpen={otpModalOpen}
          onClose={() => setOtpModalOpen(false)}
          onSuccess={refreshSelectedDetail}
        />

        <TechnicianInspectionSheet
          estimation={selectedLead}
          isOpen={inspectionModalOpen}
          onClose={() => setInspectionModalOpen(false)}
          onComplete={refreshSelectedDetail}
        />

        <VendorQuotationBuilder
          estimation={selectedLead}
          isOpen={quotationModalOpen}
          onClose={() => setQuotationModalOpen(false)}
          onQuotationSent={refreshSelectedDetail}
        />

        <FeeActionModal
          estimation={selectedLead}
          isOpen={feeModalOpen}
          onClose={() => setFeeModalOpen(false)}
          onSuccess={refreshSelectedDetail}
        />
      </div>
    </AppShell>
  );
}
