/**
 * EmployeeRuntimeProvider.jsx
 *
 * Single persistent session runtime for the CalTrack Workforce employee application.
 * Incorporates all Six Architecture Corrections:
 * 1. ONE Authoritative GPS Implementation (session-level useLocationTracker)
 * 2. Separate Presence State from GPS State (OFFLINE -> CONNECTING -> ONLINE_LOCATION_PENDING -> ONLINE_GPS_LIVE)
 * 3. Provider Ownership as the Primary GPS/Realtime Guard
 * 4. Zero Customer Impact & Preserved API Contracts
 * 5. Workforce-Side Shared DB Testing
 * 6. Stale-While-Revalidate Active Job Cache + Out-of-Order Generation Protection
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from './AuthProvider.jsx';
import { EmployeeRuntimeContext, ACTIVE_QUEUE_STATUSES } from './EmployeeRuntimeContext.jsx';
import {
  apiGetWorkforceJobs,
  apiGetNotifications,
  apiMarkNotificationRead,
  apiClearNotifications,
  apiUpdateLocationFull,
} from '../api/workforceService.js';
import { useLocationTracker, getGPSPosition } from '../hooks/useGPSPosition.js';
import { useRealtimeStream } from '../hooks/useRealtimeStream.js';

export const isJobOffer = (j) => {
  if (!j) return false;
  if (j.is_accepted_by_current_employee || j.is_assigned_to_current_employee) {
    return false;
  }
  if (j.is_offer === true) return true;
  const offerStatus = (j.offer_status || '').toUpperCase();
  if (offerStatus === 'OFFERED') return true;
  if (j.active_offer && (j.active_offer.status || '').toUpperCase() === 'OFFERED') {
    const isEst = Boolean(
      j.is_estimation ||
      (j.pricing_mode || '').toUpperCase() === 'QUOTATION' ||
      (j.job_type || '').toUpperCase() === 'ESTIMATION' ||
      (j.request_kind || '').toLowerCase() === 'estimation' ||
      (j.request_kind || '').toLowerCase() === 'inspection' ||
      j.estimation_details
    );
    if (isEst) return true;
    return !j.active_offer.is_expired;
  }
  const status = (j.status || j.job_status || '').toUpperCase();
  if (['OFFERED'].includes(status)) return true;
  return false;
};

export function EmployeeRuntimeProvider({ children }) {
  const { user, isEmployee, registrationStatus, togglePresence: authTogglePresence, logout, isAuthenticated } = useAuth();

  const isApprovedEmployee = Boolean(user && isEmployee && registrationStatus === 'approved');
  const isOnlineAuth = Boolean(user?.isOnline);

  // ── 1. Presence & GPS State Machine (Correction 2) ──────────────────────────
  // States: 'OFFLINE' | 'CONNECTING' | 'ONLINE_LOCATION_PENDING' | 'ONLINE_GPS_LIVE'
  const [presenceState, setPresenceState] = useState(() => {
    if (!isOnlineAuth) return 'OFFLINE';
    const loc = user?.last_known_location;
    if (loc?.latitude && loc?.longitude) return 'ONLINE_GPS_LIVE';
    return 'ONLINE_LOCATION_PENDING';
  });

  const isOnline = presenceState !== 'OFFLINE' && presenceState !== 'CONNECTING';
  const isGpsLive = presenceState === 'ONLINE_GPS_LIVE';
  const isLocationPending = presenceState === 'ONLINE_LOCATION_PENDING';

  useEffect(() => {
    if (!isOnlineAuth) {
      setPresenceState('OFFLINE');
    } else {
      setPresenceState((prev) => (prev === 'OFFLINE' ? 'ONLINE_LOCATION_PENDING' : prev));
    }
  }, [isOnlineAuth]);

  // ── 2. Jobs State & Cache (Correction 6: Stale-While-Revalidate) ─────────────
  const [activeJobs, setActiveJobs] = useState([]);
  const [completedJobs, setCompletedJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [isJobsLoading, setIsJobsLoading] = useState(false);
  const [isCompletedLoading, setIsCompletedLoading] = useState(false);
  const [jobsError, setJobsError] = useState(null);

  // Sequence versioning to prevent out-of-order stale responses
  const fetchGenerationRef = useRef(0);
  const inFlightActiveJobsPromiseRef = useRef(null);
  const inFlightCompletedJobsPromiseRef = useRef(null);
  const activeJobsRef = useRef([]);
  const selectedJobRef = useRef(null);
  const debounceTimerRef = useRef(null);

  useEffect(() => {
    activeJobsRef.current = activeJobs;
  }, [activeJobs]);

  useEffect(() => {
    selectedJobRef.current = selectedJob;
  }, [selectedJob]);

  // Derived active workload state
  const hasActiveJob = useMemo(() => {
    return activeJobs.some((j) => {
      const st = (j.status || j.job_status || '').toLowerCase();
      const isAssigned = Boolean(j.is_assigned_to_current_employee || j.assigned_employee_id === user?.id);
      return isAssigned && ACTIVE_QUEUE_STATUSES.includes(st);
    });
  }, [activeJobs, user?.id]);

  const incomingOffers = useMemo(() => {
    return activeJobs.filter(isJobOffer);
  }, [activeJobs]);

  const incomingOffer = useMemo(() => {
    return incomingOffers[0] || null;
  }, [incomingOffers]);

  // ── 3. Notification Deduplication ──────────────────────────────────────────
  const knownOfferIdsRef = useRef(new Set());
  const isInitialOffersLoadedRef = useRef(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // Request browser notification permission once when online
  useEffect(() => {
    if (isOnline && typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {});
    }
  }, [isOnline]);

  const triggerOfferBrowserNotification = useCallback((offeredJob) => {
    if (!offeredJob) return;
    const offerId = offeredJob.active_offer?.id || offeredJob.offer_id || `job_${offeredJob.id}`;

    // Deduplication check: only notify if this offer ID has never been notified
    if (knownOfferIdsRef.current.has(offerId)) {
      return;
    }
    knownOfferIdsRef.current.add(offerId);

    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      try {
        const title = '⚡ New Exclusive Job Offer!';
        const body = `Job #${offeredJob.request_id || offeredJob.id}: ${
          offeredJob.service_title || offeredJob.service_category || 'Service Request'
        }. Tap to review and accept.`;
        new Notification(title, {
          body,
          icon: '/favicon.ico',
          tag: `offer_${offerId}`, // Browser-level tag deduplication
        });
      } catch (_) {}
    }
  }, []);

  // ── 4. Single-Flight Stale-While-Revalidate Active Jobs Refresh ──────────────
  const refreshActiveJobs = useCallback(
    async (options = {}) => {
      const isSilent = options?.silent === true;
      const force = options?.force === true;

      // Request Coalescing: Return existing in-flight Promise if one is running
      if (inFlightActiveJobsPromiseRef.current && !force) {
        return inFlightActiveJobsPromiseRef.current;
      }

      if (!isSilent && activeJobsRef.current.length === 0) {
        setIsJobsLoading(true);
      }
      setJobsError(null);

      // Track request generation sequence
      const currentGen = ++fetchGenerationRef.current;

      const fetchPromise = (async () => {
        try {
          // Query active jobs from backend
          const jobsData = await apiGetWorkforceJobs('active');

          // Out-of-order response check: discard if a newer fetch was initiated
          if (currentGen < fetchGenerationRef.current) {
            console.info(`[EmployeeRuntime] Discarding stale active jobs response (gen #${currentGen} < #${fetchGenerationRef.current})`);
            return activeJobsRef.current;
          }

          if (Array.isArray(jobsData)) {
            setActiveJobs(jobsData);

            // Seed initial offer IDs so historical offers do not trigger browser alerts
            const currentOffers = jobsData.filter(isJobOffer);
            if (currentOffers.length > 0) {
              currentOffers.forEach((offer) => {
                const offerId = offer.active_offer?.id || offer.offer_id || `job_${offer.id}`;
                if (!isInitialOffersLoadedRef.current) {
                  knownOfferIdsRef.current.add(offerId);
                } else {
                  triggerOfferBrowserNotification(offer);
                }
              });
              isInitialOffersLoadedRef.current = true;
            } else {
              isInitialOffersLoadedRef.current = true;
            }

            // Smart reconciliation of selectedJob without resetting selection
            setSelectedJob((prev) => {
              if (!prev) {
                if (currentOffers[0]) return currentOffers[0];
                const active = jobsData.find((j) =>
                  ACTIVE_QUEUE_STATUSES.includes((j.status || j.job_status || '').toLowerCase())
                );
                return active || null;
              }
              const updated = jobsData.find((j) => j.id === prev.id);
              return updated || null;
            });
            return jobsData;
          }
          return activeJobsRef.current;
        } catch (err) {
          // CRITICAL: On transient failure, preserve last known valid state. Never set to []!
          console.warn('[EmployeeRuntime] Background active jobs refresh error:', err);
          setJobsError(err.message || 'Unable to update jobs.');
          return activeJobsRef.current;
        } finally {
          setIsJobsLoading(false);
          inFlightActiveJobsPromiseRef.current = null;
        }
      })();

      inFlightActiveJobsPromiseRef.current = fetchPromise;
      return fetchPromise;
    },
    [triggerOfferBrowserNotification]
  );

  // ── 5. Lazy Completed Jobs Fetch ───────────────────────────────────────────
  const refreshCompletedJobs = useCallback(async (options = {}) => {
    const isSilent = options?.silent === true;
    if (inFlightCompletedJobsPromiseRef.current) {
      return inFlightCompletedJobsPromiseRef.current;
    }

    if (!isSilent) setIsCompletedLoading(true);

    const fetchPromise = (async () => {
      try {
        const completedData = await apiGetWorkforceJobs('completed');
        if (Array.isArray(completedData)) {
          setCompletedJobs(completedData);
          return completedData;
        }
        return [];
      } catch (err) {
        console.warn('[EmployeeRuntime] Completed jobs fetch error:', err);
        return [];
      } finally {
        setIsCompletedLoading(false);
        inFlightCompletedJobsPromiseRef.current = null;
      }
    })();

    inFlightCompletedJobsPromiseRef.current = fetchPromise;
    return fetchPromise;
  }, []);

  // Debounced coalesced active jobs refresh helper
  const scheduleCoalescedRefresh = useCallback(
    (delayMs = 400) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(() => {
        refreshActiveJobs({ silent: true });
      }, delayMs);
    },
    [refreshActiveJobs]
  );

  // ── 6. Centralized Notification Synchronization ────────────────────────────
  const syncNotifications = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const res = await apiGetNotifications();
      if (res) {
        setNotifications(res.notifications || []);
        setUnreadCount(res.unread_count || 0);
      }
    } catch (_) {}
  }, [isAuthenticated]);

  const markNotificationAsRead = useCallback(
    async (notificationId = null) => {
      try {
        await apiMarkNotificationRead(notificationId);
        await syncNotifications();
      } catch (_) {}
    },
    [syncNotifications]
  );

  const clearAllNotifications = useCallback(
    async (notificationIds = []) => {
      try {
        await apiClearNotifications(notificationIds);
        await syncNotifications();
      } catch (_) {}
    },
    [syncNotifications]
  );

  // Initial load on authentication
  useEffect(() => {
    if (isAuthenticated && isApprovedEmployee) {
      refreshActiveJobs();
      syncNotifications();
    }
  }, [isAuthenticated, isApprovedEmployee, refreshActiveJobs, syncNotifications]);

  // ── 7. Single Authoritative Live GPS Watcher (Correction 1 & 3) ────────────
  const [liveLocation, setLiveLocation] = useState(() => {
    const loc = user?.last_known_location;
    if (loc?.latitude && loc?.longitude) {
      return {
        latitude: Number(loc.latitude),
        longitude: Number(loc.longitude),
        accuracy: loc.accuracy || null,
        timestamp: Date.now(),
      };
    }
    return null;
  });

  const isUpdatingLocationRef = useRef(false);

  // Bug found: useLocationTracker's onError callback already carries a
  // real, user-facing message per GeolocationPositionError code (see
  // handleLocationError below and useGPSPosition.js's handleError), but
  // nothing kept it -- it was only console.warn'd, so a technician whose
  // browser denied location permission just saw the cockpit silently sit
  // in ONLINE_LOCATION_PENDING forever with no indication why. Surfaced
  // via context so PortalCockpitLayout can render it.
  const [locationError, setLocationError] = useState(null);

  const handlePositionChange = useCallback(async (payload) => {
    const newLoc = {
      latitude: payload.latitude,
      longitude: payload.longitude,
      accuracy: payload.accuracy,
      timestamp: Date.now(),
    };
    setLiveLocation(newLoc);
    setPresenceState('ONLINE_GPS_LIVE');
    setLocationError(null);

    // Transmit authoritative telemetry to backend (with in-flight deduplication)
    if (isUpdatingLocationRef.current) return;
    isUpdatingLocationRef.current = true;
    try {
      await apiUpdateLocationFull(
        payload.latitude,
        payload.longitude,
        payload.accuracy,
        payload.speed,
        payload.heading,
        payload.captured_at
      );
      // Notify map views
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('workforce:location-updated', {
            detail: { ...payload, source: 'session_watcher' },
          })
        );
      }
    } catch (_) {
    } finally {
      isUpdatingLocationRef.current = false;
    }
  }, []);

  const handleLocationError = useCallback((err) => {
    console.warn('[EmployeeRuntime] Location tracker warning:', err);
    // If location fails, we remain online but location is pending
    setPresenceState((prev) => (prev === 'OFFLINE' ? 'OFFLINE' : 'ONLINE_LOCATION_PENDING'));
    // If transient timeout and cached location already exists, do not clear or set error
    if (err?.code === 'TIMEOUT') {
      return;
    }
    setLocationError(err?.message || 'Unable to access your location. Please check your device location settings.');
  }, []);

  // Mount single continuous GPS watcher for online authenticated technician
  useLocationTracker(
    Boolean(isAuthenticated && isApprovedEmployee && isOnline),
    handlePositionChange,
    handleLocationError
  );

  const scanCurrentLocation = useCallback(async () => {
    try {
      const pos = await getGPSPosition(true);
      const { latitude, longitude, accuracy, speed, heading } = pos.coords;
      const captured_at = new Date(pos.timestamp || Date.now()).toISOString();
      await apiUpdateLocationFull(latitude, longitude, accuracy, speed, heading, captured_at);
      const newLoc = {
        latitude,
        longitude,
        accuracy,
        timestamp: pos.timestamp || Date.now(),
      };
      setLiveLocation(newLoc);
      setPresenceState('ONLINE_GPS_LIVE');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('workforce:location-updated', {
            detail: { ...newLoc, speed, heading, captured_at, source: 'manual_scan' },
          })
        );
      }
      return newLoc;
    } catch (err) {
      throw err;
    }
  }, []);

  // ── 8. Single Realtime Event Stream Connection (SSE) ───────────────────────
  const handleRealtimeEvent = useCallback(
    (eventData) => {
      const type = eventData.event_type;
      console.info(`[EmployeeRuntime SSE Event] ${type}`, eventData);

      if (
        type === 'OFFER_CREATED' ||
        type === 'JOB_OFFER' ||
        type === 'JOB_OFFER_CREATED'
      ) {
        const payload = eventData.payload || {};
        if (payload.offer_id || payload.id) {
          triggerOfferBrowserNotification(payload);
        }
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('workforce:offer-received', { detail: eventData }));
        }
        scheduleCoalescedRefresh(50);
      } else if (
        [
          'JOB_ASSIGNED',
          'JOB_ACCEPTED',
          'ARRIVAL_DETECTED',
          'JOB_ARRIVED',
          'INSPECTION_UPDATED',
          'QUOTATION_CREATED',
          'QUOTATION_SENT',
          'QUOTATION_APPROVED',
          'QUOTATION_DECLINED',
          'EXECUTION_JOB_CREATED',
          'PAYMENT_UPDATED',
          'PAYMENT_COLLECTED',
          'INVOICE_CREATED',
          'JOB_COMPLETED',
          'JOB_LOCATION_UPDATE',
          'STATUS_CHANGE',
          'EXTENSION_DECIDED',
        ].includes(type)
      ) {
        scheduleCoalescedRefresh(300);
      } else if (type === 'NOTIFICATION_CREATED') {
        syncNotifications();
      }
    },
    [triggerOfferBrowserNotification, scheduleCoalescedRefresh, syncNotifications]
  );

  const handleRealtimeReconcile = useCallback(() => {
    scheduleCoalescedRefresh(100);
    syncNotifications();
  }, [scheduleCoalescedRefresh, syncNotifications]);

  const handleRealtimeAuthFailure = useCallback(() => {
    console.warn('[Realtime] Auth failure encountered on SSE channel. Realtime disconnected.');
  }, []);

  const { connectionState: realtimeConnectionState } = useRealtimeStream({
    enabled: Boolean(isAuthenticated && isApprovedEmployee && isOnline),
    onEvent: handleRealtimeEvent,
    onReconcile: handleRealtimeReconcile,
    onAuthFailure: handleRealtimeAuthFailure,
  });

  // ── 9. Fast Presence Toggle Controller (Correction 2) ──────────────────────
  const togglePresenceFast = useCallback(
    async (desiredState = null) => {
      try {
        setPresenceState('CONNECTING');
        const res = await authTogglePresence(desiredState);
        if (res?.is_online) {
          setPresenceState('ONLINE_LOCATION_PENDING');
          // Start background GPS resolution without blocking presence completion
          getGPSPosition(false)
            .then((pos) => {
              handlePositionChange({
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
                accuracy: pos.coords.accuracy,
                speed: pos.coords.speed,
                heading: pos.coords.heading,
                captured_at: new Date(pos.timestamp || Date.now()).toISOString(),
              });
            })
            .catch(() => {});
          refreshActiveJobs({ silent: true });
        } else {
          setPresenceState('OFFLINE');
        }
        return res;
      } catch (err) {
        setPresenceState(isOnlineAuth ? 'ONLINE_LOCATION_PENDING' : 'OFFLINE');
        throw err;
      }
    },
    [authTogglePresence, isOnlineAuth, handlePositionChange, refreshActiveJobs]
  );

  const activeAssignedJob = useMemo(() => {
    return (
      activeJobs.find((j) => {
        const st = (j.status || j.job_status || '').toLowerCase();
        const isAssigned = Boolean(j.is_assigned_to_current_employee || j.assigned_employee_id === user?.id);
        return isAssigned && ACTIVE_QUEUE_STATUSES.includes(st);
      }) || null
    );
  }, [activeJobs, user?.id]);

  const reconcileJobAccepted = useCallback((jobId) => {
    refreshActiveJobs({ silent: true });
  }, [refreshActiveJobs]);

  const reconcileJobCompleted = useCallback((jobId) => {
    refreshActiveJobs({ silent: true });
    refreshCompletedJobs({ silent: true });
  }, [refreshActiveJobs, refreshCompletedJobs]);

  const reconcileOfferRemoved = useCallback((offerId) => {
    refreshActiveJobs({ silent: true });
  }, [refreshActiveJobs]);

  // ── 10. Context Value Assembly ─────────────────────────────────────────────
  const value = useMemo(
    () => ({
      // Jobs State
      activeJobs,
      completedJobs,
      selectedJob,
      setSelectedJob,
      incomingOffer,
      incomingOffers,
      hasActiveJob,
      activeAssignedJob,
      isJobsLoading,
      isCompletedLoading,
      jobsError,
      refreshActiveJobs,
      refreshCompletedJobs,
      reconcileJobAccepted,
      reconcileJobCompleted,
      reconcileOfferRemoved,

      // Location & Presence State Machine
      presenceState,
      isOnline,
      isGpsLive,
      isLocationPending,
      liveLocation,
      gpsState: isGpsLive ? 'live' : isLocationPending ? 'locating' : 'idle',
      locationState: isGpsLive ? 'live' : isLocationPending ? 'locating' : 'idle',
      locationError,
      scanCurrentLocation,
      togglePresence: togglePresenceFast,

      // Notifications
      notifications,
      unreadCount,
      syncNotifications,
      markNotificationAsRead,
      clearAllNotifications,

      // Realtime State
      realtimeConnectionState,
    }),
    [
      activeJobs,
      completedJobs,
      selectedJob,
      incomingOffer,
      incomingOffers,
      hasActiveJob,
      activeAssignedJob,
      isJobsLoading,
      isCompletedLoading,
      jobsError,
      refreshActiveJobs,
      refreshCompletedJobs,
      reconcileJobAccepted,
      reconcileJobCompleted,
      reconcileOfferRemoved,
      presenceState,
      isOnline,
      isGpsLive,
      isLocationPending,
      liveLocation,
      locationError,
      scanCurrentLocation,
      togglePresenceFast,
      notifications,
      unreadCount,
      syncNotifications,
      markNotificationAsRead,
      clearAllNotifications,
      realtimeConnectionState,
    ]
  );

  return <EmployeeRuntimeContext.Provider value={value}>{children}</EmployeeRuntimeContext.Provider>;
}

export { useEmployeeRuntime } from './EmployeeRuntimeContext.jsx';
