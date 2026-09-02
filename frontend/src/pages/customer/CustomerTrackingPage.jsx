/**
 * CustomerTrackingPage.jsx
 *
 * Standalone, Responsive Full-Page Customer Live Tracking Interface for CalTrack.
 * Mounted at `/track/:jobId` and `/customer/track/:jobId`.
 * Enables real-time tracking, ETA calculation, OTP display, and status updates.
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
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
import { getAccessToken } from '../../utils/authTokens.js';

export function CustomerTrackingPage() {
  const { jobId } = useParams();
  const [searchParams] = useSearchParams();
  const [trackingData, setTrackingData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [isSseActive, setIsSseActive] = useState(false);

  const sseRef = useRef(null);
  const pollTimerRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const isMountedRef = useRef(true);

  // Fetch authoritative snapshot via REST API
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

  // Fallback Polling Control: Only active when SSE is disconnected
  const startFallbackPolling = useCallback(() => {
    if (pollTimerRef.current || isTerminal) return;
    console.info('[CustomerTracking] SSE disconnected. Activating 5-second REST fallback polling.');
    pollTimerRef.current = setInterval(() => {
      if (!isMountedRef.current) return;
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      fetchTracking(true);
    }, 5000);
  }, [fetchTracking, isTerminal]);

  const stopFallbackPolling = useCallback(() => {
    if (pollTimerRef.current) {
      console.info('[CustomerTracking] SSE healthy. Stopping 5-second fallback REST polling.');
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  // Update technician coordinates in-place without page reload
  const handleLocationEvent = useCallback((loc) => {
    if (!loc) return;
    const lat = loc.latitude ?? loc.lat ?? loc.employee_location?.latitude;
    const lon = loc.longitude ?? loc.lng ?? loc.lon ?? loc.employee_location?.longitude;
    if (lat == null || lon == null) return;

    setTrackingData((prev) => {
      if (!prev) return prev;
      const accuracy = loc.accuracy ?? loc.employee_location?.accuracy ?? prev.assigned_technician?.location?.accuracy;
      const speed = loc.speed ?? loc.employee_location?.speed ?? prev.assigned_technician?.location?.speed;
      const heading = loc.heading ?? loc.employee_location?.heading ?? prev.assigned_technician?.location?.heading;
      const capturedAt = loc.captured_at ?? loc.timestamp ?? new Date().toISOString();

      return {
        ...prev,
        status: (loc.status || prev.status).toUpperCase(),
        distance_m: loc.distance_m ?? prev.distance_m,
        distance_km: loc.distance_km ?? prev.distance_km,
        geofence_status: loc.geofence_status ?? prev.geofence_status,
        movement_status: loc.movement_status ?? prev.movement_status,
        freshness_state: loc.freshness_state ?? 'LIVE',
        assigned_technician: prev.assigned_technician
          ? {
              ...prev.assigned_technician,
              location: {
                latitude: Number(lat),
                longitude: Number(lon),
                accuracy: accuracy != null ? Number(accuracy) : null,
                speed: speed != null ? Number(speed) : null,
                heading: heading != null ? Number(heading) : null,
                captured_at: capturedAt,
                received_at: new Date().toISOString(),
              },
            }
          : prev.assigned_technician,
      };
    });
  }, []);

  // Establish SSE stream
  const connectSSE = useCallback(() => {
    if (!jobId || isTerminal) return;
    if (sseRef.current) {
      try { sseRef.current.close(); } catch (_) {}
      sseRef.current = null;
    }

    const token = getAccessToken() || '';
    const trackingToken = searchParams.get('token') || searchParams.get('tracking_token') || '';
    const params = new URLSearchParams();
    params.set('job_id', jobId);
    if (token) params.set('token', token);
    if (trackingToken) params.set('tracking_token', trackingToken);

    const sseUrl = `/api/workforce/realtime/stream/?${params.toString()}`;
    console.info(`[CustomerTracking] Connecting to live SSE stream: ${sseUrl}`);
    const es = new EventSource(sseUrl);
    sseRef.current = es;

    es.addEventListener('ping', () => {
      if (!isMountedRef.current) return;
      setIsSseActive(true);
      stopFallbackPolling();
      if (reconnectAttemptsRef.current > 0) {
        console.info('[CustomerTracking] SSE reconnected. Fetching fresh state once.');
        fetchTracking(true);
      }
      reconnectAttemptsRef.current = 0;
    });

    es.addEventListener('job_location', (e) => {
      if (!isMountedRef.current) return;
      setIsSseActive(true);
      stopFallbackPolling();
      try {
        const payload = JSON.parse(e.data);
        handleLocationEvent(payload);
      } catch (err) {
        console.warn('[CustomerTracking] Error parsing job_location event:', err);
      }
    });

    es.addEventListener('workforce_event', (e) => {
      if (!isMountedRef.current) return;
      try {
        const ev = JSON.parse(e.data);
        if (ev.event_type === 'JOB_LOCATION_UPDATE' && ev.payload) {
          handleLocationEvent(ev.payload);
        }
      } catch (_) {}
    });

    es.onerror = () => {
      if (!isMountedRef.current) return;
      console.warn('[CustomerTracking] SSE stream dropped. Starting fallback polling & reconnecting.');
      setIsSseActive(false);
      startFallbackPolling();

      try { es.close(); } catch (_) {}
      sseRef.current = null;

      // Exponential backoff reconnect: 2s, 4s, 8s, max 15s
      reconnectAttemptsRef.current += 1;
      const delay = Math.min(15000, Math.pow(2, reconnectAttemptsRef.current) * 1000);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = setTimeout(() => {
        if (isMountedRef.current && !isTerminal) {
          connectSSE();
        }
      }, delay);
    };
  }, [jobId, isTerminal, searchParams, fetchTracking, handleLocationEvent, startFallbackPolling, stopFallbackPolling]);

  // Master Lifecycle: Load REST state once, establish SSE, clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;
    // 1. Initial REST fetch
    fetchTracking(false);

    // 2. Establish SSE connection
    if (!isTerminal) {
      connectSSE();
    }

    return () => {
      isMountedRef.current = false;
      if (sseRef.current) {
        try { sseRef.current.close(); } catch (_) {}
        sseRef.current = null;
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [jobId, isTerminal]);

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
