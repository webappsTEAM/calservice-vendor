/**
 * AdminDispatchRadar.jsx
 *
 * CalTrack Super Admin Dispatch Radar — Read-Only Observability & Control Tower.
 *
 * Visualizes how customer bookings travel through the technician dispatch pipeline:
 *  - Metric overview strip (Active, Searching, Offered, Assigned, En Route, In Progress, Completed Today)
 *  - Filterable active jobs queue with search & distinct empty states
 *  - Selected Job summary with textual location only (NO MAP)
 *  - Current active offer card with live countdown timer
 *  - Sequential Decline / Expiry progression visualizer (Tech A -> Tech B -> Tech C)
 *  - Immutable Candidate Evaluation snapshot at dispatch time
 *  - Chronological dispatch lifecycle event timeline
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
} from 'lucide-react';

export function AdminDispatchRadar() {
  const [data, setData] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);
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

  // Handle job selection
  const handleSelectJob = (id) => {
    setSelectedJobId(id);
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
    if (s.includes('SEARCH') || s.includes('DISPATCH') || s.includes('RETRY')) return 'bg-sky-50 text-sky-700 border-sky-200';
    if (s.includes('ASSIGN') || s.includes('ACCEPT')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (s.includes('ROUTE') || s.includes('WAY')) return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    if (s.includes('PROGRESS') || s.includes('ARRIV')) return 'bg-purple-50 text-purple-700 border-purple-200';
    if (s.includes('COMPLET')) return 'bg-emerald-50 text-emerald-800 border-emerald-300';
    if (s.includes('DECLIN') || s.includes('CANCEL') || s.includes('FAIL') || s.includes('EXPIRE')) return 'bg-rose-50 text-rose-700 border-rose-200';
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  return (
    <div className="space-y-5">
      {/* ─── Metric Strip (Light Cards Aligned with Operations Page) ─────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Active Jobs</span>
            <Activity className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-1">{summary.total_active}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Pipeline total</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Searching</span>
            <Radio className="w-4 h-4 text-sky-500 animate-pulse" />
          </div>
          <div className="text-2xl font-black text-sky-600 mt-1">{summary.searching}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Finding candidates</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Active Offers</span>
            <Timer className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-black text-amber-600 mt-1">{summary.offered}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Awaiting decision</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Assigned</span>
            <UserCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-emerald-600 mt-1">{summary.assigned}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Ready for transit</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">En Route</span>
            <MapPin className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-black text-indigo-600 mt-1">{summary.en_route}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Traveling to site</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">In Progress</span>
            <Sparkles className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-black text-purple-600 mt-1">{summary.in_progress}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Active execution</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-xs col-span-2 sm:col-span-4 lg:col-span-1">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-1">{summary.completed_today}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Today's total</div>
        </div>
      </div>

      {/* ─── Control Bar: Filters, Search, and Refresh ───────────────────────── */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
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
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
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
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by Job #, Service, Tech..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            type="button"
            onClick={() => fetchRadar(null, false)}
            disabled={isRefreshing}
            className="p-2 bg-white hover:bg-slate-100 border border-slate-200 text-slate-600 hover:text-slate-900 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh Telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* ─── State C: API Error State ────────────────────────────────────────── */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 text-center">
          <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wide">DISPATCH RADAR UNAVAILABLE</h4>
          <p className="text-[11px] text-rose-700 mt-1">{error}</p>
          <button
            type="button"
            onClick={() => fetchRadar(null, false)}
            className="mt-3 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-bold shadow-xs inline-flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Radar Telemetry</span>
          </button>
        </div>
      )}

      {/* ─── Main Radar Grid (2 Columns: Active Queue & Selected Job Control Tower) ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Active Dispatch Queue */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Active Queue</span>
              <span className="px-2 py-0.5 bg-slate-100 text-slate-600 border border-slate-200 rounded-full text-[10px] font-bold">
                {jobsList.length}
              </span>
            </div>
            <span className="text-[10px] text-slate-400">Read-Only Telemetry</span>
          </div>

          {isLoading ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 flex flex-col items-center justify-center text-center gap-3 shadow-xs">
              <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
              <p className="text-xs font-semibold text-slate-600">Streaming dispatch telemetry...</p>
            </div>
          ) : jobsList.length === 0 ? (
            statusFilter === 'all' && !searchQuery ? (
              /* State A: Real Empty Queue */
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center shadow-xs">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">NO ACTIVE DISPATCH JOBS</h4>
                <p className="text-[11px] text-slate-500 mt-1">
                  No bookings are currently in an active dispatch state.
                </p>
              </div>
            ) : (
              /* State B: Filtered Empty Queue */
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center shadow-xs">
                <Filter className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">NO JOBS MATCH THIS FILTER</h4>
                <p className="text-[11px] text-slate-500 mt-1">
                  No active jobs match the selected criteria.
                </p>
                <button
                  type="button"
                  onClick={() => { setStatusFilter('all'); setSearchQuery(''); }}
                  className="mt-3 px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold"
                >
                  Reset Filters
                </button>
              </div>
            )
          ) : (
            <div className="space-y-2.5 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
              {jobsList.map((job) => {
                const isSelected = selectedJob?.id === job.id;
                const hasActiveOffer = !!job.current_offer;

                return (
                  <div
                    key={job.id}
                    onClick={() => handleSelectJob(job.id)}
                    className={`cursor-pointer rounded-xl p-4 transition-all duration-200 border ${
                      isSelected
                        ? 'bg-blue-50/60 border-blue-500 ring-1 ring-blue-500/30 shadow-sm'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/70 shadow-xs'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-black text-slate-900">
                            #{job.request_id || job.id}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getStatusBadgeClass(
                              hasActiveOffer ? 'OFFERED' : job.dispatch_status || job.status
                            )}`}
                          >
                            {hasActiveOffer ? 'OFFERED' : (job.dispatch_status || job.status).replace(/_/g, ' ')}
                          </span>
                        </div>
                        <h4 className="text-xs font-semibold text-slate-700 mt-1">{job.service}</h4>
                      </div>

                      {hasActiveOffer && (
                        <div className="text-right">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 border border-amber-200 text-amber-700 rounded text-[11px] font-mono font-bold">
                            <Clock className="w-3 h-3" />
                            {formatRemainingTime(job.current_offer.expires_at)}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Compact Details Footer */}
                    <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between text-[11px] text-slate-500 gap-2">
                      <div className="flex items-center gap-1.5 truncate max-w-[240px]">
                        <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                        <span className="truncate">{job.address || 'Textual location not specified'}</span>
                      </div>

                      {hasActiveOffer ? (
                        <span className="text-amber-700 font-semibold truncate">
                          → {job.current_offer.employee_name} ({job.current_offer.score} pts)
                        </span>
                      ) : job.assigned_technician_name ? (
                        <span className="text-emerald-700 font-semibold truncate">
                          ✓ {job.assigned_technician_name}
                        </span>
                      ) : (
                        <span className="text-slate-400 font-mono">
                          Attempt #{job.attempt_count || 1}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Selected Job Control Tower */}
        <div className="lg:col-span-7 space-y-4">
          {!selectedJob ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center shadow-xs">
              <Radio className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">Select a Job from the Queue</h3>
              <p className="text-xs text-slate-500 mt-1">
                Choose an active booking on the left to inspect its live offer status, candidate evaluations, and dispatch timeline.
              </p>
            </div>
          ) : (
            <>
              {/* 1. Job Summary Card */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-base font-black text-slate-900">
                        JOB #{selectedJob.request_id || selectedJob.id}
                      </h2>
                      <span
                        className={`px-2.5 py-0.5 rounded text-xs font-bold border uppercase ${getStatusBadgeClass(
                          selectedJob.current_offer ? 'OFFERED' : selectedJob.dispatch_status || selectedJob.status
                        )}`}
                      >
                        {selectedJob.current_offer ? 'OFFERED' : (selectedJob.dispatch_status || selectedJob.status).replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-sm font-bold text-blue-600 mt-1">{selectedJob.service}</p>
                  </div>

                  <div className="text-right text-xs text-slate-500">
                    <div>
                      Scheduled:{' '}
                      <span className="font-bold text-slate-800">
                        {selectedJob.scheduled_date || 'Today'} {selectedJob.scheduled_time || ''}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      Booked: {selectedJob.created_at ? new Date(selectedJob.created_at).toLocaleTimeString() : 'N/A'}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-slate-100 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                      Customer & Location
                    </span>
                    <span className="font-bold text-slate-800">{selectedJob.customer_name}</span>
                    <p className="text-slate-500 mt-0.5 flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                      <span>{selectedJob.address || 'Textual address not specified'}</span>
                    </p>
                  </div>

                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                      Assigned Professional
                    </span>
                    {selectedJob.assigned_technician_name ? (
                      <div className="flex items-center gap-1.5 mt-0.5 text-emerald-700 font-bold">
                        <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                        <span>{selectedJob.assigned_technician_name}</span>
                      </div>
                    ) : (
                      <span className="text-slate-400 italic font-medium">None currently assigned</span>
                    )}
                  </div>
                </div>
              </div>

              {/* 2. Current Offer Banner */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Timer className="w-4 h-4 text-amber-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Current Offer</span>
                  </div>
                  {selectedJob.current_offer && (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                      LIVE EXCLUSIVE WINDOW
                    </span>
                  )}
                </div>

                {selectedJob.current_offer ? (
                  <div className="bg-amber-50/50 border border-amber-200 rounded-xl p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Recipient</span>
                        <h3 className="text-sm font-black text-slate-900 mt-0.5">
                          {selectedJob.current_offer.employee_name}
                        </h3>
                      </div>

                      <div className="text-right">
                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Time Remaining</span>
                        <div className="text-lg font-mono font-black text-amber-700">
                          {formatRemainingTime(selectedJob.current_offer.expires_at)}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-amber-200/60 text-center text-xs">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Rank Score</span>
                        <span className="font-bold text-slate-900 font-mono">{selectedJob.current_offer.score} pts</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Sent At</span>
                        <span className="font-bold text-slate-800">
                          {selectedJob.current_offer.offered_at ? new Date(selectedJob.current_offer.offered_at).toLocaleTimeString() : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Status</span>
                        <span className="font-bold text-amber-700 uppercase">{selectedJob.current_offer.status}</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-center">
                    <p className="text-xs font-bold text-slate-700">NO ACTIVE TECHNICIAN OFFER</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {selectedJob.assigned_technician_name
                        ? `Job successfully assigned to ${selectedJob.assigned_technician_name}.`
                        : selectedJob.unassigned_reason_message || 'Awaiting candidate ranking or retry schedule.'}
                    </p>
                  </div>
                )}
              </div>

              {/* 3. Sequential Decline / Expiry Flow Visualizer */}
              {selectedJob.offers_history && selectedJob.offers_history.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Sequential Offer Progression
                    </span>
                  </div>

                  <div className="space-y-2">
                    {selectedJob.offers_history.map((off, idx) => (
                      <div
                        key={off.offer_id || idx}
                        className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs"
                      >
                        <div className="flex items-center gap-3">
                          <span className="w-5 h-5 rounded-full bg-white border border-slate-300 text-slate-700 font-mono font-bold flex items-center justify-center text-[10px]">
                            {idx + 1}
                          </span>
                          <div>
                            <span className="font-bold text-slate-900">{off.employee_name}</span>
                            <span className="text-[10px] text-slate-500 font-mono ml-2">({off.score} pts)</span>
                            {off.rejection_reason && (
                              <p className="text-[10px] text-rose-600 mt-0.5 italic">"{off.rejection_reason}"</p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getStatusBadgeClass(
                              off.status
                            )}`}
                          >
                            {off.status}
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {off.offered_at ? new Date(off.offered_at).toLocaleTimeString() : ''}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 4. Eligible Candidate Snapshot (Immutable at Dispatch Time) */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-purple-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                      Candidate Evaluation Snapshot
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400">Captured at Dispatch Time</span>
                </div>

                {selectedJob.candidate_evaluations && selectedJob.candidate_evaluations.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 text-[10px] uppercase font-bold">
                          <th className="py-2.5 px-3 font-mono">Rank</th>
                          <th className="py-2.5 px-3">Technician</th>
                          <th className="py-2.5 px-3">Distance</th>
                          <th className="py-2.5 px-3">Score</th>
                          <th className="py-2.5 px-3 text-right">Result</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {selectedJob.candidate_evaluations.map((cand, idx) => (
                          <tr key={cand.employee_id || idx} className="hover:bg-slate-50/80">
                            <td className="py-2 px-3 font-mono text-slate-500">{cand.rank || idx + 1}</td>
                            <td className="py-2 px-3 font-bold text-slate-900">{cand.employee_name}</td>
                            <td className="py-2 px-3 text-slate-600 font-mono">
                              {cand.distance_km !== null && cand.distance_km !== undefined
                                ? `${cand.distance_km} km`
                                : '—'}
                            </td>
                            <td className="py-2 px-3 font-mono text-slate-700">{cand.score ?? '—'}</td>
                            <td className="py-2 px-3 text-right">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getStatusBadgeClass(
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
                ) : (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center text-xs text-slate-500">
                    <Info className="w-4 h-4 text-slate-400 mx-auto mb-1" />
                    Candidate snapshot recorded upon first candidate evaluation cycle.
                  </div>
                )}
              </div>

              {/* 5. Unified Dispatch Lifecycle Timeline */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Dispatch Flow Timeline
                  </span>
                </div>

                {selectedJob.timeline && selectedJob.timeline.length > 0 ? (
                  <div className="space-y-3 relative pl-4 border-l border-slate-200 my-2">
                    {selectedJob.timeline.map((ev, idx) => (
                      <div key={idx} className="relative group">
                        {/* Dot indicator */}
                        <div
                          className={`absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full border-2 border-white ${
                            ev.badge === 'success'
                              ? 'bg-emerald-500'
                              : ev.badge === 'danger'
                              ? 'bg-rose-500'
                              : ev.badge === 'warning'
                              ? 'bg-amber-500'
                              : 'bg-blue-600'
                          }`}
                        />
                        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-bold text-slate-900">{ev.title}</span>
                            <span className="text-[10px] font-mono text-slate-400">
                              {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ''}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-600 mt-1">{ev.description}</p>
                          <div className="text-[10px] text-slate-400 mt-1.5 flex items-center gap-1">
                            <span>Actor:</span>
                            <span className="font-semibold text-slate-700">{ev.actor || 'System'}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">No lifecycle events recorded yet.</p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
