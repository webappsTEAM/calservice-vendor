import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Clock,
  Power,
  Phone,
  CheckCircle2,
  AlertCircle,
  Camera,
  User,
  Zap,
  Play,
  FileText,
  RotateCw,
  MapPin,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  Radio,
  Briefcase,
  Wrench,
  X,
} from 'lucide-react';
import { TechnicianNavigationView } from '../navigation/TechnicianNavigationView.jsx';

/**
 * Real-time Countdown Badge for Offer Expiration & Cancellation Window
 */
function CountdownBadge({ targetTime, prefix = '', expiredText = 'Expired', tone = 'amber' }) {
  const [remaining, setRemaining] = useState(() => {
    if (!targetTime) return 0;
    return Math.max(0, Math.floor((new Date(targetTime).getTime() - Date.now()) / 1000));
  });

  useEffect(() => {
    if (!targetTime) return;
    const interval = setInterval(() => {
      const diff = Math.max(0, Math.floor((new Date(targetTime).getTime() - Date.now()) / 1000));
      setRemaining(diff);
      if (diff <= 0) clearInterval(interval);
    }, 1000);
    return () => clearInterval(interval);
  }, [targetTime]);

  if (remaining <= 0) {
    return (
      <span className="font-mono text-[11px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
        {expiredText}
      </span>
    );
  }

  const mm = String(Math.floor(remaining / 60)).padStart(2, '0');
  const ss = String(remaining % 60).padStart(2, '0');

  const toneStyles = {
    amber: 'bg-amber-100 text-amber-900 border-amber-300',
    rose: 'bg-rose-100 text-rose-900 border-rose-300',
    emerald: 'bg-emerald-100 text-emerald-900 border-emerald-300',
    blue: 'bg-blue-100 text-blue-900 border-blue-300',
  };

  return (
    <span className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${toneStyles[tone] || toneStyles.amber} flex items-center gap-1`}>
      <Clock className="w-3.5 h-3.5" />
      <span>{prefix}{mm}:{ss}</span>
    </span>
  );
}

export function PortalCockpitLayout({
  user,
  employee,
  profile,
  isOnline,
  isTogglingOnline,
  handleToggleOnline,
  timeTracking,
  activeJobs = [],
  completedJobs = [],
  allJobs = [],
  incomingOffers = [],
  activeAssignedJob,
  hasActiveJob,
  liveLocation,
  locationError,
  actionLoading,
  handleAcceptOffer,
  handleRejectOffer,
  handleJobAction,
  handleManualVerifyArrival,
  handleDirectJobClockIn,
  onOpenCancelModal,
  onOpenProofModal,
  preServiceState = {},
  otpInput = '',
  setOtpInput,
  handleVerifyOtpSubmit,
  handleResendOtp,
  openLiveCamera,
  handlePhotoUploadSubmit,
  onRefreshData,
  onClockIn,
  onClockOut,
  onStartBreak,
  onEndBreak,
}) {
  const navigate = useNavigate();
  const [shiftElapsedSeconds, setShiftElapsedSeconds] = useState(0);

  const isClockedIn = Boolean(timeTracking?.is_clocked_in);
  const isBreak = timeTracking?.shift_status === 'on_break';

  // Authoritative Primary Active Job and Incoming Offer Resolution
  const offer = incomingOffers && incomingOffers.length > 0 ? incomingOffers[0] : null;
  const activeJob = activeAssignedJob || (activeJobs && activeJobs.length > 0 ? activeJobs[0] : null);
  const isOffer = Boolean(offer && !activeJob);
  const job = activeJob || offer || null;

  const status = (activeJob?.status || activeJob?.job_status || (offer ? 'OFFERED' : 'STANDBY')).toUpperCase();

  const isAssigned = status === 'ASSIGNED' || status === 'ACCEPTED';
  const isEnRoute = status === 'EN_ROUTE' || status === 'ON_THE_WAY';
  const isArrived = status === 'ARRIVED';
  const isInProgress = status === 'IN_PROGRESS' || status === 'IN_SERVICE' || status === 'INSPECTION';
  const isCompleted = status === 'COMPLETED' || status === 'WORK_COMPLETED';

  // Verification Gate Statuses (All 4 are strictly mandatory for assigned active job)
  const isGeofencePassed = Boolean(preServiceState?.geofence_passed || isArrived || isInProgress || isCompleted);
  const isOtpVerified = Boolean(preServiceState?.otp_verified || isInProgress || isCompleted);
  const isPresencePhotoDone = Boolean(preServiceState?.presence_photo || isInProgress || isCompleted);
  const isWorkAreaPhotoDone = Boolean(preServiceState?.work_area_photo || isInProgress || isCompleted);

  // All 4 required gates must be satisfied to unlock work execution
  const isAllPrerequisitesDone = isGeofencePassed && isOtpVerified && isPresencePhotoDone && isWorkAreaPhotoDone;

  // Shift elapsed timer calculation (Active only after customer OTP is verified / when clocked in)
  useEffect(() => {
    if (!isClockedIn || !timeTracking?.clock_in_time) {
      setShiftElapsedSeconds(0);
      return;
    }
    const startTime = new Date(timeTracking.clock_in_time).getTime();
    const updateElapsed = () => {
      const now = Date.now();
      const diffSecs = Math.max(0, Math.floor((now - startTime) / 1000));
      setShiftElapsedSeconds(diffSecs);
    };
    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    return () => clearInterval(interval);
  }, [isClockedIn, timeTracking?.clock_in_time]);

  const formatElapsed = (totalSecs) => {
    const hours = Math.floor(totalSecs / 3600);
    const minutes = Math.floor((totalSecs % 3600) / 60);
    const seconds = totalSecs % 60;
    if (hours > 0) {
      return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  // Horizontal Stepper Calculation
  const currentStepNum = isCompleted ? 4 : isInProgress ? 4 : isArrived ? 3 : isEnRoute ? 2 : isAssigned ? 1 : 1;

  // Real job metrics (without fake fallback constants)
  const customerPhone = job?.customer_phone || job?.phone || offer?.customer_phone;
  // Bug found: estimated_payout/estimated_price/price are not fields the
  // vendor API returns (WorkforceJobSerializer sends total_amount and a
  // computed payment{amount_due,...} object) -- every alternative here was
  // undefined, so this always rendered a flat ₹0 "EST. PAYOUT" on the
  // technician's home cockpit. Matches the correct pattern already used in
  // EmployeeDashboardPage.jsx and EmployeeJobsPage.jsx.
  const payoutAmount = job?.payment?.amount_due ?? job?.total_amount ?? offer?.payment?.amount_due ?? offer?.total_amount ?? 0;
  const distanceKm = job?.distance_km ?? offer?.distance_km ?? null;

  // Approved services from profile
  const allRequestedServices = profile?.all_requested_services || profile?.bank_details?.onboarding?.services || [];
  const approvedServices = allRequestedServices.filter((s) => s.status === 'approved' || s.is_approved);

  return (
    <div className="w-full h-full flex-1 flex flex-col font-sans bg-slate-100/90 text-slate-900 overflow-hidden p-3 sm:p-4 lg:p-4">
      {/* Bug found: useGPSPosition/useLocationTracker already produce a
          real, user-facing error message per GeolocationPositionError code
          (permission denied, position unavailable, timeout), but
          EmployeeRuntimeProvider only console.warn'd it and this cockpit
          never rendered anything -- a technician whose browser denied
          location access just saw the map/standby view sit there with no
          explanation. Surfaced here, dismissible-by-nature (clears itself
          the moment a position succeeds via locationError=null). */}
      {locationError && (
        <div className="mb-2 flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-300 rounded-xl text-red-900 shrink-0">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span className="text-xs font-semibold">{locationError}</span>
        </div>
      )}
      {/* ── MAIN 2-COLUMN SPLIT WORKSPACE (Elevated Card Layout, Clean Separation from Header) ── */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 min-h-0 bg-white rounded-2xl border border-slate-200/90 shadow-card overflow-hidden">
        {/* ── LEFT COLUMN: FIRST-PERSON DRIVING NAVIGATION / SITE MAP / STANDBY RADAR (7 Cols / 58%) ── */}
        <div className="lg:col-span-7 h-full w-full relative min-h-[420px] lg:min-h-full flex flex-col bg-slate-950 border-b lg:border-b-0 lg:border-r border-slate-200 overflow-hidden">
          <div className="w-full h-full relative flex-1">
            <TechnicianNavigationView
              job={job}
              technicianLocation={liveLocation || user?.last_known_location}
              preServiceState={preServiceState}
              geofenceRadius={250}
              isOnline={isOnline}
            />
          </div>
        </div>

        {/* ── RIGHT COLUMN: JOB CARD, STEPPER & PRE-SERVICE VERIFICATION / STANDBY COCKPIT (5 Cols / 42%) ── */}
        <div className="lg:col-span-5 h-full bg-white flex flex-col justify-between p-5 sm:p-6 overflow-y-auto space-y-4">
          <div className="space-y-4">
            {/* ── TOP SHIFT STATUS BADGE ── */}
            <div className="flex items-center justify-between gap-2 px-3 py-2 bg-slate-50 border border-slate-200/90 rounded-xl shadow-2xs">
              <div className="flex items-center gap-2">
                {isOtpVerified || isClockedIn || isInProgress ? (
                  <>
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                    <span className="text-xs font-black text-emerald-950 uppercase tracking-wider flex items-center gap-1.5">
                      <span>Shift Active:</span>
                      <span className="font-mono text-sm font-black text-emerald-700">{formatElapsed(shiftElapsedSeconds)}</span>
                    </span>
                    {isBreak && (
                      <span className="text-[10px] bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded font-black">
                        PAUSED
                      </span>
                    )}
                  </>
                ) : (
                  <>
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="text-xs font-semibold text-slate-600">
                      Shift Standby (Starts upon Customer OTP)
                    </span>
                  </>
                )}
              </div>

              <button
                type="button"
                onClick={onRefreshData}
                className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-md transition-colors cursor-pointer"
                title="Refresh State"
              >
                <RotateCw className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* ════════════════════════════════════════════════════════════════════════════
                CASE A: NO ACTIVE JOB AND NO INCOMING OFFER (STANDBY / DISPATCH READY MODE)
               ════════════════════════════════════════════════════════════════════════════ */}
            {!job && (
              <div className="space-y-4">
                {/* Standby Header Card */}
                <div className="p-4 rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-slate-100/60 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-black uppercase tracking-wider border ${
                      isOnline
                        ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                        : 'bg-slate-200 text-slate-700 border-slate-300'
                    }`}>
                      {isOnline ? 'ONLINE • READY FOR DISPATCH' : 'OFFLINE'}
                    </span>
                    <span className="text-[11px] font-mono font-bold text-slate-400">
                      {isOnline ? 'RADAR ACTIVE' : 'LOCATION PAUSED'}
                    </span>
                  </div>

                  <div>
                    <h1 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
                      {isOnline ? 'Standby — Waiting for Job Dispatch' : 'You are Currently Offline'}
                    </h1>
                    <p className="text-xs text-slate-600 font-medium mt-1 leading-relaxed">
                      {isOnline
                        ? 'Your location is active and eligible for matching service requests. You will be alerted instantly when a booking is dispatched to you.'
                        : 'Toggle your status to Online at the top right to broadcast your GPS location and receive exclusive jobs.'}
                    </p>
                  </div>
                </div>

                {/* Telemetry & Qualifications Cards */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-white border border-slate-200 rounded-xl space-y-1 shadow-2xs">
                    <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
                      GPS ACCURACY
                    </span>
                    <div className="flex items-center gap-1.5">
                      <Radio className={`w-3.5 h-3.5 ${isOnline ? 'text-emerald-500 animate-pulse' : 'text-slate-400'}`} />
                      <span className="text-xs font-bold text-slate-900">
                        {liveLocation?.accuracy ? `±${Math.round(liveLocation.accuracy)}m Fix` : isOnline ? 'Acquiring...' : 'Inactive'}
                      </span>
                    </div>
                  </div>

                  <div className="p-3 bg-white border border-slate-200 rounded-xl space-y-1 shadow-2xs">
                    <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
                      COMPLETED TODAY
                    </span>
                    <div className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
                      <span className="text-xs font-bold text-slate-900">
                        {completedJobs.length} Job{completedJobs.length === 1 ? '' : 's'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Approved Services / Skills Section */}
                <div className="p-3.5 bg-slate-50 border border-slate-200/90 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Wrench className="w-3.5 h-3.5 text-slate-600" />
                      <span className="text-xs font-bold text-slate-800">
                        Authorized Service Capabilities
                      </span>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      {approvedServices.length} Approved
                    </span>
                  </div>

                  {approvedServices.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {approvedServices.slice(0, 6).map((s, idx) => (
                        <span
                          key={s.id || idx}
                          className="px-2 py-1 bg-white border border-slate-200 rounded-md text-[11px] font-medium text-slate-700 shadow-2xs"
                        >
                          {s.service_title || s.title || s.name || s.category_name}
                        </span>
                      ))}
                      {approvedServices.length > 6 && (
                        <span className="px-2 py-1 bg-slate-100 text-slate-500 rounded-md text-[11px] font-bold">
                          +{approvedServices.length - 6} more
                        </span>
                      )}
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-500">
                      No services configured. Go to Credentials &gt; Services &amp; Skills to request service authorizations.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* ════════════════════════════════════════════════════════════════════════════
                CASE B: INCOMING EXCLUSIVE JOB OFFER OR ACTIVE ASSIGNED JOB
               ════════════════════════════════════════════════════════════════════════════ */}
            {job && (
              <>
                {/* ── TOP JOB CARD ── */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-black uppercase border ${
                      isOffer
                        ? 'bg-amber-100 text-amber-800 border-amber-300'
                        : isArrived
                        ? 'bg-blue-100 text-blue-800 border-blue-300'
                        : isEnRoute
                        ? 'bg-indigo-100 text-indigo-800 border-indigo-300'
                        : isInProgress
                        ? 'bg-purple-100 text-purple-800 border-purple-300'
                        : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    }`}>
                      {isOffer ? 'NEW JOB OFFER' : isArrived ? 'SITE ARRIVAL' : isEnRoute ? 'EN ROUTE' : isInProgress ? 'IN PROGRESS' : 'ACTIVE ASSIGNMENT'}
                    </span>
                    <div className="flex items-center gap-2">
                      {isOffer && (job.offer_expires_at || job.active_offer?.expires_at) && (
                        <CountdownBadge
                          targetTime={job.offer_expires_at || job.active_offer?.expires_at}
                          prefix="Expires in "
                          tone="amber"
                        />
                      )}
                      <span className="font-mono text-xs font-bold text-slate-400">
                        SR-{job.request_id || job.id}
                      </span>
                    </div>
                  </div>

                  <div>
                    <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight leading-tight">
                      {job.service_title || job.service_category || 'Service Request'}
                    </h1>
                    {job.service_description && (
                      <p className="text-xs text-slate-500 font-medium mt-0.5">
                        {job.service_description}
                      </p>
                    )}
                  </div>

                  {/* Metrics Row: Distance & Est Payout */}
                  <div className="flex items-center gap-8 pt-1">
                    <div>
                      <span className="text-[10px] font-mono font-bold uppercase text-slate-400 block tracking-wider">
                        DISTANCE
                      </span>
                      <span className="text-xs font-bold text-slate-900">
                        {distanceKm != null ? `${parseFloat(distanceKm).toFixed(1)} km away` : 'Nearby'}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] font-mono font-bold uppercase text-slate-400 block tracking-wider">
                        EST. PAYOUT
                      </span>
                      <span className="text-sm font-mono font-black text-emerald-700">
                        ₹{Number(payoutAmount).toLocaleString('en-IN')}
                      </span>
                    </div>
                  </div>

                  {/* Offer Action Buttons (Decline / Accept Job) */}
                  {isOffer && (
                    <div className="grid grid-cols-2 gap-3 pt-2">
                      <button
                        type="button"
                        onClick={() => handleRejectOffer(job.id)}
                        disabled={actionLoading}
                        className="py-2.5 px-4 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs rounded-lg transition-all cursor-pointer shadow-2xs text-center"
                      >
                        Decline
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAcceptOffer(job.id)}
                        disabled={actionLoading}
                        className="py-2.5 px-4 bg-[#2d6a4f] hover:bg-[#1b4332] text-white font-black text-xs rounded-lg shadow-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <Zap className="w-3.5 h-3.5 fill-current" />
                        <span>Accept Job</span>
                      </button>
                    </div>
                  )}

                  {/* Active Accepted Job: Cancellation Button (Available before Customer OTP) */}
                  {!isOffer && job && !isOtpVerified && !isInProgress && !isCompleted && (
                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={() => onOpenCancelModal && onOpenCancelModal(job)}
                        className="w-full py-2.5 px-4 bg-rose-50 hover:bg-rose-100 active:bg-rose-200 text-rose-700 border border-rose-300 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-2xs"
                      >
                        <X className="w-4 h-4 text-rose-600 shrink-0" />
                        <span>Cancel Assignment (Available before Customer OTP)</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* ── HORIZONTAL STEPPER LINE (Accepted ── En Route ── Arrived) (For Active Assigned Job) ── */}
                {!isOffer && (
                  <div className="pt-2 border-t border-slate-100">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-600">
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        <span className="text-slate-800">Accepted</span>
                      </div>
                      <div className="flex-1 h-0.5 bg-slate-200 mx-3" />
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2 className={`w-4 h-4 ${currentStepNum >= 2 ? 'text-emerald-600' : 'text-slate-300'}`} />
                        <span className={currentStepNum >= 2 ? 'text-slate-800' : 'text-slate-400'}>En Route</span>
                      </div>
                      <div className="flex-1 h-0.5 bg-slate-200 mx-3" />
                      <div className="flex items-center gap-1.5">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-black ${
                          currentStepNum >= 3 ? 'bg-slate-950 text-white' : 'bg-slate-200 text-slate-500'
                        }`}>
                          3
                        </div>
                        <span className={currentStepNum >= 3 ? 'text-slate-950 font-black' : 'text-slate-400'}>Arrived</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── PRE-SERVICE VERIFICATION SECTION (Only for Active Assigned Job prior to completion) ── */}
                {!isOffer && (
                  <div className="pt-2 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-slate-700" />
                        <h2 className="text-sm font-black text-slate-900 tracking-tight">
                          Pre-Service Verification
                        </h2>
                      </div>
                      <span className="text-[10px] font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                        All Fields Required *
                      </span>
                    </div>

                    {/* 1. Location Check-In (≤250m) * (Required) */}
                    <div className={`p-3.5 rounded-xl border space-y-1 transition-all ${
                      isGeofencePassed ? 'bg-emerald-50/40 border-emerald-300' : 'bg-white border-slate-200'
                    }`}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900 flex items-center gap-1">
                          <span>1. Location Check-In (≤250m)</span>
                          <span className="text-rose-600">*</span>
                        </span>
                        {isGeofencePassed ? (
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-bold rounded text-[11px]">
                            Verified ✓
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleManualVerifyArrival(job)}
                            disabled={actionLoading}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded text-[11px] cursor-pointer"
                          >
                            Verify GPS
                          </button>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Technician GPS coordinates verified within customer site geofence.
                      </p>
                    </div>

                    {/* 2. Customer Start OTP * (Required) */}
                    <div className={`p-3.5 rounded-xl border space-y-2 transition-all ${
                      isOtpVerified ? 'bg-emerald-50/40 border-emerald-300' : 'bg-white border-slate-200'
                    }`}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900 flex items-center gap-1">
                          <span>2. Customer Start OTP</span>
                          <span className="text-rose-600">*</span>
                        </span>
                        {isOtpVerified ? (
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-bold rounded text-[11px]">
                            Verified ✓
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleResendOtp(job)}
                            className="text-[11px] font-bold text-slate-600 hover:text-slate-900 cursor-pointer"
                          >
                            Resend OTP
                          </button>
                        )}
                      </div>

                      {isOtpVerified ? (
                        <p className="text-[11px] text-emerald-700 font-bold">
                          Customer start code verified successfully.
                        </p>
                      ) : (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            maxLength={6}
                            value={otpInput || ''}
                            onChange={(e) => setOtpInput(e.target.value)}
                            placeholder="4-digit OTP *"
                            className="flex-1 px-3 py-2 bg-slate-100/90 border border-slate-200 rounded-lg text-xs font-mono font-bold text-slate-900 outline-none focus:bg-white focus:border-slate-400"
                          />
                          <button
                            type="button"
                            onClick={() => handleVerifyOtpSubmit(job)}
                            disabled={actionLoading || !otpInput}
                            className="px-5 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold text-xs rounded-lg transition-all cursor-pointer disabled:opacity-50"
                          >
                            Verify
                          </button>
                        </div>
                      )}
                    </div>

                    {/* 3. Pre-Service Diagnostic Photos * (Both Required) */}
                    <div className={`p-3.5 rounded-xl border space-y-2.5 transition-all ${
                      isPresencePhotoDone && isWorkAreaPhotoDone ? 'bg-emerald-50/40 border-emerald-300' : 'bg-white border-slate-200'
                    }`}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900 flex items-center gap-1">
                          <span>3. Pre-Service Diagnostic Photos</span>
                          <span className="text-rose-600">*</span>
                        </span>
                        <span className="text-[10px] text-slate-400 font-bold">
                          {isPresencePhotoDone && isWorkAreaPhotoDone ? '2/2 Uploaded ✓' : `${(isPresencePhotoDone ? 1 : 0) + (isWorkAreaPhotoDone ? 1 : 0)}/2 Complete`}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        {/* Box 1: Technician Selfie * (Required) */}
                        <button
                          type="button"
                          onClick={() => {
                            if (openLiveCamera) {
                              openLiveCamera('Capture Presence Selfie', 'user', 'presence_selfie', (file) => handlePhotoUploadSubmit('presence', file, job));
                            }
                          }}
                          className={`border-2 border-dashed rounded-xl p-3.5 flex flex-col items-center justify-center gap-1.5 text-center transition-all cursor-pointer ${
                            isPresencePhotoDone
                              ? 'border-emerald-400 bg-emerald-50/50 text-emerald-800'
                              : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                          }`}
                        >
                          <User className="w-5 h-5 text-slate-500" />
                          <span className="font-mono text-[10px] font-bold">
                            {isPresencePhotoDone ? 'Selfie Uploaded ✓' : 'Tech Selfie *'}
                          </span>
                        </button>

                        {/* Box 2: Work Area Photo * (Required) */}
                        <button
                          type="button"
                          onClick={() => {
                            if (openLiveCamera) {
                              openLiveCamera('Capture Work Area Photo', 'environment', 'pre_work_area', (file) => handlePhotoUploadSubmit('work_area', file, job));
                            }
                          }}
                          className={`border-2 border-dashed rounded-xl p-3.5 flex flex-col items-center justify-center gap-1.5 text-center transition-all cursor-pointer ${
                            isWorkAreaPhotoDone
                              ? 'border-emerald-400 bg-emerald-50/50 text-emerald-800'
                              : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                          }`}
                        >
                          <Camera className="w-5 h-5 text-slate-500" />
                          <span className="font-mono text-[10px] font-bold">
                            {isWorkAreaPhotoDone ? 'Work Area Uploaded ✓' : 'Work Area *'}
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* ── BOTTOM ACTION BUTTON: Start Service Execution / Complete Service (Only when active job exists) ── */}
          {activeJob && !isOffer && (
            <div className="pt-2 border-t border-slate-100 space-y-1.5">
              {isInProgress ? (
                <button
                  type="button"
                  onClick={() => onOpenProofModal && onOpenProofModal(activeJob)}
                  disabled={actionLoading}
                  className="w-full py-3.5 rounded-xl font-black text-xs transition-all flex items-center justify-center gap-2 bg-[#2d6a4f] hover:bg-[#1b4332] active:bg-[#153427] text-white shadow-md cursor-pointer"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Complete Service &amp; Submit Proof</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => handleJobAction(activeJob.id, 'IN_PROGRESS')}
                  disabled={actionLoading || !isAllPrerequisitesDone}
                  className={`w-full py-3.5 rounded-xl font-black text-xs transition-all flex items-center justify-center gap-2 ${
                    isAllPrerequisitesDone
                      ? 'bg-[#2d6a4f] hover:bg-[#1b4332] active:bg-[#153427] text-white shadow-md cursor-pointer'
                      : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  }`}
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>
                    {isAllPrerequisitesDone
                      ? 'Start Service Execution'
                      : 'Start Service Execution (Fill All 4 Required Gates Above)'}
                  </span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PortalCockpitLayout;
