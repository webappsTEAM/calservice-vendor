/**
 * CustomerTrackingPage.jsx
 *
 * Standalone, Responsive Full-Page Customer Live Tracking Interface for CalTrack.
 * Mounted at `/track/:jobId` and `/customer/track/:jobId`.
 * Enables real-time tracking, ETA calculation, OTP display, and status updates.
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  MapPin,
  Car,
  Clock,
  Navigation,
  ShieldCheck,
  AlertCircle,
  Phone,
  RefreshCw,
  Search,
  Lock,
  CheckCircle2,
} from 'lucide-react';
import { apiGetCustomerJobTracking } from '../../api/workforceService.js';
import { CustomerTrackingMap } from '../../components/customer/CustomerTrackingMap.jsx';

export function CustomerTrackingPage() {
  const { jobId } = useParams();
  const [trackingData, setTrackingData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const pollTimerRef = useRef(null);

  const fetchTracking = useCallback(async (silent = false) => {
    if (!jobId) return;
    if (!silent) setIsRefreshing(true);
    try {
      const data = await apiGetCustomerJobTracking(jobId);
      setTrackingData(data);
      setError(null);
    } catch (err) {
      if (!silent) {
        setError(err.message || 'Unable to retrieve live tracking session.');
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [jobId]);

  const currentStatus = (trackingData?.status || '').toUpperCase();
  const isTerminal = ['COMPLETED', 'CANCELLED', 'UNABLE_TO_COMPLETE'].includes(currentStatus);

  useEffect(() => {
    fetchTracking(false);
    if (!isTerminal) {
      pollTimerRef.current = setInterval(() => {
        fetchTracking(true);
      }, 5000);
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [fetchTracking, isTerminal]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center text-white font-sans p-4">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-zinc-100 border-t-transparent rounded-full animate-spin" />
          <div className="text-sm font-bold tracking-wide text-zinc-300">Connecting to CalTrack Live GPS Stream...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center text-white font-sans p-4">
        <div className="max-w-md w-full bg-zinc-900 border border-zinc-800 rounded-md p-6 text-center shadow-card">
          <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
          <h2 className="text-base font-bold text-white mb-2">Tracking Session Unavailable</h2>
          <p className="text-xs text-zinc-400 mb-6 leading-relaxed">{error}</p>
          <button
            onClick={() => fetchTracking(false)}
            className="w-full py-2.5 bg-zinc-100 hover:bg-white text-zinc-950 text-xs font-bold rounded-lg transition-all cursor-pointer shadow-xs"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // Terminal State: Service Completed (No Live Map)
  if (currentStatus === 'COMPLETED') {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col font-sans">
        <header className="bg-zinc-900 border-b border-zinc-800 px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center font-black text-white text-sm shadow-xs">
              CT
            </div>
            <div>
              <h1 className="text-sm font-bold text-white">CalTrack Service</h1>
              <p className="text-[10px] text-zinc-400 font-mono">Job #{jobId} • Completed</p>
            </div>
          </div>
        </header>

        <main className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-zinc-900 border border-zinc-800 rounded-md p-6 text-center shadow-card space-y-4">
            <div className="w-14 h-14 bg-emerald-500/10 text-emerald-400 rounded-full flex items-center justify-center mx-auto border border-emerald-500/20">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Service Completed Successfully</h2>
              <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                Your service has been completed by {trackingData?.assigned_technician?.name || 'our verified technician'}.
              </p>
            </div>
            {trackingData?.customer_location?.address && (
              <div className="p-3 bg-zinc-950 rounded-lg border border-zinc-800 text-left text-xs text-zinc-300 flex items-start gap-2">
                <MapPin className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span className="truncate">{trackingData.customer_location.address}</span>
              </div>
            )}
          </div>
        </main>
      </div>
    );
  }

  // Terminal State: Cancelled (No Live Map)
  if (currentStatus === 'CANCELLED') {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col font-sans">
        <header className="bg-zinc-900 border-b border-zinc-800 px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-rose-600 flex items-center justify-center font-black text-white text-sm shadow-xs">
              CT
            </div>
            <div>
              <h1 className="text-sm font-bold text-white">CalTrack Service</h1>
              <p className="text-[10px] text-zinc-400 font-mono">Job #{jobId} • Cancelled</p>
            </div>
          </div>
        </header>

        <main className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-zinc-900 border border-zinc-800 rounded-md p-6 text-center shadow-card space-y-4">
            <div className="w-14 h-14 bg-rose-500/10 text-rose-400 rounded-full flex items-center justify-center mx-auto border border-rose-500/20">
              <AlertCircle className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Service Booking Cancelled</h2>
              <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                This service booking was cancelled. Live vehicle tracking has ended.
              </p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="bg-zinc-900 border-b border-zinc-800 px-6 py-3.5 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-100 text-zinc-950 flex items-center justify-center font-black text-sm tracking-tighter shadow-xs">
            CT
          </div>
          <div>
            <h1 className="text-sm font-bold text-white leading-tight">CalTrack Live Tracking</h1>
            <p className="text-[10px] text-zinc-400 font-mono">Job #{jobId} • Real-time GPS</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchTracking(false)}
            disabled={isRefreshing}
            className="px-3.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 border border-zinc-700 cursor-pointer shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-zinc-300' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </header>

      {/* Main Tracking Content */}
      <main className="flex-1 relative w-full h-[calc(100vh-57px)]">
        <CustomerTrackingMap
          trackingData={trackingData}
          isLoading={isRefreshing}
          onRefresh={() => fetchTracking(false)}
          className="w-full h-full"
        />
      </main>
    </div>
  );
}
