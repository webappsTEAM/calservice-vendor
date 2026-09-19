/**
 * AdminDispatchRadar.jsx
 *
 * CalTrack Super Admin Dispatch Radar V2 — Read-Only Observability & Control Tower.
 *
 * Visualizes how customer bookings travel through the technician dispatch pipeline:
 *  - Compact metric overview strip (Active, Searching, Offered, Assigned, En Route, In Progress, Completed Today)
 *  - Filterable active jobs queue with search & compact rows (60-75px high)
 *  - Selected Job Header with inline telemetry and unambiguous technician identities (EMP #ID)
 *  - Single Unified DISPATCH JOURNEY (Primary Visual connecting Booking -> Search -> Offer -> Decision -> Assignment)
 *  - Multi-Attempt Selector & Immutable Candidate Snapshot (first 5 + expandable)
 *  - Live countdown timers on active offers
 *  - Realtime SSE reconciliation with zero dispatch side effects
 *
 * THEME: Strictly aligned with the clean, light CalTrack Admin Operations visual system.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { apiGetDispatchRadar } from '../../api/workforceService.js';
import {
  Radio,
  Clock,
  CheckCircle2,
  AlertCircle,
  Users,
  MapPin,
  Sparkles,
  Search,
  Filter,
  Activity,
  UserCheck,
  Timer,
  Info,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Check,
  X,
} from 'lucide-react';

export function AdminDispatchRadar() {
  const [data, setData] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedAttemptIndex, setSelectedAttemptIndex] = useState(0);
  const [isCandidatesExpanded, setIsCandidatesExpanded] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [nowTs, setNowTs] = useState(Date.now());

  // Live second clock for countdown timer calculations
  useEffect(() => {
    const timer = setInterval(() => setNowTs(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch Radar data (Strictly READ-ONLY)
  const fetchRadar = useCallback(async (jobIdToSelect = null, isSilent = false) => {
    try {
      if (!isSilent) setIsRefreshing(true);
      setError(null);
      const res = await apiGetDispatchRadar({
        jobId: jobIdToSelect || selectedJobId,
        status: statusFilter,
        search: searchQuery,
      });
      setData(res);
      if (res?.selected_job?.id) {
        setSelectedJobId(res.selected_job.id);
      } else if (res?.jobs?.length > 0 && !selectedJobId) {
        setSelectedJobId(res.jobs[0].id);
      }
    } catch (err) {
      console.error('[RADAR_FETCH_ERROR]', err);
      setError(err.message || 'Failed to load dispatch radar telemetry.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [selectedJobId, statusFilter, searchQuery]);

  // Initial load & when filters change
  useEffect(() => {
    fetchRadar(null, false);
  }, [statusFilter, searchQuery]);

  // Reset attempt index when selecting a new job
  const handleSelectJob = (id) => {
    setSelectedJobId(id);
    setSelectedAttemptIndex(0);
    setIsCandidatesExpanded(false);
    fetchRadar(id, true);
  };

  // Realtime SSE Event Listener (debounced/coalesced)
  useEffect(() => {
    let debounceTimer = null;

    const handleRealtimeEvent = (e) => {
      const detail = e?.detail || {};
      const evType = detail.event_type || detail.type || '';
      const relevantEvents = [
        'DISPATCH_STARTED',
        'CANDIDATES_EVALUATED',
        'OFFER_CREATED',
        'OFFER_REJECTED',
        'OFFER_ACCEPTED',
        'EMPLOYEE_JOB_DECLINED',
        'EMPLOYEE_JOB_ACCEPTED',
        'EMPLOYEE_JOB_CANCELLED',
        'DISPATCH_UNASSIGNED_REASON',
        'technician.assigned',
      ];

      if (relevantEvents.some((rev) => evType.includes(rev) || rev.includes(evType))) {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          fetchRadar(null, true);
        }, 800);
      }
    };

    window.addEventListener('workforce_event', handleRealtimeEvent);
    return () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      window.removeEventListener('workforce_event', handleRealtimeEvent);
    };
  }, [fetchRadar]);

  // Authoritative global metrics from backend summary
  const summary = data?.summary || {
    total_active: 0,
    searching: 0,
    offered: 0,
    assigned: 0,
    en_route: 0,
    in_progress: 0,
    completed_today: 0,
  };

  const jobsList = data?.jobs || [];
  const selectedJob = data?.selected_job || null;

  // Format seconds remaining countdown
  const formatRemainingTime = (expiresAtIso) => {
    if (!expiresAtIso) return '00:00';
    const diffMs = new Date(expiresAtIso).getTime() - nowTs;
    if (diffMs <= 0) return 'Expired';
    const totalSec = Math.floor(diffMs / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m < 10 ? '0' + m : m}:${s < 10 ? '0' + s : s}`;
  };

  // Status badge styling helper aligned with CalTrack light palette
  const getStatusBadgeClass = (st) => {
    const s = (st || '').toUpperCase();
    if (s.includes('OFFER')) return 'bg-amber-50 text-amber-700 border-amber-200';
    if (s.includes('SEARCH') || s.includes('DISPATCH') || s.includes('RETRY') || s.includes('WAITING')) return 'bg-sky-50 text-sky-700 border-sky-200';
    if (s.includes('ASSIGN') || s.includes('ACCEPT')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (s.includes('ROUTE') || s.includes('WAY')) return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    if (s.includes('PROGRESS') || s.includes('ARRIV')) return 'bg-purple-50 text-purple-700 border-purple-200';
    if (s.includes('COMPLET')) return 'bg-emerald-50 text-emerald-800 border-emerald-300';
    if (s.includes('DECLIN') || s.includes('CANCEL') || s.includes('FAIL') || s.includes('EXPIRE') || s.includes('SUPERSEDED')) return 'bg-rose-50 text-rose-700 border-rose-200';
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  // Normalization for display
  const normalizeStatusText = (st) => {
    if (!st) return 'NEVER ATTEMPTED';
    const s = st.toUpperCase();
    if (s === 'OFFER_ACTIVE') return 'OFFERED';
    if (s === 'DISPATCHING') return 'SEARCHING';
    if (s === 'RETRY_SCHEDULED') return 'RETRYING';
    if (s === 'NEVER_ATTEMPTED') return 'SEARCHING';
    return s.replace(/_/g, ' ');
  };

  // Extract attempts and current candidate snapshot
  const attempts = selectedJob?.attempts || [];
  const currentAttempt = attempts[selectedAttemptIndex] || attempts[0] || null;
  const currentCandidates = currentAttempt?.candidates || selectedJob?.candidate_evaluations || [];
  const displayedCandidates = isCandidatesExpanded ? currentCandidates : currentCandidates.slice(0, 5);

  return (
    <div className="space-y-4">
      {/* ─── Compact Top Metric Strip (Slim rectangular pills) ───────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Active</span>
            <span className="text-lg font-black text-slate-900">{summary.total_active}</span>
          </div>
          <Activity className="w-4 h-4 text-blue-600" />
        </div>

        <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Searching</span>
            <span className="text-lg font-black text-sky-600">{summary.searching}</span>
          </div>
          <Radio className="w-4 h-4 text-sky-500 animate-pulse" />
        </div>

        <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Offered</span>
            <span className="text-lg font-black text-amber-600">{summary.offered}</span>
          </div>
          <Timer className="w-4 h-4 text-amber-500" />
        </div>

        <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Assigned</span>
            <span className="text-lg font-black text-emerald-600">{summary.assigned}</span>
          </div>
          <UserCheck className="w-4 h-4 text-emerald-600" />
        </div>

        <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">En Route</span>
            <span className="text-lg font-black text-indigo-600">{summary.en_route}</span>
          </div>
          <MapPin className="w-4 h-4 text-indigo-600" />
        </div>

        <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 flex items-center justify-between shadow-xs">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">In Progress</span>
            <span className="text-lg font-black text-purple-600">{summary.in_progress}</span>
          </div>
          <Sparkles className="w-4 h-4 text-purple-600" />
        </div>

        <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 flex items-center justify-between shadow-xs col-span-2 sm:col-span-4 lg:col-span-1">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Completed</span>
            <span className="text-lg font-black text-slate-900">{summary.completed_today}</span>
          </div>
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
        </div>
      </div>

      {/* ─── Control Bar: Filters, Search, and Refresh ───────────────────────── */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-1">
          {[
            { key: 'all', label: 'All Jobs' },
            { key: 'offered', label: 'Offered' },
            { key: 'searching', label: 'Searching' },
            { key: 'assigned', label: 'Assigned' },
            { key: 'en_route', label: 'En Route' },
            { key: 'in_progress', label: 'In Progress' },
            { key: 'completed', label: 'Completed' },
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setStatusFilter(tab.key)}
              className={`px-2.5 py-1 rounded-md text-xs font-bold transition-colors ${
                statusFilter === tab.key
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-60">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by Job #, Service, Tech..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-md pl-7 pr-2.5 py-1 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            type="button"
            onClick={() => fetchRadar(null, false)}
            disabled={isRefreshing}
            className="p-1.5 bg-white hover:bg-slate-100 border border-slate-200 text-slate-600 hover:text-slate-900 rounded-md transition-colors disabled:opacity-50"
            title="Refresh Telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* ─── API Error State ─────────────────────────────────────────────────── */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-center">
          <AlertCircle className="w-6 h-6 text-rose-500 mx-auto mb-1.5" />
          <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wide">DISPATCH RADAR UNAVAILABLE</h4>
          <p className="text-[11px] text-rose-700 mt-0.5">{error}</p>
          <button
            type="button"
            onClick={() => fetchRadar(null, false)}
            className="mt-2 px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-bold shadow-xs inline-flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Radar Telemetry</span>
          </button>
        </div>
      )}

      {/* ─── Main Radar Grid (2 Columns: Active Queue ~35% & Selected Job Control Tower ~65%) ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left Column: Active Dispatch Queue (~35%) */}
        <div className="lg:col-span-4 space-y-2">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Active Queue</span>
              <span className="px-1.5 py-0.2 bg-slate-100 text-slate-600 border border-slate-200 rounded text-[10px] font-bold">
                {jobsList.length}
              </span>
            </div>
            <span className="text-[10px] text-slate-400">Read-Only Telemetry</span>
          </div>

          {isLoading ? (
            <div className="bg-white border border-slate-200 rounded-lg p-8 flex flex-col items-center justify-center text-center gap-2 shadow-xs">
              <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
              <p className="text-xs font-semibold text-slate-600">Streaming dispatch telemetry...</p>
            </div>
          ) : jobsList.length === 0 ? (
            statusFilter === 'all' && !searchQuery ? (
              <div className="bg-white border border-slate-200 rounded-lg p-6 text-center shadow-xs">
                <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-1.5" />
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">NO ACTIVE DISPATCH JOBS</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  No bookings are currently in an active dispatch state.
                </p>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded-lg p-6 text-center shadow-xs">
                <Filter className="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">NO MATCHING JOBS</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  No active jobs match the selected filter.
                </p>
                <button
                  type="button"
                  onClick={() => { setStatusFilter('all'); setSearchQuery(''); }}
                  className="mt-2 px-2.5 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold"
                >
                  Reset Filters
                </button>
              </div>
            )
          ) : (
            <div className="space-y-1.5 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
              {jobsList.map((job) => {
                const isSelected = selectedJob?.id === job.id;
                const hasActiveOffer = !!job.current_offer;
                const statusLabel = hasActiveOffer ? 'OFFERED' : normalizeStatusText(job.dispatch_status || job.status);

                return (
                  <div
                    key={job.id}
                    onClick={() => handleSelectJob(job.id)}
                    className={`cursor-pointer rounded-lg p-2.5 transition-all duration-150 border text-xs ${
                      isSelected
                        ? 'bg-blue-50/80 border-blue-500 ring-1 ring-blue-500/30 shadow-xs'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/70 shadow-xs'
                    }`}
                  >
                    {/* Top line: Job # + Status badge + optional Timer */}
                    <div className="flex items-center justify-between gap-1.5">
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="font-black text-slate-900">
                          #{job.request_id || job.id}
                        </span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[9px] font-bold border uppercase ${getStatusBadgeClass(
                            statusLabel
                          )}`}
                        >
                          {statusLabel}
                        </span>
                      </div>

                      {hasActiveOffer && (
                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.2 bg-amber-50 border border-amber-200 text-amber-700 rounded text-[10px] font-mono font-bold shrink-0">
                          <Clock className="w-2.5 h-2.5" />
                          {formatRemainingTime(job.current_offer.expires_at)}
                        </span>
                      )}
                    </div>

                    {/* Middle line: Service Title */}
                    <div className="font-semibold text-slate-700 truncate mt-1">
                      {job.service}
                    </div>

                    {/* Bottom line: Recipient tech (EMP #ID) / Assignee / Attempt count */}
                    <div className="mt-1 pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
                      {hasActiveOffer ? (
                        <span className="text-amber-700 font-semibold truncate">
                          → {job.current_offer.employee_name} ({job.current_offer.score} pts)
                        </span>
                      ) : job.assigned_technician_name ? (
                        <span className="text-emerald-700 font-semibold truncate flex items-center gap-1">
                          <Check className="w-3 h-3 text-emerald-600" />
                          <span>{job.assigned_technician_name}</span>
                        </span>
                      ) : (
                        <span className="text-slate-400 font-mono">
                          Attempt #{job.attempt_count || 1}
                        </span>
                      )}

                      <span className="text-slate-400 truncate max-w-[120px]">
                        {job.customer_name}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Job Control Tower (~65%) */}
        <div className="lg:col-span-8 space-y-3">
          {!selectedJob ? (
            <div className="bg-white border border-slate-200 rounded-lg p-10 text-center shadow-xs">
              <Radio className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Select a Job from the Queue</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Choose an active booking on the left to inspect its live offer status, dispatch journey, and candidate evaluations.
              </p>
            </div>
          ) : (
            <>
              {/* 1. Compact Selected Job Header */}
              <div className="bg-white border border-slate-200 rounded-lg p-3.5 shadow-xs space-y-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-sm font-black text-slate-900">
                        JOB #{selectedJob.request_id || selectedJob.id}
                      </h2>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getStatusBadgeClass(
                          selectedJob.current_offer ? 'OFFERED' : selectedJob.dispatch_status || selectedJob.status
                        )}`}
                      >
                        {selectedJob.current_offer ? 'OFFERED' : normalizeStatusText(selectedJob.dispatch_status || selectedJob.status)}
                      </span>
                    </div>
                    <p className="text-xs font-bold text-blue-700 mt-0.5">{selectedJob.service}</p>
                  </div>

                  <div className="text-right text-[11px] text-slate-500">
                    <div>
                      Scheduled:{' '}
                      <span className="font-bold text-slate-800">
                        {selectedJob.scheduled_date || 'Today'} {selectedJob.scheduled_time || ''}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.2">
                      Booked: {selectedJob.created_at ? new Date(selectedJob.created_at).toLocaleTimeString() : 'N/A'}
                    </div>
                  </div>
                </div>

                {/* Inline Live Offer / Assignment / Holding Info Banner */}
                <div className="bg-slate-50 border border-slate-200 rounded-md p-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                  {selectedJob.current_offer ? (
                    <>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                        <span className="text-[11px] font-bold text-amber-900">
                          Active Offer → {selectedJob.current_offer.employee_name}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          ({selectedJob.current_offer.score} pts)
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-slate-500">Expires in:</span>
                        <span className="px-1.5 py-0.2 bg-amber-100 border border-amber-300 text-amber-800 rounded font-mono font-bold text-[11px]">
                          {formatRemainingTime(selectedJob.current_offer.expires_at)}
                        </span>
                      </div>
                    </>
                  ) : selectedJob.assigned_technician_name ? (
                    <div className="flex items-center gap-1.5 text-emerald-800 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Assigned: {selectedJob.assigned_technician_name}</span>
                    </div>
                  ) : (
                    <div className="text-slate-600 flex items-center gap-1.5 text-[11px]">
                      <Info className="w-3.5 h-3.5 text-slate-400" />
                      <span>
                        {selectedJob.unassigned_reason_message || 'Awaiting candidate ranking or retry schedule.'}
                      </span>
                    </div>
                  )}
                </div>

                {/* Compact Customer & Location Line */}
                <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100 gap-2">
                  <div className="flex items-center gap-1 truncate max-w-sm">
                    <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                    <span className="truncate">{selectedJob.address || 'Textual address not specified'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Customer:</span>{' '}
                    <span className="font-semibold text-slate-700">{selectedJob.customer_name}</span>
                  </div>
                </div>
              </div>

              {/* 2. Primary Visual: Unified DISPATCH JOURNEY Timeline */}
              <div className="bg-white border border-slate-200 rounded-lg p-3.5 shadow-xs space-y-2.5">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <div className="flex items-center gap-1.5">
                    <Activity className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Dispatch Journey
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {selectedJob.timeline ? `${selectedJob.timeline.length} events` : '0 events'}
                  </span>
                </div>

                {selectedJob.timeline && selectedJob.timeline.length > 0 ? (
                  <div className="space-y-2 relative pl-4 border-l-2 border-slate-200 my-1 ml-2">
                    {selectedJob.timeline.map((ev, idx) => {
                      const isOfferSent = ev.event_type === 'OFFER_DELIVERED';
                      const isOfferDeclined = ev.event_type === 'OFFER_DECLINED';
                      const isOfferExpired = ev.event_type === 'OFFER_EXPIRED';
                      const isJobAccepted = ev.event_type === 'EMPLOYEE_JOB_ACCEPTED';
                      const isSearch = ev.event_type === 'CANDIDATES_EVALUATED' || ev.event_type === 'DISPATCH_STARTED';

                      // Dot color indicator
                      let dotColor = 'bg-blue-600';
                      if (ev.badge === 'success' || isJobAccepted) dotColor = 'bg-emerald-500 ring-2 ring-emerald-100';
                      else if (ev.badge === 'danger' || isOfferDeclined) dotColor = 'bg-rose-500 ring-2 ring-rose-100';
                      else if (ev.badge === 'warning' || isOfferExpired) dotColor = 'bg-amber-500 ring-2 ring-amber-100';
                      else if (isSearch) dotColor = 'bg-sky-500 ring-2 ring-sky-100';

                      return (
                        <div key={idx} className="relative group text-xs">
                          {/* Timeline dot */}
                          <div
                            className={`absolute -left-[23px] top-1.5 w-2.5 h-2.5 rounded-full ${dotColor}`}
                          />

                          <div className="bg-slate-50/80 border border-slate-200 rounded-md p-2.5 hover:bg-slate-50 transition-colors">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-bold text-slate-900 flex items-center gap-1.5">
                                {ev.title}
                              </span>
                              <span className="text-[10px] font-mono text-slate-400 shrink-0">
                                {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ''}
                              </span>
                            </div>

                            <p className="text-[11px] text-slate-600 mt-0.5">{ev.description}</p>

                            {/* Actor metadata footer */}
                            {ev.actor && (
                              <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                                <span>Actor:</span>
                                <span className="font-semibold text-slate-700">{ev.actor}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic py-2">No dispatch journey events recorded yet.</p>
                )}
              </div>

              {/* 3. Multi-Attempt Selector & Immutable Candidate Snapshot */}
              <div className="bg-white border border-slate-200 rounded-lg p-3.5 shadow-xs space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                  <div className="flex items-center gap-1.5">
                    <Users className="w-4 h-4 text-purple-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Candidate Evaluation Snapshot
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400">Captured at Dispatch Moment</span>
                </div>

                {/* Attempt Switcher Pills (If multiple attempts exist) */}
                {attempts.length > 1 && (
                  <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                    <span className="text-[10px] uppercase font-bold text-slate-400 mr-1">Attempts:</span>
                    {attempts.map((att, attIdx) => (
                      <button
                        key={attIdx}
                        type="button"
                        onClick={() => {
                          setSelectedAttemptIndex(attIdx);
                          setIsCandidatesExpanded(false);
                        }}
                        className={`px-2.5 py-1 rounded text-xs font-bold transition-all ${
                          selectedAttemptIndex === attIdx
                            ? 'bg-purple-600 text-white shadow-xs'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        Attempt #{att.attempt || attIdx + 1}
                        {att.eligible_count !== undefined ? ` · ${att.eligible_count} eligible` : ''}
                      </button>
                    ))}
                  </div>
                )}

                {/* Candidate Snapshot Table */}
                {currentCandidates.length > 0 ? (
                  <div className="space-y-2">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 text-[10px] uppercase font-bold">
                            <th className="py-2 px-2.5 font-mono w-12">Rank</th>
                            <th className="py-2 px-2.5">Technician</th>
                            <th className="py-2 px-2.5">Distance</th>
                            <th className="py-2 px-2.5">Score</th>
                            <th className="py-2 px-2.5 text-right">Result</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {displayedCandidates.map((cand, idx) => (
                            <tr key={cand.employee_id || idx} className="hover:bg-slate-50/80">
                              <td className="py-1.5 px-2.5 font-mono text-slate-500">{cand.rank || idx + 1}</td>
                              <td className="py-1.5 px-2.5 font-bold text-slate-900">
                                {cand.display_name || (cand.employee_id ? `${cand.employee_name} · EMP #${cand.employee_id}` : cand.employee_name)}
                              </td>
                              <td className="py-1.5 px-2.5 text-slate-600 font-mono">
                                {cand.distance_km !== null && cand.distance_km !== undefined
                                  ? `${cand.distance_km} km`
                                  : '—'}
                              </td>
                              <td className="py-1.5 px-2.5 font-mono text-slate-700">{cand.score ?? '—'}</td>
                              <td className="py-1.5 px-2.5 text-right">
                                <span
                                  className={`px-1.5 py-0.2 rounded text-[9px] font-bold border uppercase ${getStatusBadgeClass(
                                    cand.result
                                  )}`}
                                >
                                  {cand.result || 'EVALUATED'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Expand / Collapse Button if > 5 candidates */}
                    {currentCandidates.length > 5 && (
                      <div className="text-center pt-1">
                        <button
                          type="button"
                          onClick={() => setIsCandidatesExpanded(!isCandidatesExpanded)}
                          className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                        >
                          {isCandidatesExpanded ? (
                            <>
                              <ChevronUp className="w-3.5 h-3.5" />
                              <span>Show fewer candidates</span>
                            </>
                          ) : (
                            <>
                              <ChevronDown className="w-3.5 h-3.5" />
                              <span>+ {currentCandidates.length - 5} more candidates</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-slate-50 border border-slate-200 rounded-md p-3 text-center text-xs text-slate-500">
                    <Info className="w-4 h-4 text-slate-400 mx-auto mb-1" />
                    No candidate snapshot recorded for this attempt.
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
