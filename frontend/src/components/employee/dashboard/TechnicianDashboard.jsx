import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Navigation,
  Phone,
  MapPin,
  Clock,
  CheckCircle2,
  Power,
  Loader2,
  ChevronRight,
  Briefcase,
  Calculator,
  Wrench,
  Star,
  RotateCw,
  Play,
} from 'lucide-react';
import { formatDistanceDisplay } from '../../../utils/distanceFormatter.js';
import {
  apiClockIn,
  apiClockOut,
  apiStartBreak,
  apiEndBreak,
} from '../../../api/clockInApi.js';

/**
 * TechnicianDashboard.jsx
 *
 * Modern field-service technician experience inspired by Uber / Rapido:
 * - Minimal, clean, spacious, strong visual hierarchy
 * - Answers immediately: "Where am I? What job am I doing? What do I need to do next?"
 * - No card-after-card overload, no 4-column KPI wall, no service chip wall
 * - Single dominant primary action per state
 * - Consistent 6–8px button/input radius, 8–12px operational surface radius
 * - Unified Calservices brand blue (#2563EB)
 */

export function TechnicianDashboard({
  user,
  employee,
  profile,
  isOnline,
  isTogglingOnline,
  handleToggleOnline,
  timeTracking,
  onRefreshData,
  activeJobs = [],
  completedJobs = [],
  allJobs = [],
  activeAssignedJob,
  hasActiveJob,
  incomingOffers = [],
  liveLocation,
  gpsState,
  scanCurrentLocation,
  actionLoading,
  handleAcceptOffer,
  handleRejectOffer,
  handleJobAction,
  handleManualVerifyArrival,
  handleDirectJobClockIn,
  handleOpenCancelModal,
  setProofModalJob,
  setCashModalJob,
  setIsQuotationModalOpen,
  setSelectedJob,
  preServiceState = {},
  otpInput,
  setOtpInput,
  handleVerifyOtpSubmit,
  handleResendOtp,
  approvedServices = [],
  openLiveCamera,
  handlePhotoUploadSubmit,
}) {
  const navigate = useNavigate();

  // ── Shift Elapsed Timer ──
  const [shiftElapsedSeconds, setShiftElapsedSeconds] = useState(0);
  const [shiftLoading, setShiftLoading] = useState(false);
  const [shiftError, setShiftError] = useState('');
  const [showBreakPicker, setShowBreakPicker] = useState(false);

  const isClockedIn = Boolean(timeTracking?.is_clocked_in);
  const isBreak = timeTracking?.shift_status === 'on_break';
  const activeBreakType = timeTracking?.active_break?.break_type || null;

  useEffect(() => {
    if (!isClockedIn || !timeTracking?.clock_in_time) {
      setShiftElapsedSeconds(0);
      return;
    }
    const startMs = new Date(timeTracking.clock_in_time).getTime();
    const completedBreakSecs = Number(timeTracking?.time_log?.break_seconds ?? timeTracking?.break_seconds ?? 0);
    const serverOffset = timeTracking?.server_time ? Date.parse(timeTracking.server_time) - Date.now() : 0;
    const activeBreakStartMs = (isBreak && timeTracking?.active_break?.break_start)
      ? new Date(timeTracking.active_break.break_start).getTime()
      : null;

    const calc = () => {
      // If currently on break, freeze worked duration at break start timestamp
      const effectiveNowMs = (isBreak && activeBreakStartMs)
        ? activeBreakStartMs
        : (Date.now() + serverOffset);
      const totalSecs = Math.max(0, Math.floor((effectiveNowMs - startMs) / 1000) - completedBreakSecs);
      setShiftElapsedSeconds(totalSecs);
    };
    calc();
    // Only tick when not on an active break
    if (isBreak) {
      return;
    }
    const interval = setInterval(calc, 1000);
    return () => clearInterval(interval);
  }, [
    isClockedIn,
    isBreak,
    timeTracking?.clock_in_time,
    timeTracking?.time_log?.break_seconds,
    timeTracking?.break_seconds,
    timeTracking?.active_break?.break_start,
    timeTracking?.server_time,
  ]);

  const formattedShiftDuration = useMemo(() => {
    if (!isClockedIn) return 'Not clocked in';
    const hours = Math.floor(shiftElapsedSeconds / 3600);
    const mins = Math.floor((shiftElapsedSeconds % 3600) / 60);
    const secs = shiftElapsedSeconds % 60;
    if (isBreak) {
      return `On ${activeBreakType ? activeBreakType.toUpperCase() : ''} break`;
    }
    if (hours > 0) {
      return `${String(hours).padStart(2, '0')}h ${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s active`;
    }
    return `${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s active`;
  }, [isClockedIn, shiftElapsedSeconds, isBreak, activeBreakType]);

  // ── Shift Handlers ──
  const handleShiftClockIn = async () => {
    try {
      setShiftLoading(true);
      setShiftError('');
      const loc = liveLocation || (scanCurrentLocation ? await scanCurrentLocation().catch(() => null) : null);
      await apiClockIn({
        address: loc?.address || 'Current Site',
        latitude: loc?.latitude,
        longitude: loc?.longitude,
        accuracy: loc?.accuracy,
      });
      if (onRefreshData) await onRefreshData({ silent: true });
    } catch (err) {
      setShiftError(err.message || 'Clock-in failed.');
    } finally {
      setShiftLoading(false);
    }
  };

  const handleShiftClockOut = async () => {
    if (hasActiveJob) {
      setShiftError('Cannot clock out while on an active assignment.');
      return;
    }
    if (!window.confirm('Are you sure you want to end your shift and clock out?')) return;
    try {
      setShiftLoading(true);
      setShiftError('');
      await apiClockOut({ clock_out_reason: 'SHIFT_COMPLETE' });
      if (onRefreshData) await onRefreshData({ silent: true });
    } catch (err) {
      setShiftError(err.message || 'Clock-out failed.');
    } finally {
      setShiftLoading(false);
    }
  };

  const handleStartBreak = async (type) => {
    try {
      setShiftLoading(true);
      setShiftError('');
      setShowBreakPicker(false);
      await apiStartBreak(type);
      if (onRefreshData) await onRefreshData({ silent: true });
    } catch (err) {
      setShiftError(err.message || 'Failed to start break.');
    } finally {
      setShiftLoading(false);
    }
  };

  const handleEndBreak = async () => {
    try {
      setShiftLoading(true);
      setShiftError('');
      await apiEndBreak();
      if (onRefreshData) await onRefreshData({ silent: true });
    } catch (err) {
      setShiftError(err.message || 'Failed to end break.');
    } finally {
      setShiftLoading(false);
    }
  };

  // ── Offer Live Countdown ──
  const activeOffer = incomingOffers?.[0] || null;
  const [offerCountdown, setOfferCountdown] = useState('');

  const offerExpiresAt = activeOffer?.active_offer?.expires_at || activeOffer?.offer_expires_at;

  useEffect(() => {
    if (!offerExpiresAt) {
      setOfferCountdown('');
      return;
    }
    const targetMs = new Date(offerExpiresAt).getTime();
    const tick = () => {
      const remainingSecs = Math.max(0, Math.floor((targetMs - Date.now()) / 1000));
      if (remainingSecs <= 0) {
        setOfferCountdown('00:00');
        return;
      }
      const mm = String(Math.floor(remainingSecs / 60)).padStart(2, '0');
      const ss = String(remainingSecs % 60).padStart(2, '0');
      setOfferCountdown(`${mm}:${ss}`);
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [offerExpiresAt]);

  // ── Active Job Resolution ──
  const currentJob = useMemo(() => {
    if (activeAssignedJob) return activeAssignedJob;
    const empId = user?.employee_id || user?.employeeId || user?.id;
    if (activeJobs && activeJobs.length > 0) {
      const nonOffer = activeJobs.find((j) => {
        const isOffer = j.is_offer === true || j.active_offer?.status === 'OFFERED';
        if (isOffer) return false;
        const st = (j.status || j.job_status || '').toLowerCase();
        if (!['accepted', 'on_the_way', 'en_route', 'arrived', 'in_progress', 'proof_submitted'].includes(st)) {
          return false;
        }
        const isAssigned = Boolean(
          j.is_assigned_to_current_employee === true ||
          (empId && (j.assigned_employee_id === empId || j.assigned_employee === empId || j.assigned_employee?.id === empId)) ||
          (user?.id && (j.technician_id === user.id || j.assigned_employee_id === user.id))
        );
        return isAssigned;
      });
      if (nonOffer) return nonOffer;
    }
    return null;
  }, [activeAssignedJob, activeJobs, user]);

  const currentJobStatus = (currentJob?.status || '').toLowerCase();

  // ── Today's Metrics ──
  const todayCompletedJobs = useMemo(() => {
    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

    return completedJobs.filter((j) => {
      const st = (j.status || '').toLowerCase();
      if (st !== 'completed') return false;

      const compDateRaw = j.completed_at || j.completed_date;
      if (compDateRaw) {
        const d = new Date(compDateRaw);
        if (!isNaN(d.getTime())) {
          const compStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
          return compStr === todayStr;
        }
      }
      return false;
    });
  }, [completedJobs]);

  const todayEarnings = useMemo(() => {
    return todayCompletedJobs.reduce((acc, j) => {
      const val = parseFloat(
        j.payment?.amount_paid || j.payment?.amount_due || j.total_amount || 0
      );
      return acc + (isNaN(val) ? 0 : val);
    }, 0);
  }, [todayCompletedJobs]);

  // Technician display name
  const techName = user?.firstName
    ? `${user.firstName} ${user.lastName || ''}`.trim()
    : user?.username || 'Technician';

  return (
    <div className="max-w-xl mx-auto py-2 sm:py-4 px-4 font-sans text-[#0F172A] space-y-6">
      {/* ── 1. TECHNICIAN HEADER (Clean, App-Style) ── */}
      <header className="flex items-start justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-lg font-bold text-[#0F172A] tracking-tight leading-snug">
            {techName}
          </h1>
          <p className="text-xs text-[#64748B] mt-0.5">
            Field Technician {profile?.employee_id ? `· ${profile.employee_id}` : ''}
          </p>
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <div className="flex items-center gap-2">
            {hasActiveJob ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#2563EB]">
                <span className="w-2 h-2 rounded-full bg-[#2563EB]" />
                ON JOB
              </span>
            ) : isOnline ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#16A34A]">
                <span className="w-2 h-2 rounded-full bg-[#16A34A]" />
                ONLINE
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#64748B]">
                <span className="w-2 h-2 rounded-full bg-[#94A3B8]" />
                OFFLINE
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={handleToggleOnline}
            disabled={hasActiveJob || isTogglingOnline}
            className="text-[11px] font-semibold text-[#64748B] hover:text-[#0F172A] disabled:opacity-50 cursor-pointer underline transition-colors"
          >
            {isTogglingOnline
              ? 'Updating...'
              : hasActiveJob
              ? 'Locked on Job'
              : isOnline
              ? 'Go Offline'
              : 'Go Online'}
          </button>
        </div>
      </header>

      {/* ── 2. CONTEXTUAL LOCATION TELEMETRY ── */}
      <div className="flex items-center justify-between text-xs text-[#64748B]">
        <div className="flex items-center gap-1.5 truncate">
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${
              liveLocation ? 'bg-[#16A34A]' : 'bg-[#D97706]'
            }`}
          />
          {currentJob ? (
            <span className="truncate">
              {currentJob.distance_km != null
                ? `${formatDistanceDisplay(currentJob.distance_km)} · ~8 min to customer · GPS active`
                : 'GPS active · Heading to customer'}
            </span>
          ) : (
            <span>
              GPS active
              {liveLocation?.accuracy ? ` · Accuracy ${Math.round(liveLocation.accuracy)}m` : ''}
            </span>
          )}
        </div>

        {scanCurrentLocation && (
          <button
            type="button"
            onClick={() => scanCurrentLocation()}
            title="Refresh GPS"
            className="text-xs text-[#2563EB] hover:underline font-medium flex items-center gap-1 shrink-0 ml-2 cursor-pointer"
          >
            <RotateCw className="w-3 h-3" />
            <span>Refresh</span>
          </button>
        )}
      </div>

      {/* ── 3. CURRENT JOB / OPERATIONAL STATE (THE HEART OF THE DASHBOARD) ── */}
      <main className="space-y-4">
        {/* STATE B: INCOMING DISPATCH OFFER (Always visible whenever activeOffer exists!) */}
        {activeOffer && (
          <div className="bg-white border-2 border-amber-400 rounded-lg p-5 space-y-4 shadow-md bg-amber-50/20">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
                </span>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#D97706]">
                  Incoming Offer {incomingOffers?.length > 1 ? `(1 of ${incomingOffers.length})` : ''}
                </span>
              </div>
              {offerCountdown && (
                <span className="text-xs font-mono font-bold text-[#D97706] bg-amber-100/80 px-2 py-0.5 rounded border border-amber-300">
                  Offer expires in {offerCountdown}
                </span>
              )}
            </div>

            <div>
              <h2 className="text-xl font-bold text-[#0F172A] leading-tight">
                {activeOffer.service_title || activeOffer.service_category || activeOffer.issue_title || 'Service Request'}
              </h2>
              <p className="text-xs text-[#64748B] mt-1">
                {activeOffer.distance_km != null
                  ? `${formatDistanceDisplay(activeOffer.distance_km)} · Customer nearby`
                  : 'Customer nearby'}
                {activeOffer.total_amount ? ` · Estimated ₹${activeOffer.total_amount}` : ''}
              </p>
              {activeOffer.address && (
                <p className="text-xs text-slate-600 mt-1.5 flex items-start gap-1.5 leading-relaxed">
                  <MapPin className="w-3.5 h-3.5 text-[#2563EB] shrink-0 mt-0.5" />
                  <span>{activeOffer.address}</span>
                </p>
              )}
            </div>

            {/* Dominant Primary Action: Accept Job */}
            <div className="space-y-2 pt-1">
              <button
                type="button"
                onClick={() => handleAcceptOffer(activeOffer.id)}
                disabled={actionLoading === activeOffer.id || hasActiveJob}
                className="w-full min-h-[48px] py-3 px-4 bg-[#2563EB] hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 text-white font-bold text-sm rounded-md transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                {actionLoading === activeOffer.id ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                <span>
                  {hasActiveJob ? 'Finish current job first' : 'ACCEPT JOB'}
                </span>
              </button>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => handleRejectOffer(activeOffer.id)}
                  disabled={actionLoading === activeOffer.id}
                  className="text-xs text-[#64748B] hover:text-[#DC2626] font-medium transition-colors cursor-pointer py-1"
                >
                  Decline
                </button>
              </div>
            </div>
          </div>
        )}

        {/* STATE A: ACTIVE JOB IN PROGRESS */}
        {currentJob ? (
          <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-4 shadow-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#2563EB]">
                {currentJobStatus === 'on_the_way' || currentJobStatus === 'en_route'
                  ? 'Travelling'
                  : currentJobStatus === 'arrived'
                  ? 'Arrived at Site'
                  : currentJobStatus === 'in_progress' || currentJobStatus === 'service_started'
                  ? 'In Progress'
                  : currentJobStatus === 'proof_submitted'
                  ? 'Payment Due'
                  : 'Current Job'}
              </span>
              {currentJob.distance_km != null && (
                <span className="text-xs text-[#64748B] font-medium">
                  {formatDistanceDisplay(currentJob.distance_km)} away · ~8 min
                </span>
              )}
            </div>

            {/* Service Title */}
            <div>
              <h2 className="text-xl font-bold text-[#0F172A] leading-tight">
                {currentJob.service_title || currentJob.service_category || currentJob.issue_title || 'Service Request'}
              </h2>
            </div>

            {/* Customer & Location */}
            <div className="space-y-2 text-xs text-[#0F172A]">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-sm">
                  Customer: {currentJob.customer_display_name || currentJob.customer_name || 'Customer'}
                </span>
                {currentJob.phone && (
                  <a
                    href={`tel:${currentJob.phone}`}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-[#2563EB] hover:underline"
                  >
                    <Phone className="w-3.5 h-3.5" />
                    <span>Call</span>
                  </a>
                )}
              </div>

              {currentJob.address && (
                <p className="text-[#64748B] flex items-start gap-1.5 leading-relaxed">
                  <MapPin className="w-3.5 h-3.5 text-[#2563EB] shrink-0 mt-0.5" />
                  <span>{currentJob.address}</span>
                </p>
              )}
            </div>

            {/* Simple Text Stepper */}
            <div className="pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between text-[11px] font-semibold text-[#94A3B8]">
                <span className={['accepted', 'on_the_way', 'arrived', 'in_progress', 'proof_submitted', 'completed'].includes(currentJobStatus) ? 'text-[#0F172A] font-bold' : ''}>
                  Assigned
                </span>
                <span>→</span>
                <span className={['on_the_way', 'arrived', 'in_progress', 'proof_submitted', 'completed'].includes(currentJobStatus) ? 'text-[#2563EB] font-bold' : ''}>
                  Travel
                </span>
                <span>→</span>
                <span className={['arrived', 'in_progress', 'proof_submitted', 'completed'].includes(currentJobStatus) ? 'text-[#16A34A] font-bold' : ''}>
                  Arrived
                </span>
                <span>→</span>
                <span className={['in_progress', 'proof_submitted', 'completed'].includes(currentJobStatus) ? 'text-[#16A34A] font-bold' : ''}>
                  Work
                </span>
                <span>→</span>
                <span className={['proof_submitted', 'completed'].includes(currentJobStatus) ? 'text-[#D97706] font-bold' : ''}>
                  Done
                </span>
              </div>
            </div>

            {/* ONE DOMINANT ACTION BUTTON */}
            <div className="pt-2">
              {currentJobStatus === 'accepted' ? (
                <button
                  type="button"
                  onClick={() => handleJobAction(currentJob.id, 'on_the_way')}
                  disabled={actionLoading === currentJob.id}
                  className="w-full min-h-[48px] py-3 px-4 bg-[#2563EB] hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-sm rounded-md transition-colors flex items-center justify-center gap-2 cursor-pointer"
                >
                  {actionLoading === currentJob.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Navigation className="w-4 h-4" />
                  )}
                  <span>START TRIP</span>
                </button>
              ) : currentJobStatus === 'on_the_way' || currentJobStatus === 'en_route' ? (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedJob(currentJob);
                      navigate('/workforce/employee/jobs');
                    }}
                    className="w-full min-h-[48px] py-3 px-4 bg-[#2563EB] hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-sm rounded-md transition-colors flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Navigation className="w-4 h-4" />
                    <span>OPEN NAVIGATION</span>
                  </button>
                  <div className="text-center">
                    <button
                      type="button"
                      onClick={handleManualVerifyArrival}
                      disabled={actionLoading === currentJob.id}
                      className="text-xs text-[#2563EB] hover:underline cursor-pointer py-1 font-medium"
                    >
                      {actionLoading === currentJob.id ? 'Verifying arrival...' : 'Arrived at site? Verify Arrival →'}
                    </button>
                  </div>
                </div>
              ) : currentJobStatus === 'arrived' ? (
                <div className="space-y-3">
                  <div className="bg-slate-50 p-3 rounded-md border border-slate-200 space-y-2">
                    <p className="text-xs font-semibold text-[#0F172A]">
                      Verification required. Ask customer for 6-digit OTP:
                    </p>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        maxLength={6}
                        placeholder="6-digit OTP"
                        value={otpInput}
                        onChange={(e) => setOtpInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleVerifyOtpSubmit()}
                        className="flex-1 min-h-[44px] px-3 bg-white border border-slate-300 rounded-md font-mono text-center text-sm font-bold tracking-widest text-[#0F172A] focus:outline-none focus:border-[#2563EB]"
                      />
                      <button
                        type="button"
                        onClick={handleVerifyOtpSubmit}
                        disabled={actionLoading === currentJob.id || !otpInput?.trim()}
                        className="min-h-[44px] px-4 bg-[#2563EB] hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 text-white font-bold text-xs rounded-md transition-colors cursor-pointer shrink-0"
                      >
                        {actionLoading === currentJob.id ? 'Verifying...' : 'VERIFY OTP'}
                      </button>
                    </div>
                    <div className="flex items-center justify-between text-[11px] pt-0.5">
                      <button
                        type="button"
                        onClick={handleResendOtp}
                        disabled={actionLoading === currentJob.id}
                        className="text-[#2563EB] hover:underline cursor-pointer font-medium"
                      >
                        Resend OTP
                      </button>
                      {!preServiceState.presence_photo && openLiveCamera && (
                        <button
                          type="button"
                          onClick={() =>
                            openLiveCamera(
                              'Capture Presence Selfie',
                              'user',
                              'presence_selfie',
                              (file) => {
                                if (handlePhotoUploadSubmit) {
                                  handlePhotoUploadSubmit('presence', file, currentJob);
                                }
                              }
                            )
                          }
                          className="text-[#0F172A] underline cursor-pointer font-medium"
                        >
                          Take presence selfie
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ) : currentJobStatus === 'in_progress' || currentJobStatus === 'service_started' ? (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => setProofModalJob(currentJob)}
                    className="w-full min-h-[48px] py-3 px-4 bg-[#16A34A] hover:bg-emerald-700 active:bg-emerald-800 text-white font-bold text-sm rounded-md transition-colors flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>COMPLETE SERVICE</span>
                  </button>
                  {(currentJob.is_estimation || currentJob.pricing_mode === 'QUOTATION') && (
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedJob(currentJob);
                        setIsQuotationModalOpen(true);
                      }}
                      className="w-full min-h-[40px] py-2 px-3 bg-white hover:bg-slate-50 border border-slate-200 text-[#0F172A] font-semibold text-xs rounded-md transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Calculator className="w-3.5 h-3.5 text-[#2563EB]" />
                      <span>Open Quotation Builder</span>
                    </button>
                  )}
                </div>
              ) : currentJobStatus === 'proof_submitted' ? (
                <button
                  type="button"
                  onClick={() => setCashModalJob(currentJob)}
                  className="w-full min-h-[48px] py-3 px-4 bg-[#2563EB] hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-sm rounded-md transition-colors flex items-center justify-center gap-2 cursor-pointer"
                >
                  <span>COLLECT PAYMENT (₹{currentJob.payment?.amount_due || currentJob.total_amount || '0'})</span>
                </button>
              ) : null}
            </div>

            {/* Quiet Secondary Links */}
            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-100 text-[#64748B]">
              <button
                type="button"
                onClick={() => {
                  setSelectedJob(currentJob);
                  navigate('/workforce/employee/jobs');
                }}
                className="hover:text-[#0F172A] cursor-pointer font-medium"
              >
                View full details →
              </button>
              {['accepted', 'on_the_way', 'en_route', 'arrived'].includes(currentJobStatus) &&
                !preServiceState?.otp_verified && (
                  <button
                    type="button"
                    onClick={() => handleOpenCancelModal(currentJob)}
                    className="text-[#DC2626] hover:underline cursor-pointer font-medium"
                  >
                    Cancel assignment
                  </button>
                )}
            </div>
          </div>
        ) : !activeOffer ? (
          /* STATE C: STANDBY / READINESS */
          <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-3 shadow-xs">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
              {isOnline ? 'Standby' : 'Offline'}
            </span>

            <div>
              <h2 className="text-xl font-bold text-[#0F172A] leading-tight">
                {isOnline ? "You're ready" : "You're offline"}
              </h2>
              <p className="text-xs text-[#64748B] mt-1 leading-relaxed">
                {isOnline
                  ? 'Location active. Waiting for nearby customer dispatches in your territory.'
                  : 'Switch online to start receiving automated customer bookings.'}
              </p>
            </div>

            <div className="pt-2">
              {isOnline ? (
                <button
                  type="button"
                  onClick={handleToggleOnline}
                  disabled={isTogglingOnline}
                  className="w-full min-h-[44px] py-2.5 px-4 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-bold text-xs rounded-md transition-colors cursor-pointer"
                >
                  {isTogglingOnline ? 'Updating...' : 'GO OFFLINE'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleToggleOnline}
                  disabled={isTogglingOnline}
                  className="w-full min-h-[48px] py-3 px-4 bg-[#2563EB] hover:bg-blue-700 text-white font-bold text-sm rounded-md transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  {isTogglingOnline ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Power className="w-4 h-4" />
                  )}
                  <span>GO ONLINE</span>
                </button>
              )}
            </div>
          </div>
        ) : null}
      </main>

      {/* ── 4. SHIFT / ATTENDANCE (Compact Operational Control) ── */}
      <section className="pt-3 border-t border-slate-200 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
            Shift
          </span>
          <span className="font-mono font-semibold text-[#0F172A]">
            {formattedShiftDuration}
          </span>
        </div>

        {shiftError && (
          <p className="text-xs text-[#DC2626] font-medium">{shiftError}</p>
        )}

        <div className="flex items-center gap-2">
          {isClockedIn ? (
            <>
              <button
                type="button"
                onClick={handleShiftClockOut}
                disabled={shiftLoading || hasActiveJob}
                className="flex-1 min-h-[38px] py-1.5 px-3 bg-white hover:bg-rose-50 text-[#DC2626] border border-rose-200 font-bold text-xs rounded-md transition-colors disabled:opacity-50 cursor-pointer"
              >
                {shiftLoading ? 'Ending shift...' : 'CLOCK OUT'}
              </button>

              {isBreak ? (
                <button
                  type="button"
                  onClick={handleEndBreak}
                  disabled={shiftLoading}
                  className="min-h-[38px] py-1.5 px-3 bg-[#16A34A] hover:bg-emerald-700 text-white font-bold text-xs rounded-md transition-colors cursor-pointer"
                >
                  End Break
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowBreakPicker(!showBreakPicker)}
                  disabled={shiftLoading}
                  className="min-h-[38px] py-1.5 px-3 bg-white hover:bg-slate-50 text-[#0F172A] border border-slate-300 font-semibold text-xs rounded-md transition-colors cursor-pointer"
                >
                  Break ▾
                </button>
              )}
            </>
          ) : (
            <button
              type="button"
              onClick={handleShiftClockIn}
              disabled={shiftLoading}
              className="w-full min-h-[40px] py-2 px-3 bg-[#2563EB] hover:bg-blue-700 text-white font-bold text-xs rounded-md transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{shiftLoading ? 'Starting shift...' : 'START SHIFT'}</span>
            </button>
          )}
        </div>

        {/* Break Selection Menu */}
        {showBreakPicker && isClockedIn && !isBreak && (
          <div className="bg-white border border-slate-200 rounded-md p-2 space-y-1 text-xs">
            <p className="text-[11px] font-semibold text-[#64748B] px-1">Select Break Type:</p>
            <div className="grid grid-cols-2 gap-1.5">
              {['Tea', 'Lunch', 'Rest', 'Personal'].map((b) => (
                <button
                  key={b}
                  type="button"
                  onClick={() => handleStartBreak(b.toLowerCase())}
                  className="py-1 px-2 bg-slate-50 hover:bg-slate-100 text-[#0F172A] font-medium text-xs rounded-md border border-slate-200 text-left cursor-pointer"
                >
                  {b} Break
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ── 5. TODAY'S ACTIVITY (Lightweight Summary) ── */}
      <section className="pt-3 border-t border-slate-200 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
            Today
          </span>
          <span className="font-semibold text-[#0F172A]">
            {todayCompletedJobs.length} completed
            {todayEarnings > 0 ? ` · ₹${todayEarnings.toFixed(0)} earned` : ''}
          </span>
        </div>

        {/* Recent Jobs list */}
        {allJobs && allJobs.length > 0 ? (
          <div className="divide-y divide-slate-100 text-xs">
            {allJobs.slice(0, 3).map((job) => (
              <div
                key={job.id}
                onClick={() => {
                  setSelectedJob(job);
                  navigate('/workforce/employee/jobs');
                }}
                className="py-2 flex items-center justify-between gap-2 hover:bg-slate-50 rounded px-1 transition-colors cursor-pointer"
              >
                <div className="truncate">
                  <p className="font-semibold text-[#0F172A] truncate">
                    {job.service_title || job.service_category || 'Service Request'}
                  </p>
                  <p className="text-[11px] text-[#64748B]">
                    {job.customer_display_name || job.customer_name || 'Customer'}
                  </p>
                </div>
                <div className="text-right shrink-0 text-xs font-mono font-medium text-[#0F172A]">
                  {job.total_amount ? `₹${job.total_amount}` : ''}
                  <ChevronRight className="w-3.5 h-3.5 inline ml-1 text-slate-400" />
                </div>
              </div>
            ))}
            <div className="pt-1.5">
              <Link
                to="/workforce/employee/jobs"
                className="text-xs text-[#2563EB] hover:underline font-semibold"
              >
                View all →
              </Link>
            </div>
          </div>
        ) : (
          <p className="text-xs text-[#64748B] italic py-1">
            No activity recorded today yet.
          </p>
        )}
      </section>

      {/* ── 6. QUICK NAVIGATION (Mobile Application Strip) ── */}
      <nav className="pt-3 border-t border-slate-200 space-y-2">
        <div className="grid grid-cols-4 gap-2 text-center text-xs">
          <Link
            to="/workforce/employee/jobs"
            className="flex flex-col items-center justify-center py-2.5 px-2 rounded-md hover:bg-slate-100 text-slate-700 hover:text-[#2563EB] transition-colors"
          >
            <Briefcase className="w-4 h-4 mb-1 text-slate-500" />
            <span className="font-semibold">Jobs</span>
          </Link>
          <Link
            to="/workforce/employee/estimates"
            className="flex flex-col items-center justify-center py-2.5 px-2 rounded-md hover:bg-slate-100 text-slate-700 hover:text-[#2563EB] transition-colors"
          >
            <Calculator className="w-4 h-4 mb-1 text-slate-500" />
            <span className="font-semibold">Quotes</span>
          </Link>
          <Link
            to="/workforce/employee/services"
            className="flex flex-col items-center justify-center py-2.5 px-2 rounded-md hover:bg-slate-100 text-slate-700 hover:text-[#2563EB] transition-colors"
          >
            <Wrench className="w-4 h-4 mb-1 text-slate-500" />
            <span className="font-semibold">Services</span>
          </Link>
          <Link
            to="/workforce/employee/performance"
            className="flex flex-col items-center justify-center py-2.5 px-2 rounded-md hover:bg-slate-100 text-slate-700 hover:text-[#2563EB] transition-colors"
          >
            <Star className="w-4 h-4 mb-1 text-slate-500" />
            <span className="font-semibold">Ratings</span>
          </Link>
        </div>
      </nav>

      {/* ── 7. YOUR SERVICES (Compact Preview) ── */}
      <section className="pt-3 border-t border-slate-200 text-xs space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
            Your Services
          </span>
          <Link
            to="/workforce/employee/services"
            className="text-xs text-[#2563EB] hover:underline font-semibold"
          >
            View all →
          </Link>
        </div>

        <p className="text-xs text-[#0F172A] leading-relaxed">
          {approvedServices && approvedServices.length > 0 ? (
            <>
              <span>
                {approvedServices
                  .slice(0, 3)
                  .map((s) => s.name)
                  .join(' · ')}
              </span>
              {approvedServices.length > 3 && (
                <span className="text-[#64748B] font-medium">
                  {' '}
                  · +{approvedServices.length - 3} more
                </span>
              )}
            </>
          ) : (
            <span className="italic text-[#64748B]">
              No authorized services on file yet.
            </span>
          )}
        </p>
      </section>
    </div>
  );
}

export default TechnicianDashboard;
