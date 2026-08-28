/**
 * EmployeeRuntimeProvider.jsx
 *
 * Single persistent session runtime for the CalTrack Workforce employee application.
 * Incorporates Phase 2 Architecture Standards:
 * 1. ONE Authoritative GPS Implementation (session-level useLocationTracker)
 * 2. Explicit GPS State Machine (GPS_IDLE, GPS_REQUESTING, GPS_ACQUIRING, GPS_LIVE, GPS_GEOFENCE_READY, GPS_STALE, GPS_UNAVAILABLE, GPS_PERMISSION_DENIED, GPS_ERROR)
 * 3. Fast presence toggle decoupled from GPS acquisition
 * 4. Centralized background auto-arrival detection (<= 250m) with in-flight coalescing
 * 5. Single controlled autoClockIn runtime action with idempotency protection
 * 6. Explicit Clock-In readiness state engine
 * 7. Zero Customer Impact & Preserved API Contracts
 * 8. Stale-While-Revalidate Active Job Cache + Out-of-Order Generation Protection
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
  apiVerifyArrival,
} from '../api/workforceService.js';
import { apiClockIn } from '../api/clockInApi.js';
import {
  useLocationTracker,
  getGPSPosition,
  GPS_STATE,
  computeGpsState,
  haversineMetres,
  MAX_GEOFENCE_ACCURACY_METERS,
  classifyAccuracy,
} from '../hooks/useGPSPosition.js';
import { useRealtimeStream } from '../hooks/useRealtimeStream.js';

export function EmployeeRuntimeProvider({ children }) {
  const { user, isEmployee, registrationStatus, togglePresence: authTogglePresence, logout, isAuthenticated } = useAuth();

  const isApprovedEmployee = Boolean(user && isEmployee && registrationStatus === 'approved');
  const isOnlineAuth = Boolean(user?.isOnline);

  // ── 1. Presence & GPS State Machine ─────────────────────────────────────────
  const [presenceState, setPresenceState] = useState(() => {
    if (!isOnlineAuth) return 'OFFLINE';
    const loc = user?.last_known_location;
    if (loc?.latitude && loc?.longitude) return 'ONLINE_GPS_LIVE';
    return 'ONLINE_LOCATION_PENDING';
  });

  const [gpsState, setGpsState] = useState(() => {
    if (!isOnlineAuth) return GPS_STATE.IDLE;
    const loc = user?.last_known_location;
    if (loc?.latitude && loc?.longitude) return computeGpsState(loc);
    return GPS_STATE.ACQUIRING;
  });

  const isOnline = presenceState !== 'OFFLINE' && presenceState !== 'CONNECTING';
  const isGpsLive = gpsState === GPS_STATE.LIVE || gpsState === GPS_STATE.GEOFENCE_READY;
  const isGpsGeofenceReady = gpsState === GPS_STATE.GEOFENCE_READY;
  const isLocationPending = gpsState === GPS_STATE.ACQUIRING || gpsState === GPS_STATE.REQUESTING;

  useEffect(() => {
    if (!isOnlineAuth) {
      setPresenceState('OFFLINE');
      setGpsState(GPS_STATE.IDLE);
    } else {
      setPresenceState((prev) => (prev === 'OFFLINE' ? 'ONLINE_LOCATION_PENDING' : prev));
      setGpsState((prev) => (prev === GPS_STATE.IDLE ? GPS_STATE.ACQUIRING : prev));
    }
  }, [isOnlineAuth]);

  // ── 2. Jobs State & Cache (Stale-While-Revalidate) ───────────────────────────
  const [activeJobs, setActiveJobs] = useState([]);
  const [completedJobs, setCompletedJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [isJobsLoading, setIsJobsLoading] = useState(false);
  const [isCompletedLoading, setIsCompletedLoading] = useState(false);
  const [jobsError, setJobsError] = useState(null);
  const [serverTimeOffset, setServerTimeOffset] = useState(0);

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

  const activeAssignedJob = useMemo(() => {
    const empId = user?.employee_id || user?.employeeId || user?.id;
    return activeJobs.find((j) => {
      const st = (j.status || j.job_status || '').toLowerCase();
      if (!ACTIVE_QUEUE_STATUSES.includes(st)) return false;
      const isAssigned = Boolean(
        j.is_assigned_to_current_employee === true ||
        (empId && (j.assigned_employee_id === empId || j.assigned_employee === empId || j.assigned_employee?.id === empId)) ||
        (user?.id && (j.technician_id === user.id || j.assigned_employee_id === user.id))
      );
      return isAssigned;
    }) || null;
  }, [activeJobs, user?.id, user?.employee_id, user?.employeeId]);

  const hasActiveJob = Boolean(activeAssignedJob);


  const incomingOffers = useMemo(() => {
    const currentNow = Date.now() + (serverTimeOffset || 0);
    return activeJobs.filter((j) => {
      const isOffer = j.is_offer === true || j.active_offer?.status === 'OFFERED';
      if (!isOffer) return false;
      if (j.is_assigned_to_current_employee) return false;
      const st = (j.status || j.job_status || '').toLowerCase();
      if (['accepted', 'on_the_way', 'en_route', 'arrived', 'in_progress', 'proof_submitted', 'completed', 'cancelled'].includes(st)) {
        return false;
      }
      if (j.assigned_employee_id || j.assigned_employee) return false;
      if (j.active_offer?.status && j.active_offer.status !== 'OFFERED') return false;

      const expStr = j.offer_expires_at || j.active_offer?.expires_at;
      if (expStr) {
        const expMs = Date.parse(expStr);
        if (!isNaN(expMs) && expMs <= currentNow) {
          return false;
        }
      }
      return !j.active_offer?.is_expired;
    });
  }, [activeJobs, serverTimeOffset]);

  const incomingOffer = useMemo(() => {
    return incomingOffers[0] || null;
  }, [incomingOffers]);

  // ── 3. Notification Deduplication ──────────────────────────────────────────
  const knownOfferIdsRef = useRef(new Set());
  const isInitialOffersLoadedRef = useRef(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (isOnline && typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {});
    }
  }, [isOnline]);

  const triggerOfferBrowserNotification = useCallback((offeredJob) => {
    if (!offeredJob) return;
    const offerId = offeredJob.active_offer?.id || offeredJob.offer_id || `job_${offeredJob.id}`;

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
          tag: `offer_${offerId}`,
        });
      } catch (_) {}
    }
  }, []);

  // ── Scheduled Local Expiry Timer for Active Offers ─────────────────────────
  const expiryTimerRef = useRef(null);

  const refreshActiveJobs = useCallback(
    async (options = {}) => {
      const isSilent = options?.silent === true;
      const force = options?.force === true;

      if (inFlightActiveJobsPromiseRef.current && !force) {
        return inFlightActiveJobsPromiseRef.current;
      }

      if (!isSilent && activeJobsRef.current.length === 0) {
        setIsJobsLoading(true);
      }
      setJobsError(null);

      const currentGen = ++fetchGenerationRef.current;

      const fetchPromise = (async () => {
        try {
          const jobsData = await apiGetWorkforceJobs('active');

          if (currentGen < fetchGenerationRef.current) {
            console.info(`[EmployeeRuntime] Discarding stale active jobs response (gen #${currentGen} < #${fetchGenerationRef.current})`);
            return activeJobsRef.current;
          }

          if (Array.isArray(jobsData)) {
            setActiveJobs(jobsData);

            const jobWithServerTime = jobsData.find((j) => j.server_time || j.active_offer?.server_time);
            const serverTimeStr = jobWithServerTime?.server_time || jobWithServerTime?.active_offer?.server_time;
            if (serverTimeStr) {
              const sTime = Date.parse(serverTimeStr);
              if (!isNaN(sTime)) {
                setServerTimeOffset(sTime - Date.now());
              }
            }

            // Filter all currently valid incoming offers
            const validOffers = jobsData.filter(
              (j) =>
                (j.is_offer === true || j.active_offer?.status === 'OFFERED') &&
                !j.active_offer?.is_expired &&
                !j.is_assigned_to_current_employee
            );

            if (!isInitialOffersLoadedRef.current) {
              // Seed ALL initial offers to prevent duplicate notification triggers on initial mount
              validOffers.forEach((offer) => {
                const offerId = offer.active_offer?.id || offer.offer_id || `job_${offer.id}`;
                knownOfferIdsRef.current.add(offerId);
              });
              isInitialOffersLoadedRef.current = true;
            } else {
              // Trigger notification ONLY for genuinely new offer IDs
              validOffers.forEach((offer) => {
                const offerId = offer.active_offer?.id || offer.offer_id || `job_${offer.id}`;
                if (!knownOfferIdsRef.current.has(offerId)) {
                  knownOfferIdsRef.current.add(offerId);
                  triggerOfferBrowserNotification(offer);
                }
              });
            }

            const currentOffer = validOffers[0] || null;

            setSelectedJob((prev) => {
              const empId = user?.employee_id || user?.employeeId || user?.id;
              const findActiveJob = () =>
                jobsData.find((j) => {
                  const st = (j.status || j.job_status || '').toLowerCase();
                  if (!ACTIVE_QUEUE_STATUSES.includes(st)) return false;
                  const isAssigned = Boolean(
                    j.is_assigned_to_current_employee === true ||
                    (empId && (j.assigned_employee_id === empId || j.assigned_employee === empId || j.assigned_employee?.id === empId)) ||
                    (user?.id && (j.technician_id === user.id || j.assigned_employee_id === user.id))
                  );
                  return isAssigned;
                });

              if (!prev) {
                if (currentOffer) return currentOffer;
                return findActiveJob() || null;
              }
              const updated = jobsData.find((j) => j.id === prev.id);
              if (updated) {
                const isOffer = (updated.is_offer === true || updated.active_offer?.status === 'OFFERED') &&
                  !updated.active_offer?.is_expired &&
                  !updated.is_assigned_to_current_employee;
                if (isOffer) {
                  return updated;
                }
                const st = (updated.status || updated.job_status || '').toLowerCase();
                const isAssigned = Boolean(
                  updated.is_assigned_to_current_employee === true ||
                  (empId && (updated.assigned_employee_id === empId || updated.assigned_employee === empId || updated.assigned_employee?.id === empId)) ||
                  (user?.id && (updated.technician_id === user.id || updated.assigned_employee_id === user.id))
                );
                if (isAssigned && ACTIVE_QUEUE_STATUSES.includes(st)) {
                  return updated;
                }
              }
              // If prev was completed, cancelled, expired or removed from active queue, pick next authoritative offer or active job, or null
              if (currentOffer) return currentOffer;
              return findActiveJob() || null;
            });
            return jobsData;
          }
          return activeJobsRef.current;
        } catch (err) {
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

  useEffect(() => {
    if (expiryTimerRef.current) {
      clearTimeout(expiryTimerRef.current);
      expiryTimerRef.current = null;
    }

    const offers = activeJobs.filter(
      (j) =>
        (j.is_offer === true || j.active_offer?.status === 'OFFERED') &&
        !j.is_assigned_to_current_employee
    );

    if (offers.length === 0) return;

    let earliestExpiryMs = Infinity;
    for (const job of offers) {
      const expStr = job.offer_expires_at || job.active_offer?.expires_at;
      if (expStr) {
        const expMs = Date.parse(expStr);
        if (!isNaN(expMs) && expMs < earliestExpiryMs) {
          earliestExpiryMs = expMs;
        }
      }
    }

    if (earliestExpiryMs === Infinity) return;

    const nowWithOffset = Date.now() + (serverTimeOffset || 0);
    const delayMs = Math.max(0, earliestExpiryMs - nowWithOffset);

    expiryTimerRef.current = setTimeout(() => {
      console.info('[EmployeeRuntime] Scheduled offer expiry reached. Reconciling UI.');
      setActiveJobs((prev) =>
        prev.filter((j) => {
          const expStr = j.offer_expires_at || j.active_offer?.expires_at;
          if (expStr) {
            const expMs = Date.parse(expStr);
            const currentNow = Date.now() + (serverTimeOffset || 0);
            if (!isNaN(expMs) && expMs <= currentNow && !j.is_assigned_to_current_employee) {
              return false;
            }
          }
          return true;
        })
      );

      setSelectedJob((prev) => {
        if (!prev) return null;
        const expStr = prev.offer_expires_at || prev.active_offer?.expires_at;
        if (expStr) {
          const expMs = Date.parse(expStr);
          const currentNow = Date.now() + (serverTimeOffset || 0);
          if (!isNaN(expMs) && expMs <= currentNow && !prev.is_assigned_to_current_employee) {
            return null;
          }
        }
        return prev;
      });

      refreshActiveJobs({ silent: true });
    }, delayMs);

    return () => {
      if (expiryTimerRef.current) {
        clearTimeout(expiryTimerRef.current);
        expiryTimerRef.current = null;
      }
    };
  }, [activeJobs, serverTimeOffset, refreshActiveJobs]);

  // ── 5. Completed Jobs Fetch ────────────────────────────────────────────────
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

  // ── 6. Notification Sync ───────────────────────────────────────────────────
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

  useEffect(() => {
    if (isAuthenticated && isApprovedEmployee) {
      refreshActiveJobs();
      syncNotifications();
    }
  }, [isAuthenticated, isApprovedEmployee, refreshActiveJobs, syncNotifications]);

  // ── 7. Single Authoritative Live GPS Watcher ───────────────────────────────
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

  const handlePositionChange = useCallback(async (localPayload, backendPayload) => {
    if (!localPayload) return;

    // ── PIPELINE A: Immediate Local Navigation & UI (Zero Delay, No Network) ──
    const newLoc = {
      latitude: localPayload.latitude,
      longitude: localPayload.longitude,
      accuracy: localPayload.accuracy,
      speed: localPayload.speed,
      heading: localPayload.heading,
      timestamp: localPayload.timestamp || Date.now(),
      captured_at: localPayload.captured_at || new Date().toISOString(),
    };
    setLiveLocation(newLoc);
    setPresenceState('ONLINE_GPS_LIVE');
    setGpsState(localPayload.is_geofence_ready ? GPS_STATE.GEOFENCE_READY : GPS_STATE.LIVE);

    // Dispatch local UI event immediately so navigation map responds with zero latency
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('workforce:location-updated', {
          detail: { ...newLoc, source: 'session_watcher' },
        })
      );
    }

    // ── PIPELINE B: Backend Telemetry Persistence (Throttled, Asynchronous, Non-Blocking) ──
    if (!backendPayload) return;
    if (isUpdatingLocationRef.current) return;
    isUpdatingLocationRef.current = true;
    try {
      await apiUpdateLocationFull(
        backendPayload.latitude,
        backendPayload.longitude,
        backendPayload.accuracy,
        backendPayload.speed,
        backendPayload.heading,
        backendPayload.captured_at
      );
    } catch (_) {
    } finally {
      isUpdatingLocationRef.current = false;
    }
  }, []);

  const handleLocationError = useCallback((err) => {
    if (err?.code === 1) {
      setGpsState(GPS_STATE.DENIED);
      setPresenceState('ONLINE_GPS_ERROR');
    } else {
      setGpsState(GPS_STATE.TIMEOUT);
      setPresenceState('ONLINE_GPS_ERROR');
    }
  }, []);

  const isNavigating = useMemo(() => {
    if (!selectedJob) return false;
    const st = (selectedJob.status || selectedJob.job_status || '').toLowerCase();
    return ['accepted', 'on_the_way', 'en_route'].includes(st);
  }, [selectedJob]);

  // Dynamic movement status
  const movementStatus = useMemo(() => {
    if (!liveLocation) return 'UNKNOWN';
    if (liveLocation.speed != null && liveLocation.speed >= 1.2) return 'MOVING';
    if (liveLocation.speed != null && liveLocation.speed < 0.4) return 'STATIONARY';
    return 'UNKNOWN';
  }, [liveLocation]);

  // Dynamic freshness state
  const freshnessState = useMemo(() => {
    if (!liveLocation?.captured_at) return 'LOCATION_LOST';
    const ageSeconds = (Date.now() - new Date(liveLocation.captured_at).getTime()) / 1000;
    if (ageSeconds <= 5) return 'LIVE';
    if (ageSeconds <= 15) return 'UPDATING';
    if (ageSeconds <= 30) return 'DELAYED';
    if (ageSeconds <= 60) return 'STALE';
    return 'LOCATION_LOST';
  }, [liveLocation]);

  // Dynamic geofence status relative to selected job
  const geofenceStatus = useMemo(() => {
    if (!selectedJob || !liveLocation?.latitude || !liveLocation?.longitude) return 'OUTSIDE';
    const custLat = Number(selectedJob.latitude);
    const custLng = Number(selectedJob.longitude);
    if (isNaN(custLat) || isNaN(custLng)) return 'OUTSIDE';
    const distM = haversineMetres(liveLocation.latitude, liveLocation.longitude, custLat, custLng);
    const st = (selectedJob.status || selectedJob.job_status || '').toLowerCase();
    if (st === 'arrived' || distM <= 250) return 'ARRIVED';
    if (distM <= 500) return 'ARRIVING';
    if (distM <= 1000) return 'APPROACHING';
    return 'OUTSIDE';
  }, [selectedJob, liveLocation]);

  // Mount single continuous GPS watcher for online authenticated employee (with adaptive transmission mode)
  useLocationTracker(
    Boolean(isAuthenticated && isApprovedEmployee && isOnline),
    handlePositionChange,
    handleLocationError,
    { isNavigating }
  );

  const scanCurrentLocation = useCallback(async () => {
    try {
      setGpsState(GPS_STATE.REQUESTING);
      const pos = await getGPSPosition(true);
      const { latitude, longitude, accuracy, speed, heading } = pos.coords;
      const captured_at = new Date(pos.timestamp || Date.now()).toISOString();
      await apiUpdateLocationFull(latitude, longitude, accuracy, speed, heading, captured_at);
      const newLoc = {
        latitude,
        longitude,
        accuracy,
        speed,
        heading,
        timestamp: pos.timestamp || Date.now(),
        captured_at,
      };
      setLiveLocation(newLoc);
      setPresenceState('ONLINE_GPS_LIVE');
      setGpsState(accuracy <= MAX_GEOFENCE_ACCURACY_METERS ? GPS_STATE.GEOFENCE_READY : GPS_STATE.LIVE);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('workforce:location-updated', {
            detail: { ...newLoc, source: 'manual_scan' },
          })
        );
      }
      return newLoc;
    } catch (err) {
      const state = computeGpsState(null, 0, true, err);
      setGpsState(state);
      throw err;
    }
  }, []);

  // ── 8. Centralized Automatic Geofence Arrival Monitor (<= 250m) ─────────────
  const inFlightArrivalJobIdsRef = useRef(new Set());

  useEffect(() => {
    if (!isOnline || !liveLocation || !selectedJob) return;
    const st = (selectedJob.status || selectedJob.job_status || '').toLowerCase();
    if (!['accepted', 'on_the_way', 'en_route'].includes(st)) return;

    const custLat = Number(selectedJob.latitude);
    const custLon = Number(selectedJob.longitude);
    if (isNaN(custLat) || isNaN(custLon) || (custLat === 0 && custLon === 0)) return;

    const dist = haversineMetres(liveLocation.latitude, liveLocation.longitude, custLat, custLon);
    const isAccurate = liveLocation.accuracy != null && liveLocation.accuracy <= MAX_GEOFENCE_ACCURACY_METERS;

    if (dist <= 250 && isAccurate && !inFlightArrivalJobIdsRef.current.has(selectedJob.id)) {
      inFlightArrivalJobIdsRef.current.add(selectedJob.id);
      console.info(`[EmployeeRuntime] Auto-Arrival triggered at ${Math.round(dist)}m for Job #${selectedJob.id}.`);
      apiVerifyArrival(
        selectedJob.id,
        liveLocation.latitude,
        liveLocation.longitude,
        liveLocation.accuracy,
        liveLocation.timestamp || Date.now()
      )
        .then(() => {
          scheduleCoalescedRefresh(100);
        })
        .catch((err) => {
          console.warn('[EmployeeRuntime] Auto-arrival API error:', err);
          inFlightArrivalJobIdsRef.current.delete(selectedJob.id);
        });
    }
  }, [isOnline, liveLocation, selectedJob, scheduleCoalescedRefresh]);

  // ── 9. Single Controlled Auto Clock-In Runtime Action ──────────────────────
  const inFlightClockInRef = useRef(null);

  const autoClockIn = useCallback(
    async (jobId, options = {}) => {
      if (inFlightClockInRef.current) {
        return inFlightClockInRef.current;
      }

      const promise = (async () => {
        try {
          let loc = liveLocation;
          if (!loc?.latitude || !loc?.longitude) {
            try {
              loc = await scanCurrentLocation();
            } catch (_e) {
              console.warn('[EmployeeRuntime] scanCurrentLocation error during autoClockIn:', _e);
            }
          }
          if (!loc?.latitude || !loc?.longitude) {
            if (user?.last_known_location?.latitude && user?.last_known_location?.longitude) {
              loc = {
                latitude: Number(user.last_known_location.latitude),
                longitude: Number(user.last_known_location.longitude),
                accuracy: user.last_known_location.accuracy || 10,
              };
            }
          }

          const payload = {
            address: options.address || 'GPS Verified Site Arrival',
            job_id: jobId,
          };
          if (loc?.latitude && loc?.longitude) {
            payload.lat = loc.latitude;
            payload.lon = loc.longitude;
            payload.accuracy = loc.accuracy || 10;
            payload.timestamp = loc.timestamp || Date.now();
          }

          const res = await apiClockIn(payload);
          await refreshActiveJobs({ force: true });
          return res;
        } finally {
          inFlightClockInRef.current = null;
        }
      })();

      inFlightClockInRef.current = promise;
      return promise;
    },
    [liveLocation, user?.last_known_location, scanCurrentLocation, refreshActiveJobs]
  );

  // ── 10. Explicit Clock-In Readiness State Engine ───────────────────────────
  const getClockInReadiness = useCallback(
    (job, preServiceStatus = null, isShiftClockedIn = false) => {
      if (isShiftClockedIn) return { state: 'CLOCKED_IN', label: 'Clocked In', canClockIn: false };
      if (!job) return { state: 'NOT_READY', label: 'No Active Job', canClockIn: false };
      if (!isOnline) return { state: 'OFFLINE', label: 'Technician Offline', canClockIn: false };

      if (gpsState === GPS_STATE.PERMISSION_DENIED) {
        return { state: 'GPS_UNAVAILABLE', label: 'Location Permission Denied', canClockIn: false, reason: 'Please allow location access in browser settings.' };
      }
      if (gpsState === GPS_STATE.UNAVAILABLE || gpsState === GPS_STATE.ERROR) {
        return { state: 'GPS_UNAVAILABLE', label: 'GPS Signal Unavailable', canClockIn: false, reason: 'Device GPS unavailable. Please enable location.' };
      }
      if (gpsState === GPS_STATE.ACQUIRING || gpsState === GPS_STATE.REQUESTING) {
        return { state: 'GPS_PENDING', label: 'Acquiring GPS Signal...', canClockIn: false, reason: 'Waiting for high-accuracy GPS fix...' };
      }
      if (gpsState === GPS_STATE.STALE) {
        return { state: 'GPS_STALE', label: 'GPS Signal Stale', canClockIn: false, reason: 'GPS fix is outdated. Waiting for fresh fix...' };
      }

      const custLat = Number(job.latitude);
      const custLon = Number(job.longitude);
      let distanceM = null;
      if (!isNaN(custLat) && !isNaN(custLon) && liveLocation) {
        distanceM = Math.round(haversineMetres(liveLocation.latitude, liveLocation.longitude, custLat, custLon));
      }

      const isGeofencePassed = preServiceStatus?.geofence_passed || (distanceM != null && distanceM <= 250);
      if (!isGeofencePassed) {
        return {
          state: 'OUTSIDE_GEOFENCE',
          label: `Outside Geofence (${distanceM != null ? `${distanceM}m` : 'Unknown'} away)`,
          canClockIn: false,
          distanceM,
          reason: `You are ${distanceM != null ? `${distanceM}m` : 'away'} from customer. Move within 250m.`,
        };
      }

      if (!preServiceStatus?.otp_verified) {
        return { state: 'OTP_PENDING', label: 'Customer OTP Required', canClockIn: false, reason: 'Ask customer for the 6-digit Work Start OTP code.' };
      }

      if (!preServiceStatus?.presence_photo) {
        return { state: 'PRESENCE_PENDING', label: 'Technician Presence Selfie Required', canClockIn: false, reason: 'Take live presence selfie to confirm on-site identity.' };
      }

      return { state: 'READY', label: 'Pre-Verification Complete — Ready', canClockIn: true, distanceM };
    },
    [isOnline, gpsState, liveLocation]
  );

  // ── Synchronous Authoritative State Reconciliation Handlers ───────────────
  const reconcileJobAccepted = useCallback((jobId, responseData = {}) => {
    setActiveJobs((prev) =>
      prev.map((j) => {
        if (j.id === jobId) {
          return {
            ...j,
            status: responseData.status || 'accepted',
            job_status: responseData.status || 'accepted',
            is_offer: false,
            is_accepted_by_current_employee: true,
            is_assigned_to_current_employee: true,
            accepted_at: responseData.accepted_at || new Date().toISOString(),
            active_offer: null,
          };
        }
        return j;
      })
    );

    setSelectedJob((prev) => {
      const base = prev?.id === jobId ? prev : activeJobsRef.current.find((j) => j.id === jobId) || { id: jobId };
      return {
        ...base,
        status: responseData.status || 'accepted',
        job_status: responseData.status || 'accepted',
        is_offer: false,
        is_accepted_by_current_employee: true,
        is_assigned_to_current_employee: true,
        accepted_at: responseData.accepted_at || new Date().toISOString(),
        active_offer: null,
      };
    });

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('workforce:job-accepted', { detail: { jobId, ...responseData } }));
    }

    refreshActiveJobs({ force: true }).catch(() => {});
  }, [refreshActiveJobs]);

  const reconcileJobCompleted = useCallback((jobId, completedJobData = {}) => {
    // 1. Immediately purge from activeJobs
    setActiveJobs((prev) => prev.filter((j) => j.id !== jobId));

    // 2. Clear selectedJob if it was the completed job
    setSelectedJob((prev) => (prev?.id === jobId ? null : prev));

    // 3. Immediately prepend to completedJobs for live dashboard metrics
    setCompletedJobs((prev) => {
      const existing = prev.find((j) => j.id === jobId);
      if (existing) {
        return prev.map((j) => (j.id === jobId ? { ...j, ...completedJobData, status: 'completed' } : j));
      }
      const jobFromActive = activeJobsRef.current.find((j) => j.id === jobId);
      const newCompleted = {
        ...(jobFromActive || {}),
        ...completedJobData,
        id: jobId,
        status: 'completed',
        completed_at: completedJobData?.completed_at || new Date().toISOString(),
      };
      return [newCompleted, ...prev];
    });

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('workforce:job-completed', { detail: { jobId, ...completedJobData } }));
    }

    refreshActiveJobs({ force: true }).catch(() => {});
    refreshCompletedJobs({ force: true }).catch(() => {});
  }, [refreshActiveJobs, refreshCompletedJobs]);

  const reconcileOfferRemoved = useCallback((jobId) => {
    setActiveJobs((prev) => prev.filter((j) => j.id !== jobId));
    setSelectedJob((prev) => (prev?.id === jobId ? null : prev));
    refreshActiveJobs({ force: true }).catch(() => {});
  }, [refreshActiveJobs]);

  // Gentle 15-second background synchronization to ensure UI matches DB state
  useEffect(() => {
    if (!isAuthenticated || !isApprovedEmployee || !isOnline) return;
    const interval = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      refreshActiveJobs({ silent: true }).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, [isAuthenticated, isApprovedEmployee, isOnline, refreshActiveJobs]);

  // ── 11. Realtime Stream (SSE) ──────────────────────────────────────────────
  const handleRealtimeEvent = useCallback(
    (eventData) => {
      const type = eventData.event_type;
      console.info(`[EmployeeRuntime SSE Event] ${type}`, eventData);

      if (type === 'OFFER_CREATED' || type === 'JOB_OFFER' || type === 'EMPLOYEE_JOB_OFFERED') {
        const payload = eventData.payload || {};
        if (payload.offer_id || payload.id) {
          triggerOfferBrowserNotification(payload);
        }
        scheduleCoalescedRefresh(150);
      } else if (type === 'JOB_OFFER_SUPERSEDED' || type === 'OFFER_SUPERSEDED' || type === 'OFFER_EXPIRED') {
        const payload = eventData.payload || {};
        const jobTargetId = payload.job_id || payload.id;
        if (jobTargetId) {
          reconcileOfferRemoved(jobTargetId);
        }
        scheduleCoalescedRefresh(100);
      } else if (type === 'JOB_ACCEPTED' || type === 'EMPLOYEE_JOB_ACCEPTED') {
        const payload = eventData.payload || {};
        const empId = user?.employee_id || user?.employeeId || user?.id;
        const acceptedByAnother = payload.employee_id && empId && String(payload.employee_id) !== String(empId);
        if (acceptedByAnother) {
          // Another technician won the job: immediately purge offer from this technician's view
          const jobTargetId = payload.job_id || payload.id;
          if (jobTargetId) {
            reconcileOfferRemoved(jobTargetId);
          }
        }
        scheduleCoalescedRefresh(150);
      } else if (type === 'JOB_COMPLETED' || type === 'EMPLOYEE_JOB_COMPLETED') {
        const payload = eventData.payload || {};
        const jobTargetId = payload.job_id || payload.id;
        if (jobTargetId) {
          reconcileJobCompleted(jobTargetId, payload);
        }
        scheduleCoalescedRefresh(150);
      } else if (
        [
          'JOB_ASSIGNED',
          'ARRIVAL_DETECTED',
          'EMPLOYEE_JOB_CANCELLED',
          'EMPLOYEE_CANCELLED',
          'EMPLOYEE_AVAILABILITY_CHANGED',
          'PRE_SERVICE_COMPLETED',
          'JOB_LOCATION_UPDATE',
          'STATUS_CHANGE',
          'EXTENSION_DECIDED',
          'PAYMENT_COLLECTED',
          'PAYMENT_OTP_VERIFIED',
        ].includes(type)
      ) {
        scheduleCoalescedRefresh(200);
      } else if (type === 'NOTIFICATION_CREATED') {
        syncNotifications();
      }
    },
    [
      triggerOfferBrowserNotification,
      scheduleCoalescedRefresh,
      syncNotifications,
      reconcileOfferRemoved,
      reconcileJobCompleted,
      user,
    ]
  );

  const handleRealtimeReconcile = useCallback(() => {
    scheduleCoalescedRefresh(100);
    syncNotifications();
  }, [scheduleCoalescedRefresh, syncNotifications]);

  const handleRealtimeAuthFailure = useCallback(() => {
    console.warn('[Realtime SSE] Realtime connection interrupted; continuing REST polling.');
  }, []);

  const { connectionState: realtimeConnectionState } = useRealtimeStream({
    enabled: Boolean(isAuthenticated && isApprovedEmployee && isOnline),
    onEvent: handleRealtimeEvent,
    onReconcile: handleRealtimeReconcile,
    onAuthFailure: handleRealtimeAuthFailure,
  });

  // ── 12. Fast Presence Toggle Controller ────────────────────────────────────
  const togglePresenceFast = useCallback(
    async (desiredState = null) => {
      try {
        setPresenceState('CONNECTING');
        const res = await authTogglePresence(desiredState);
        if (res.is_online) {
          setPresenceState('ONLINE_LOCATION_PENDING');
          setGpsState(GPS_STATE.ACQUIRING);
          // Background GPS resolution without blocking presence completion
          getGPSPosition(false)
            .then((pos) => {
              handlePositionChange({
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
                accuracy: pos.coords.accuracy,
                speed: pos.coords.speed,
                heading: pos.coords.heading,
                captured_at: new Date(pos.timestamp || Date.now()).toISOString(),
                timestamp: pos.timestamp || Date.now(),
                is_geofence_ready: pos.coords.accuracy <= MAX_GEOFENCE_ACCURACY_METERS,
              });
            })
            .catch(() => {});
          refreshActiveJobs({ silent: true });
        } else {
          setPresenceState('OFFLINE');
          setGpsState(GPS_STATE.IDLE);
        }
        return res;
      } catch (err) {
        setPresenceState(isOnlineAuth ? 'ONLINE_LOCATION_PENDING' : 'OFFLINE');
        throw err;
      }
    },
    [authTogglePresence, isOnlineAuth, handlePositionChange, refreshActiveJobs]
  );

  // ── 13. Context Value Assembly ─────────────────────────────────────────────
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
      serverTimeOffset,
      getServerTimeNow: () => Date.now() + (serverTimeOffset || 0),

      // Location & Presence Canonical Runtime Telemetry Object
      presenceState,
      gpsState,
      isOnline,
      isGpsLive,
      isGpsGeofenceReady,
      isLocationPending,
      dispatchReady: isOnline && isGpsLive,
      liveLocation,
      latitude: liveLocation?.latitude ?? null,
      longitude: liveLocation?.longitude ?? null,
      accuracy: liveLocation?.accuracy ?? null,
      accuracyTier: liveLocation?.accuracy_tier || classifyAccuracy(liveLocation?.accuracy),
      speed: liveLocation?.speed ?? null,
      heading: liveLocation?.heading ?? null,
      capturedAt: liveLocation?.captured_at ?? null,
      receivedAt: liveLocation?.timestamp ? new Date(liveLocation.timestamp).toISOString() : null,
      serverTime: Date.now() + (serverTimeOffset || 0),
      movementStatus,
      freshnessState,
      geofenceStatus,
      locationState: isGpsGeofenceReady ? 'ready' : isGpsLive ? 'live' : isLocationPending ? 'locating' : 'idle',
      scanCurrentLocation,
      togglePresence: togglePresenceFast,

      // Auto Clock-In & Readiness
      autoClockIn,
      getClockInReadiness,

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
      serverTimeOffset,
      presenceState,
      gpsState,
      isOnline,
      isGpsLive,
      isGpsGeofenceReady,
      isLocationPending,
      liveLocation,
      movementStatus,
      freshnessState,
      geofenceStatus,
      scanCurrentLocation,
      togglePresenceFast,
      autoClockIn,
      getClockInReadiness,
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
