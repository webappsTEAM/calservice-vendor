/**
 * TechnicianNavigationView.jsx
 *
 * Authoritative Field Technician Navigation State Router for CalTrack.
 *
 * Explicit Job Status Mapping:
 *  - 'accepted'    -> TechnicianFirstPersonNavView (Pre-travel / First-Person Turn-by-Turn Navigation)
 *  - 'on_the_way'  -> TechnicianFirstPersonNavView (Active First-Person Turn-by-Turn Driving Navigation)
 *  - 'arrived'     -> TechnicianArrivalView (Contextual 2D Arrival Map + 300m Geofence + Call Customer)
 *  - 'in_progress' -> null (EmployeeDashboardPage renders ClockInCard, work timer, scope extensions & post-service proof)
 *  - 'completed'   -> null (EmployeeDashboardPage renders settlement & completion summary)
 *  - 'cancelled'   -> null (EmployeeDashboardPage renders cancellation notice / available state)
 *  - other         -> null (No fallback assumptions)
 */

import React from 'react';
import {
  CheckCircle2,
  Clock,
  MapPin,
  Phone,
  ShieldCheck,
  Banknote,
  XCircle,
} from 'lucide-react';
import { TechnicianFirstPersonNavView } from './TechnicianFirstPersonNavView.jsx';
import { TechnicianArrivalView } from './TechnicianArrivalView.jsx';
import { TechnicianStandbyMapView } from './TechnicianStandbyMapView.jsx';

function TechnicianExecutionStateView({ job, status, technicianLocation }) {
  const customerName = job?.customer_name || 'Customer';
  const customerPhone = job?.phone || job?.customer_phone;
  const customerAddress = job?.address || job?.customer_address || 'Authorized Site Address';
  const paymentMethod = (job?.payment_method || 'COD').toUpperCase();
  const paymentStatus = (job?.payment_status || 'PENDING').toUpperCase();
  const amount = job?.total_amount != null ? `₹${Number(job.total_amount).toLocaleString('en-IN')}` : '—';
  const isCod = paymentMethod === 'COD' || paymentMethod === 'CASH_ON_SERVICE';

  if (status === 'proof_submitted') {
    return (
      <div className="h-full w-full bg-gradient-to-br from-slate-900 via-slate-950 to-emerald-950 text-white p-6 flex flex-col justify-between overflow-y-auto">
        <div className="space-y-6">
          {/* Status Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold uppercase tracking-wider">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Proof Submitted & Recorded</span>
            </div>
            <span className="text-xs text-slate-400 font-mono font-bold">
              #{job?.request_id || job?.id}
            </span>
          </div>

          <div>
            <h2 className="text-2xl font-black text-white tracking-tight">
              Service Proof Submitted
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Photos and delivery evidence have been uploaded to dispatch.
            </p>
          </div>

          {/* Payment & Next Action Card */}
          <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/15 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Banknote className="w-5 h-5 text-emerald-400" />
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Payment Status
                </span>
              </div>
              <span className={`text-xs font-black px-2.5 py-1 rounded-full ${
                paymentStatus === 'PAID'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              }`}>
                {paymentStatus}
              </span>
            </div>

            <div className="flex items-baseline justify-between">
              <span className="text-sm text-slate-300 font-medium">Payable Amount</span>
              <span className="text-2xl font-black text-white">{amount}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/10 text-xs space-y-1">
              <p className="font-bold text-slate-200">Next Permitted Step:</p>
              {isCod && paymentStatus !== 'PAID' ? (
                <p className="text-slate-400 leading-relaxed">
                  Collect cash from customer ({amount}), enter customer confirmation OTP, then complete the job in the cockpit panel.
                </p>
              ) : (
                <p className="text-slate-400 leading-relaxed">
                  Payment is verified online. Confirm completion in the right cockpit panel to finalize settlement.
                </p>
              )}
            </div>
          </div>

          {/* Location & Customer summary */}
          <div className="bg-white/5 rounded-xl border border-white/10 p-4 space-y-3">
            <div className="flex items-start gap-3 text-xs">
              <MapPin className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-slate-200">Site Destination</p>
                <p className="text-slate-400 mt-0.5 leading-snug">{customerAddress}</p>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs pt-2 border-t border-white/10">
              <span className="text-slate-400">Customer: <strong className="text-slate-200">{customerName}</strong></span>
              {customerPhone && (
                <a
                  href={`tel:${customerPhone}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition-colors"
                >
                  <Phone className="w-3.5 h-3.5" /> Call Customer
                </a>
              )}
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> Authorized Workforce Session
          </span>
          <span>Awaiting Final Completion</span>
        </div>
      </div>
    );
  }

  if (status === 'in_progress') {
    return (
      <div className="h-full w-full bg-gradient-to-br from-slate-900 via-slate-950 to-blue-950 text-white p-6 flex flex-col justify-between overflow-y-auto">
        <div className="space-y-6">
          {/* Status Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/20 border border-blue-500/40 text-blue-300 text-xs font-bold uppercase tracking-wider">
              <Clock className="w-4 h-4 text-blue-400" />
              <span>Service In Progress</span>
            </div>
            <span className="text-xs text-slate-400 font-mono font-bold">
              #{job?.request_id || job?.id}
            </span>
          </div>

          <div>
            <h2 className="text-2xl font-black text-white tracking-tight">
              Executing Job On-Site
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Deliver cargo or perform service tasks. Clock-in is active.
            </p>
          </div>

          {/* Details Card */}
          <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/15 p-5 space-y-4">
            <div className="flex items-start gap-3">
              <MapPin className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-slate-300 uppercase tracking-wider">Destination</p>
                <p className="text-sm text-white font-medium mt-0.5 leading-snug">{customerAddress}</p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-white/10 text-xs space-y-1">
              <p className="font-bold text-slate-200">Next Permitted Step:</p>
              <p className="text-slate-400 leading-relaxed">
                Once goods are handed over or service is completed, take completion photos in the right cockpit panel to submit proof.
              </p>
            </div>
          </div>

          {/* Customer contact */}
          <div className="bg-white/5 rounded-xl border border-white/10 p-4 flex items-center justify-between text-xs">
            <div>
              <p className="text-slate-400">Customer</p>
              <p className="font-bold text-slate-100 mt-0.5">{customerName}</p>
            </div>
            {customerPhone && (
              <a
                href={`tel:${customerPhone}`}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition-colors"
              >
                <Phone className="w-3.5 h-3.5" /> Call Customer
              </a>
            )}
          </div>
        </div>

        <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-blue-400" /> On-Site Clock Active
          </span>
          <span>Submit Proof when Finished</span>
        </div>
      </div>
    );
  }

  if (status === 'completed') {
    return (
      <div className="h-full w-full bg-gradient-to-br from-slate-900 via-slate-950 to-emerald-950 text-white p-6 flex flex-col justify-between overflow-y-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold uppercase tracking-wider">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Job Completed</span>
            </div>
            <span className="text-xs text-slate-400 font-mono font-bold">
              #{job?.request_id || job?.id}
            </span>
          </div>

          <div>
            <h2 className="text-2xl font-black text-white tracking-tight">
              All Tasks Finished
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              Proof submitted, payment processed, and milestone completed.
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/15 p-5 space-y-3">
            <div className="flex justify-between items-center text-sm">
              <span className="text-slate-300">Total Fare:</span>
              <span className="text-xl font-black text-white">{amount}</span>
            </div>
            <div className="flex justify-between items-center text-xs text-slate-300 pt-2 border-t border-white/10">
              <span>Status:</span>
              <span className="font-bold text-emerald-400">Settled / Closed</span>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Shift Active
          </span>
          <span>Ready for Next Job</span>
        </div>
      </div>
    );
  }

  if (status === 'cancelled') {
    return (
      <div className="h-full w-full bg-gradient-to-br from-slate-900 via-slate-950 to-rose-950 text-white p-6 flex flex-col justify-between overflow-y-auto">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 text-xs font-bold uppercase tracking-wider">
              <XCircle className="w-4 h-4 text-rose-400" />
              <span>Assignment Cancelled</span>
            </div>
            <span className="text-xs text-slate-400 font-mono font-bold">
              #{job?.request_id || job?.id}
            </span>
          </div>

          <div>
            <h2 className="text-2xl font-black text-white tracking-tight">
              Job Cancelled
            </h2>
            <p className="text-sm text-slate-300 mt-1">
              This assignment was cancelled and returned to the dispatch queue.
            </p>
          </div>
        </div>

        <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-400">
          <span>Standing: Available</span>
          <span>Listening for new dispatches</span>
        </div>
      </div>
    );
  }

  return (
    <TechnicianStandbyMapView
      technicianLocation={technicianLocation}
      isOnline={true}
    />
  );
}

export function TechnicianNavigationView({
  job,
  technicianLocation,
  preServiceState = {},
  geofenceRadius = 250,
  onLocationReport,
  onExitNavigation,
  isOnline = true,
}) {
  const status = job?.status;

  if (!job) {
    return (
      <TechnicianStandbyMapView
        technicianLocation={technicianLocation}
        isOnline={isOnline}
        onLocationReport={onLocationReport}
      />
    );
  }

  switch (status) {
    case 'accepted':
    case 'on_the_way':
      return (
        <TechnicianFirstPersonNavView
          job={job}
          technicianLocation={technicianLocation}
          preServiceState={preServiceState}
          geofenceRadius={geofenceRadius}
          onLocationReport={onLocationReport}
          onExitNavigation={onExitNavigation}
        />
      );

    case 'arrived':
      return (
        <TechnicianArrivalView
          job={job}
          technicianLocation={technicianLocation}
          geofenceRadius={geofenceRadius}
        />
      );

    case 'in_progress':
    case 'proof_submitted':
    case 'completed':
    case 'cancelled':
      return (
        <TechnicianExecutionStateView
          job={job}
          status={status}
          technicianLocation={technicianLocation}
        />
      );

    default:
      return (
        <TechnicianStandbyMapView
          technicianLocation={technicianLocation}
          isOnline={isOnline}
          onLocationReport={onLocationReport}
        />
      );
  }
}
