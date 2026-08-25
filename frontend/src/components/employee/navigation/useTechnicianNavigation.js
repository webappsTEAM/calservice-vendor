/**
 * useTechnicianNavigation.js
 *
 * Dedicated Navigation State Machine Hook for CalTrack Field Technicians.
 *
 * Manages:
 *  - High-accuracy GPS telemetry reception with out-of-order packet rejection.
 *  - Google Maps Directions routing with strict 50m movement & 30s rate-limit throttling.
 *  - Active step progression and distance-to-next-turn calculation.
 *  - Off-route detection and automatic recalculation.
 *  - Dynamic driving ETA, remaining distance, and estimated arrival clock.
 *  - Follow-Mode camera state and manual pan detection.
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  calculateDistanceMeters,
  calculateBearing,
  computeCrossTrackDistanceMeters,
  formatDistance,
  formatEtaMinutes,
  computeArrivalTimeClock,
} from './navigationUtils.js';
import {
  parseRouteStep,
  findActiveStepIndex,
  computeDistanceToNextManeuver,
  getUpcomingManeuverPreview,
  computeRemainingRoadDistanceMeters,
} from './maneuverUtils.js';
import { deriveSpeedFromFixes } from './speedAndCompassUtils.js';
import { loadMapsApi } from '../../../utils/loadGoogleMaps.js';

const MIN_ROUTING_INTERVAL_MS = 30_000; // 30 seconds minimum between Directions requests
const MIN_ROUTING_MOVEMENT_METERS = 50;  // 50 meters movement threshold
const OFF_ROUTE_THRESHOLD_METERS = 65;   // 65 meters cross-track deviation triggers recalculation

export function useTechnicianNavigation({
  job,
  initialTechnicianLocation,
  onLocationReport,
}) {
  const custLat = job?.latitude != null
    ? parseFloat(job.latitude)
    : (job?.customer_latitude != null
      ? parseFloat(job.customer_latitude)
      : (job?.lat != null ? parseFloat(job.lat) : null));

  const custLon = job?.longitude != null
    ? parseFloat(job.longitude)
    : (job?.customer_longitude != null
      ? parseFloat(job.customer_longitude)
      : (job?.lon != null ? parseFloat(job.lon) : (job?.lng != null ? parseFloat(job.lng) : null)));

  // Real technician live coordinates
  const [technicianLocation, setTechnicianLocation] = useState(
    initialTechnicianLocation
      ? {
          latitude: parseFloat(initialTechnicianLocation.latitude),
          longitude: parseFloat(initialTechnicianLocation.longitude),
          accuracy: initialTechnicianLocation.accuracy ?? null,
          speed: initialTechnicianLocation.speed ?? null,
          derived_speed: null,
          heading: initialTechnicianLocation.heading ?? null,
          captured_at: initialTechnicianLocation.captured_at || initialTechnicianLocation.updated_at || new Date().toISOString(),
        }
      : null
  );

  const [heading, setHeading] = useState(initialTechnicianLocation?.heading ?? 0);
  const [isFollowMode, setIsFollowMode] = useState(true);
  const [directionsResult, setDirectionsResult] = useState(null);
  const [routeSteps, setRouteSteps] = useState([]);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [isRecalculating, setIsRecalculating] = useState(false);
  const [directionsFailed, setDirectionsFailed] = useState(false);
  const [lastUpdateSecondsAgo, setLastUpdateSecondsAgo] = useState(0);

  // Performance, concurrency and throttling refs
  const lastCapturedAtRef = useRef(technicianLocation?.captured_at ? new Date(technicianLocation.captured_at).getTime() : 0);
  const lastRoutingTimeRef = useRef(0);
  const lastRoutedCoordsRef = useRef({ lat: null, lng: null });
  const prevPositionRef = useRef(technicianLocation ? { lat: technicianLocation.latitude, lng: technicianLocation.longitude } : null);
  const prevFixWithTimestampRef = useRef(technicianLocation ? { latitude: technicianLocation.latitude, longitude: technicianLocation.longitude, timestamp: Date.now() } : null);
  const stableHeadingRef = useRef(heading || 0);
  const directionsServiceRef = useRef(null);
  const routeRequestIdRef = useRef(0);
  const inFlightRoutingRef = useRef(false);
  const pendingRouteCoordsRef = useRef(null);

  // Synchronize initial technician location prop
  useEffect(() => {
    if (initialTechnicianLocation?.latitude != null && initialTechnicianLocation?.longitude != null) {
      const incomingCapturedAt = initialTechnicianLocation.captured_at || initialTechnicianLocation.updated_at;
      const incomingTime = incomingCapturedAt ? new Date(incomingCapturedAt).getTime() : Date.now();

      if (incomingTime >= lastCapturedAtRef.current) {
        lastCapturedAtRef.current = incomingTime;
        const newCoords = {
          latitude: parseFloat(initialTechnicianLocation.latitude),
          longitude: parseFloat(initialTechnicianLocation.longitude),
          accuracy: initialTechnicianLocation.accuracy ?? null,
          speed: initialTechnicianLocation.speed ?? null,
          heading: initialTechnicianLocation.heading ?? null,
          captured_at: new Date(incomingTime).toISOString(),
        };
        setTechnicianLocation(newCoords);
        if (newCoords.heading != null && !isNaN(newCoords.heading)) {
          stableHeadingRef.current = newCoords.heading;
          setHeading(newCoords.heading);
        }
      }
    }
  }, [initialTechnicianLocation]);

  // Request authoritative route from Google Directions Service (Throttled + In-flight Coalesced + Generation Protected)
  const requestRoadRoute = useCallback(
    (originLat, originLng, destLat, destLng, force = false) => {
      if (originLat == null || destLat == null) return;

      // Guard: Google Maps must be fully initialized with DirectionsService available
      const mapsReady = (
        typeof window !== 'undefined' &&
        window.google?.maps &&
        typeof window.google.maps.DirectionsService === 'function'
      );

      if (!mapsReady) {
        // Retry once the API finishes bootstrapping (checked every 300ms, max 10s)
        const retryStarted = Date.now();
        const retryInterval = setInterval(() => {
          if (
            typeof window.google?.maps?.DirectionsService === 'function' ||
            Date.now() - retryStarted > 10_000
          ) {
            clearInterval(retryInterval);
            if (typeof window.google?.maps?.DirectionsService === 'function') {
              requestRoadRoute(originLat, originLng, destLat, destLng, force);
            }
          }
        }, 300);
        return;
      }

      // If a route request is currently in-flight, coalesce by queueing the latest desired coordinates
      if (inFlightRoutingRef.current) {
        pendingRouteCoordsRef.current = { originLat, originLng, destLat, destLng, force };
        return;
      }

      const now = Date.now();

      // Check time throttle (unless forced)
      if (!force && now - lastRoutingTimeRef.current < MIN_ROUTING_INTERVAL_MS) {
        return;
      }

      // Check distance movement threshold (unless forced)
      if (!force && lastRoutedCoordsRef.current.lat != null) {
        const movedMeters = calculateDistanceMeters(
          lastRoutedCoordsRef.current.lat,
          lastRoutedCoordsRef.current.lng,
          originLat,
          originLng
        );
        if (movedMeters != null && movedMeters < MIN_ROUTING_MOVEMENT_METERS) {
          return;
        }
      }

      if (!directionsServiceRef.current) {
        directionsServiceRef.current = new window.google.maps.DirectionsService();
      }

      const currentRequestId = ++routeRequestIdRef.current;
      inFlightRoutingRef.current = true;
      lastRoutingTimeRef.current = now;
      lastRoutedCoordsRef.current = { lat: originLat, lng: originLng };
      setIsRecalculating(true);

      directionsServiceRef.current.route(
        {
          origin: new window.google.maps.LatLng(originLat, originLng),
          destination: new window.google.maps.LatLng(destLat, destLng),
          travelMode: window.google.maps.TravelMode.DRIVING,
        },
        (result, status) => {
          inFlightRoutingRef.current = false;
          setIsRecalculating(false);

          // Discard stale out-of-order responses
          if (currentRequestId !== routeRequestIdRef.current) {
            console.info(`[useTechnicianNavigation] Discarded stale route response #${currentRequestId} (latest: #${routeRequestIdRef.current})`);
            return;
          }

          if (status === window.google.maps.DirectionsStatus.OK && result?.routes?.[0]?.legs?.[0]) {
            setDirectionsResult(result);
            setDirectionsFailed(false);

            const rawSteps = result.routes[0].legs[0].steps || [];
            const parsedSteps = rawSteps.map((step, idx) =>
              parseRouteStep(step, idx, idx === rawSteps.length - 1)
            );
            setRouteSteps(parsedSteps);
            setActiveStepIndex(0);
          } else {
            console.warn('[NAVIGATION_DIRECTIONS_STATUS]', status);
            setDirectionsFailed(true);
          }

          // Process queued pending route request if any
          if (pendingRouteCoordsRef.current) {
            const pending = pendingRouteCoordsRef.current;
            pendingRouteCoordsRef.current = null;
            requestRoadRoute(pending.originLat, pending.originLng, pending.destLat, pending.destLng, pending.force);
          }
        }
      );
    },
    []
  );

  // Listen to live GPS location updates from centralized watcher
  useEffect(() => {
    const handleLocationUpdate = (e) => {
      const detail = e.detail;
      if (detail?.latitude == null || detail?.longitude == null) return;

      const incomingTimestamp = detail.timestamp || Date.now();
      const incomingCapturedAt = detail.captured_at ? new Date(detail.captured_at).getTime() : incomingTimestamp;

      // ── Out-of-Order Packet Defense Invariant ──
      if (incomingCapturedAt < lastCapturedAtRef.current) {
        return; // Discard stale/delayed packet
      }
      lastCapturedAtRef.current = incomingCapturedAt;

      const lat = parseFloat(detail.latitude);
      const lng = parseFloat(detail.longitude);
      const rawSpeed = detail.speed != null ? parseFloat(detail.speed) : null;

      // Compute derived speed from displacement if rawSpeed is unavailable
      let derivedSpeed = null;
      if (prevFixWithTimestampRef.current) {
        derivedSpeed = deriveSpeedFromFixes(prevFixWithTimestampRef.current, {
          latitude: lat,
          longitude: lng,
          timestamp: incomingCapturedAt,
        });
      }
      prevFixWithTimestampRef.current = {
        latitude: lat,
        longitude: lng,
        timestamp: incomingCapturedAt,
      };

      const effectiveSpeed = (rawSpeed != null && rawSpeed >= 0) ? rawSpeed : (derivedSpeed ?? null);

      // Dynamic heading stabilization:
      // When moving (speed >= 1.0 m/s or moved >= 3.5m): update heading from GPS or forward azimuth
      // When stationary (speed < 0.4 m/s and moved < 3m): freeze heading to eliminate marker jitter
      let currentHeading = stableHeadingRef.current;
      let movedMeters = 0;

      if (prevPositionRef.current) {
        movedMeters = calculateDistanceMeters(prevPositionRef.current.lat, prevPositionRef.current.lng, lat, lng) || 0;
      }

      const isMoving = (effectiveSpeed != null && effectiveSpeed >= 1.0) || movedMeters >= 3.5;
      const isStationary = (effectiveSpeed != null && effectiveSpeed < 0.4) && movedMeters < 3.0;

      if (isMoving) {
        if (detail.heading != null && !isNaN(detail.heading)) {
          currentHeading = detail.heading;
        } else if (prevPositionRef.current && movedMeters >= 3.0) {
          currentHeading = calculateBearing(prevPositionRef.current.lat, prevPositionRef.current.lng, lat, lng);
        }
        stableHeadingRef.current = currentHeading;
        setHeading(currentHeading);
      } else if (!isStationary && detail.heading != null && !isNaN(detail.heading)) {
        currentHeading = detail.heading;
        stableHeadingRef.current = currentHeading;
        setHeading(currentHeading);
      }

      prevPositionRef.current = { lat, lng };

      const newCoords = {
        latitude: lat,
        longitude: lng,
        accuracy: detail.accuracy ?? null,
        speed: effectiveSpeed,
        derived_speed: derivedSpeed,
        heading: currentHeading,
        captured_at: new Date(incomingCapturedAt).toISOString(),
      };

      setTechnicianLocation(newCoords);

      // Notify parent if callback provided
      if (onLocationReport) {
        onLocationReport(newCoords);
      }

      // Check step progression
      if (routeSteps.length > 0) {
        const nextIdx = findActiveStepIndex(routeSteps, lat, lng, activeStepIndex);
        if (nextIdx !== activeStepIndex) {
          setActiveStepIndex(nextIdx);
        }

        // Off-route check
        const activeStep = routeSteps[activeStepIndex];
        if (activeStep?.startLocation && activeStep?.endLocation) {
          const crossTrackDist = computeCrossTrackDistanceMeters(
            { lat, lng },
            activeStep.startLocation,
            activeStep.endLocation
          );
          if (crossTrackDist > OFF_ROUTE_THRESHOLD_METERS && custLat != null && custLon != null) {
            requestRoadRoute(lat, lng, custLat, custLon, true);
          }
        }
      }

      // Check if routing should be requested
      if (custLat != null && custLon != null && !directionsResult) {
        requestRoadRoute(lat, lng, custLat, custLon, true);
      } else if (custLat != null && custLon != null) {
        requestRoadRoute(lat, lng, custLat, custLon, false);
      }
    };

    window.addEventListener('workforce:location-updated', handleLocationUpdate);
    return () => {
      window.removeEventListener('workforce:location-updated', handleLocationUpdate);
    };
  }, [activeStepIndex, custLat, custLon, directionsResult, onLocationReport, requestRoadRoute, routeSteps]);

  // Load Google Maps API Script
  useEffect(() => {
    loadMapsApi()
      .then(() => {
        if (custLat != null && custLon != null && technicianLocation?.latitude != null && !directionsResult) {
          requestRoadRoute(technicianLocation.latitude, technicianLocation.longitude, custLat, custLon, true);
        }
      })
      .catch((err) => console.warn('[NAV_HOOK_MAP_LOAD_ERROR]', err));
  }, [custLat, custLon, directionsResult, requestRoadRoute, technicianLocation]);

  // Initial Route Request on mount if coordinates exist
  useEffect(() => {
    if (custLat != null && custLon != null && technicianLocation?.latitude != null && !directionsResult) {
      requestRoadRoute(technicianLocation.latitude, technicianLocation.longitude, custLat, custLon, true);
    }
  }, [custLat, custLon, directionsResult, requestRoadRoute, technicianLocation]);

  // Freshness timer
  useEffect(() => {
    const timer = setInterval(() => {
      if (technicianLocation?.captured_at) {
        const diffSec = Math.max(0, Math.round((Date.now() - new Date(technicianLocation.captured_at).getTime()) / 1000));
        setLastUpdateSecondsAgo(diffSec);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [technicianLocation]);

  // Active maneuver step details
  const activeStep = useMemo(() => {
    if (!routeSteps || routeSteps.length === 0) return null;
    return routeSteps[activeStepIndex] || routeSteps[0];
  }, [routeSteps, activeStepIndex]);

  const upcomingPreview = useMemo(() => {
    return getUpcomingManeuverPreview(routeSteps, activeStepIndex);
  }, [routeSteps, activeStepIndex]);

  const distanceToNextManeuverMeters = useMemo(() => {
    if (!activeStep || technicianLocation?.latitude == null) return activeStep?.stepDistanceMeters ?? 0;
    return computeDistanceToNextManeuver(activeStep, technicianLocation.latitude, technicianLocation.longitude);
  }, [activeStep, technicianLocation]);

  // Explicit Separation of Distance Types:
  // 1. Straight-Line Haversine GPS Distance
  const gpsDistanceMeters = useMemo(() => {
    return calculateDistanceMeters(
      technicianLocation?.latitude,
      technicianLocation?.longitude,
      custLat,
      custLon
    );
  }, [technicianLocation?.latitude, technicianLocation?.longitude, custLat, custLon]);

  // 2. Dynamic Remaining Road Route Distance along upcoming route steps
  const totalLeg = directionsResult?.routes?.[0]?.legs?.[0];
  const originalLegDistance = totalLeg?.distance?.value ?? null;
  const originalLegDuration = totalLeg?.duration?.value ?? null;

  const dynamicRemainingRoadMeters = useMemo(() => {
    if (routeSteps && routeSteps.length > 0) {
      return computeRemainingRoadDistanceMeters(routeSteps, activeStepIndex, distanceToNextManeuverMeters);
    }
    return originalLegDistance;
  }, [routeSteps, activeStepIndex, distanceToNextManeuverMeters, originalLegDistance]);

  const roadDistanceMeters = dynamicRemainingRoadMeters ?? originalLegDistance ?? gpsDistanceMeters;

  // 3. Dynamic ETA based on route velocity or urban transit baseline (~25 km/h)
  const effectiveSpeedMps = useMemo(() => {
    if (originalLegDistance && originalLegDuration && originalLegDuration > 0) {
      return Math.max(3.0, originalLegDistance / originalLegDuration);
    }
    return 7.0; // ~25.2 km/h default
  }, [originalLegDistance, originalLegDuration]);

  const dynamicRoadDurationSeconds = useMemo(() => {
    if (roadDistanceMeters != null && roadDistanceMeters > 0) {
      return Math.max(15, Math.round(roadDistanceMeters / effectiveSpeedMps));
    }
    if (gpsDistanceMeters != null && gpsDistanceMeters > 0) {
      return Math.max(15, Math.round((gpsDistanceMeters / 1000) * 180));
    }
    return null;
  }, [roadDistanceMeters, effectiveSpeedMps, gpsDistanceMeters]);

  const displayDistanceText = roadDistanceMeters != null
    ? formatDistance(roadDistanceMeters)
    : (gpsDistanceMeters != null ? formatDistance(gpsDistanceMeters) : '--');

  const displayEtaText = dynamicRoadDurationSeconds != null
    ? formatEtaMinutes(dynamicRoadDurationSeconds)
    : '--';

  const arrivalClockText = useMemo(() => {
    return computeArrivalTimeClock(dynamicRoadDurationSeconds);
  }, [dynamicRoadDurationSeconds]);

  // Explicit Navigation State Machine
  const navigationState = useMemo(() => {
    if (!technicianLocation?.latitude) return 'GPS_UNAVAILABLE';
    if (gpsDistanceMeters != null && gpsDistanceMeters <= 250) return 'ARRIVED';
    if (gpsDistanceMeters != null && gpsDistanceMeters <= 500) return 'ARRIVING';
    if (isRecalculating) return 'REROUTING';
    if (directionsResult) return 'NAVIGATING';
    if (directionsFailed) return 'NAVIGATING'; // Fallback to direct GPS navigation
    return 'CALCULATING';
  }, [technicianLocation, gpsDistanceMeters, isRecalculating, directionsResult, directionsFailed]);

  // Telemetry status badge
  const telemetryStatus = useMemo(() => {
    if (!technicianLocation?.captured_at) return { label: 'ACQUIRING GPS', tone: 'amber' };
    if (lastUpdateSecondsAgo <= 5) return { label: 'LIVE', tone: 'emerald' };
    if (lastUpdateSecondsAgo <= 15) return { label: 'UPDATING', tone: 'blue' };
    if (lastUpdateSecondsAgo <= 30) return { label: 'DELAYED', tone: 'amber' };
    return { label: 'LOCATION LOST', tone: 'rose' };
  }, [lastUpdateSecondsAgo, technicianLocation]);

  // Resume Navigation Follow Mode
  const handleResumeNavigation = useCallback(() => {
    setIsFollowMode(true);
  }, []);

  return {
    technicianLocation,
    heading,
    custLat,
    custLon,
    directionsResult,
    routeSteps,
    activeStep,
    activeStepIndex,
    upcomingPreview,
    distanceToNextManeuverMeters,
    distanceToNextManeuverText: formatDistance(distanceToNextManeuverMeters),
    gpsDistanceMeters,
    roadDistanceMeters,
    totalDistanceMeters: roadDistanceMeters ?? gpsDistanceMeters,
    roadDurationSeconds: dynamicRoadDurationSeconds,
    displayDistanceText,
    displayEtaText,
    arrivalClockText,
    navigationState,
    isFollowMode,
    setIsFollowMode,
    handleResumeNavigation,
    isRecalculating,
    directionsFailed,
    telemetryStatus,
    lastUpdateSecondsAgo,
    requestRoadRoute,
  };
}
