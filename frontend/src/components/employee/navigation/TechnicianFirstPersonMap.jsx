/**
 * TechnicianFirstPersonMap.jsx
 *
 * True First-Person Course-Up Navigation Map for CalTrack Technicians.
 * Matches Google Maps Navigation experience with:
 *  - Explicit Navigation Camera State Machine:
 *      * ROUTE_PREVIEW
 *      * ACTIVE_NAVIGATION
 *      * MANUAL_INTERACTION
 *      * RECENTERING
 *      * ARRIVAL
 *  - Course-Up Bearing Rotation following real device GPS movement heading.
 *  - Forward Camera Offset (technician situated in lower 25-30% of viewport).
 *  - Persistent Map and Marker instances (zero remounts / recreation).
 *  - Smooth 60fps requestAnimationFrame position & heading marker interpolation.
 *  - Controlled camera follow on GPS fixes (zero 60fps camera thrashing).
 *  - Speedometer dial (km/h from device GPS + displacement fallback).
 *  - Magnetic compass rose with North-pointing needle (Course-Up / North-Up toggle).
 *  - Follow-Mode auto-tracking with 1-click Resume Navigation.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Volume2,
  VolumeX,
  Search,
  AlertTriangle,
} from 'lucide-react';
import { loadMapsApi } from '../../../utils/loadGoogleMaps.js';
import { createNavigationPuckIcon } from './navigationPuckMarker.js';
import { formatSpeedKmh, calculateCompassRotation, interpolateShortestAngle } from './speedAndCompassUtils.js';
import { interpolatePosition } from './navigationUtils.js';

const ANIMATION_DURATION_MS = 450; // Responsive, snappy gliding interpolation between GPS fixes
const NAVIGATION_ZOOM = 18.5;

export const CAMERA_STATE = {
  ROUTE_PREVIEW: 'ROUTE_PREVIEW',
  ACTIVE_NAVIGATION: 'ACTIVE_NAVIGATION',
  MANUAL_INTERACTION: 'MANUAL_INTERACTION',
  RECENTERING: 'RECENTERING',
  ARRIVAL: 'ARRIVAL',
};

export function TechnicianFirstPersonMap({
  job,
  technicianLocation,
  heading = 0,
  custLat,
  custLon,
  directionsResult,
  cameraMode = 'driving', // 'driving' or 'overview'
  onCameraModeChange,
  isFollowMode = true,
  onFollowModeChange,
  isCourseUp = true,
  onToggleCourseUp,
  isFullscreen = false,
  geofenceRadius = 250,
  className = 'w-full h-full min-h-[380px]',
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const puckMarkerRef = useRef(null);
  const custMarkerRef = useRef(null);
  const geofenceCircleRef = useRef(null);
  const directionsRendererRef = useRef(null);

  // Authoritative Camera Controller State Machine Ref
  const cameraStateRef = useRef(
    cameraMode === 'overview' ? CAMERA_STATE.ROUTE_PREVIEW : CAMERA_STATE.ACTIVE_NAVIGATION
  );

  // Animation refs (strictly for marker rendering)
  const animFrameRef = useRef(null);
  const animStartTimeRef = useRef(0);
  const startPosRef = useRef(null);
  const targetPosRef = useRef(null);
  const currentPosRef = useRef(null);
  const currentHeadingRef = useRef(heading || 0);
  const targetHeadingRef = useRef(heading || 0);
  const lastCameraHeadingRef = useRef(heading || 0);

  const [apiLoaded, setApiLoaded] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_KEY || import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  // Load Google Maps API Script
  useEffect(() => {
    let mounted = true;
    if (!apiKey) return;
    loadMapsApi(apiKey)
      .then(() => {
        if (mounted) setApiLoaded(true);
      })
      .catch((err) => console.warn('[NAV_MAP_LOAD_ERROR]', err));
    return () => {
      mounted = false;
    };
  }, [apiKey]);

  // Compute forward-looking navigation camera center (offsets ~38m ahead along heading vector)
  // Placing the vehicle at the lower 25-30% of the viewport so the upcoming road is clearly visible
  const computeNavigationCenter = useCallback((lat, lng, headingDeg = 0) => {
    if (lat == null || lng == null) return { lat, lng };

    const offsetDistanceMeters = 38; // Places vehicle in lower 25-30% of viewport
    const earthRadius = 6371000;
    const headingRad = ((headingDeg || 0) * Math.PI) / 180;

    // Shift camera FORWARD along heading vector
    const deltaLat = (offsetDistanceMeters * Math.cos(headingRad)) / earthRadius * (180 / Math.PI);
    const deltaLng = (offsetDistanceMeters * Math.sin(headingRad)) / (earthRadius * Math.cos((lat * Math.PI) / 180)) * (180 / Math.PI);

    return {
      lat: lat + deltaLat,
      lng: lng + deltaLng,
    };
  }, []);

  // 1. Initialize Map Instance (Created Exactly Once per Mount)
  useEffect(() => {
    if (!apiLoaded || !mapContainerRef.current || mapRef.current) return;
    if (!window.google?.maps?.Map) return;

    try {
      const google = window.google;
      const initialLat = technicianLocation?.latitude ?? custLat ?? 12.9716;
      const initialLng = technicianLocation?.longitude ?? custLon ?? 77.5946;

      const map = new google.maps.Map(mapContainerRef.current, {
        center: { lat: initialLat, lng: initialLng },
        zoom: NAVIGATION_ZOOM,
        tilt: 45, // Perspective navigation tilt
        heading: isCourseUp ? (heading || 0) : 0,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: false, // Clean navigation canvas
        gestureHandling: 'greedy', // Seamless mobile touch navigation
        styles: [
          { featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] },
          { featureType: 'transit', elementType: 'labels', stylers: [{ visibility: 'off' }] },
        ],
      });

      mapRef.current = map;

      // Detect user manual gestures -> Transition to MANUAL_INTERACTION
      map.addListener('dragstart', () => {
        cameraStateRef.current = CAMERA_STATE.MANUAL_INTERACTION;
        if (onFollowModeChange) onFollowModeChange(false);
      });
      let userZoomPending = false;
      map.addListener('mousedown', () => { userZoomPending = true; });
      map.addListener('touchstart', () => { userZoomPending = true; }, { passive: true });
      map.addListener('zoom_changed', () => {
        if (userZoomPending) {
          userZoomPending = false;
          cameraStateRef.current = CAMERA_STATE.MANUAL_INTERACTION;
          if (onFollowModeChange) onFollowModeChange(false);
        }
      });
      map.addListener('dragend', () => { userZoomPending = false; });

      // Directions Renderer (Strictly preserves viewport during navigation)
      const directionsRenderer = new google.maps.DirectionsRenderer({
        map,
        suppressMarkers: true, // Use custom puck & customer pins
        preserveViewport: true, // NEVER allow Directions to override navigation camera
        polylineOptions: {
          strokeColor: '#2563EB', // Electric Blue road route
          strokeWeight: 7,
          strokeOpacity: 0.94,
        },
      });
      directionsRendererRef.current = directionsRenderer;

      setMapReady(true);
    } catch (err) {
      console.warn('[NAV_MAP_INIT_ERROR]', err);
    }
  }, [apiLoaded, custLat, custLon, heading, isCourseUp, onFollowModeChange, technicianLocation?.latitude, technicianLocation?.longitude]);

  // 2. Customer Destination Marker & Geofence Circle (Persistent)
  useEffect(() => {
    if (!mapReady || !mapRef.current || custLat == null || custLon == null || !window.google?.maps) return;
    const google = window.google;
    const custPos = { lat: custLat, lng: custLon };

    if (!custMarkerRef.current) {
      const customerPinSvg = {
        url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
          <svg xmlns="http://www.w3.org/2000/svg" width="46" height="54" viewBox="0 0 46 54">
            <defs>
              <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#000000" flood-opacity="0.4"/>
              </filter>
            </defs>
            <g filter="url(#shadow)">
              <path d="M23 0C10.3 0 0 10.3 0 23c0 15.2 20.4 30.1 21.3 30.8a2.5 2.5 0 0 0 3.4 0C25.6 53.1 46 38.2 46 23 46 10.3 35.7 0 23 0z" fill="#DC2626" stroke="#FFFFFF" stroke-width="2.5"/>
              <circle cx="23" cy="21" r="14" fill="#FFFFFF"/>
              <path d="M23 12l-8 7v9h5v-6h6v6h5v-9l-8-7z" fill="#DC2626"/>
            </g>
          </svg>
        `)}`,
        scaledSize: new google.maps.Size(42, 50),
        anchor: new google.maps.Point(21, 50),
      };

      custMarkerRef.current = new google.maps.Marker({
        position: custPos,
        map: mapRef.current,
        title: `Customer Site: ${job?.address || 'Destination'}`,
        icon: customerPinSvg,
        zIndex: 100,
      });
    } else {
      custMarkerRef.current.setPosition(custPos);
    }

    if (!geofenceCircleRef.current) {
      geofenceCircleRef.current = new google.maps.Circle({
        map: mapRef.current,
        center: custPos,
        radius: geofenceRadius || 250,
        strokeColor: '#10B981',
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: '#10B981',
        fillOpacity: 0.12,
        zIndex: 10,
      });
    } else {
      geofenceCircleRef.current.setCenter(custPos);
      geofenceCircleRef.current.setRadius(geofenceRadius || 250);
    }
  }, [mapReady, custLat, custLon, geofenceRadius, job?.address]);

  // 3. Technician Navigation Puck Marker Creation (Persistent)
  useEffect(() => {
    if (!mapReady || !mapRef.current || technicianLocation?.latitude == null || technicianLocation?.longitude == null || !window.google?.maps) return;
    const google = window.google;
    const techPos = { lat: technicianLocation.latitude, lng: technicianLocation.longitude };

    if (!puckMarkerRef.current) {
      currentPosRef.current = techPos;
      startPosRef.current = techPos;
      targetPosRef.current = techPos;
      currentHeadingRef.current = heading || 0;

      puckMarkerRef.current = new google.maps.Marker({
        position: techPos,
        map: mapRef.current,
        title: 'You (Technician)',
        icon: createNavigationPuckIcon(heading || 0, 56),
        zIndex: 300,
      });

      // Initial Camera Centering in ACTIVE_NAVIGATION mode
      if (cameraStateRef.current === CAMERA_STATE.ACTIVE_NAVIGATION) {
        const navCenter = computeNavigationCenter(techPos.lat, techPos.lng, heading || 0);
        mapRef.current.setCenter(navCenter);
      }
    }
  }, [computeNavigationCenter, heading, mapReady, technicianLocation?.latitude, technicianLocation?.longitude]);

  // 4. Synchronize Google Directions Result onto map (Does NOT reset camera or zoom)
  useEffect(() => {
    if (directionsRendererRef.current && directionsResult) {
      directionsRendererRef.current.setDirections(directionsResult);
    }
  }, [directionsResult]);

  // 5. Smooth 60fps Puck Marker Animation loop (Marker ONLY, zero camera thrashing)
  const animateStep = useCallback((timestamp) => {
    if (!animStartTimeRef.current) animStartTimeRef.current = timestamp;
    const elapsed = timestamp - animStartTimeRef.current;
    const progress = Math.min(1, elapsed / ANIMATION_DURATION_MS);

    if (startPosRef.current && targetPosRef.current) {
      const interpolatedPos = interpolatePosition(startPosRef.current, targetPosRef.current, progress);
      const interpolatedHeading = interpolateShortestAngle(currentHeadingRef.current, targetHeadingRef.current, progress);

      currentPosRef.current = interpolatedPos;

      if (puckMarkerRef.current && window.google?.maps) {
        puckMarkerRef.current.setPosition(new window.google.maps.LatLng(interpolatedPos.lat, interpolatedPos.lng));
        puckMarkerRef.current.setIcon(createNavigationPuckIcon(interpolatedHeading, 56));
      }
    }

    if (progress < 1) {
      animFrameRef.current = requestAnimationFrame(animateStep);
    } else {
      currentHeadingRef.current = targetHeadingRef.current;
      animStartTimeRef.current = 0;
    }
  }, []);

  // 6. Handle Incoming GPS telemetry update (Triggers marker interpolation & controlled camera update)
  useEffect(() => {
    if (!mapReady || technicianLocation?.latitude == null || technicianLocation?.longitude == null) return;
    const newTarget = { lat: technicianLocation.latitude, lng: technicianLocation.longitude };
    const newHeading = heading ?? currentHeadingRef.current;

    targetHeadingRef.current = newHeading;

    if (!currentPosRef.current) {
      currentPosRef.current = newTarget;
      startPosRef.current = newTarget;
      targetPosRef.current = newTarget;
      if (puckMarkerRef.current && window.google?.maps) {
        puckMarkerRef.current.setPosition(new window.google.maps.LatLng(newTarget.lat, newTarget.lng));
        puckMarkerRef.current.setIcon(createNavigationPuckIcon(newHeading, 56));
      }
    } else {
      startPosRef.current = { ...currentPosRef.current };
      targetPosRef.current = newTarget;
      animStartTimeRef.current = 0;

      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = requestAnimationFrame(animateStep);
    }

    // Authoritative Camera Controller: follow only in ACTIVE_NAVIGATION mode
    if (cameraStateRef.current === CAMERA_STATE.ACTIVE_NAVIGATION && mapRef.current) {
      const speed = technicianLocation?.speed || technicianLocation?.derived_speed || 0;
      const isMoving = speed >= 0.4;

      // Apply heading rotation if supported and moving
      if (isCourseUp && isMoving && typeof mapRef.current.setHeading === 'function') {
        const headingDiff = Math.abs(newHeading - lastCameraHeadingRef.current);
        if (headingDiff >= 3) {
          lastCameraHeadingRef.current = newHeading;
          mapRef.current.setHeading(newHeading);
        }
      }

      const navCenter = computeNavigationCenter(newTarget.lat, newTarget.lng, isCourseUp ? newHeading : 0);
      mapRef.current.panTo(navCenter);
    }

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [animateStep, computeNavigationCenter, heading, isCourseUp, mapReady, technicianLocation]);

  // 7. Camera State Machine Transition: Respond to cameraMode and Fullscreen transitions
  useEffect(() => {
    if (!mapRef.current || !window.google?.maps) return;
    const google = window.google;

    // Trigger map resize on fullscreen transition
    setTimeout(() => {
      if (!mapRef.current) return;
      google.maps.event.trigger(mapRef.current, 'resize');

      if (cameraMode === 'overview' && custLat != null && currentPosRef.current) {
        // Transition to ROUTE_PREVIEW mode
        cameraStateRef.current = CAMERA_STATE.ROUTE_PREVIEW;
        mapRef.current.setTilt(0);
        if (typeof mapRef.current.setHeading === 'function') {
          mapRef.current.setHeading(0);
        }
        const bounds = new google.maps.LatLngBounds();
        bounds.extend({ lat: custLat, lng: custLon });
        bounds.extend(currentPosRef.current);
        mapRef.current.fitBounds(bounds, { top: 120, right: 60, bottom: 120, left: 60 });
      } else if (cameraMode === 'driving') {
        // Transition back to ACTIVE_NAVIGATION mode
        cameraStateRef.current = CAMERA_STATE.ACTIVE_NAVIGATION;
        if (currentPosRef.current) {
          mapRef.current.setTilt(45);
          mapRef.current.setZoom(NAVIGATION_ZOOM);
          if (typeof mapRef.current.setHeading === 'function') {
            mapRef.current.setHeading(isCourseUp ? currentHeadingRef.current : 0);
          }
          const navCenter = computeNavigationCenter(
            currentPosRef.current.lat,
            currentPosRef.current.lng,
            isCourseUp ? currentHeadingRef.current : 0
          );
          mapRef.current.panTo(navCenter);
        }
      }
    }, 80);
  }, [cameraMode, computeNavigationCenter, custLat, custLon, isCourseUp, isFullscreen]);

  // Manual Recentering: Smoothly restores ACTIVE_NAVIGATION riding camera
  const handleRecenter = () => {
    cameraStateRef.current = CAMERA_STATE.RECENTERING;
    if (onFollowModeChange) onFollowModeChange(true);
    if (onCameraModeChange) onCameraModeChange('driving');

    if (mapRef.current && currentPosRef.current) {
      mapRef.current.setTilt(45);
      mapRef.current.setZoom(NAVIGATION_ZOOM);
      if (isCourseUp && typeof mapRef.current.setHeading === 'function') {
        mapRef.current.setHeading(currentHeadingRef.current);
      }
      const navCenter = computeNavigationCenter(
        currentPosRef.current.lat,
        currentPosRef.current.lng,
        isCourseUp ? currentHeadingRef.current : 0
      );
      mapRef.current.panTo(navCenter);
      cameraStateRef.current = CAMERA_STATE.ACTIVE_NAVIGATION;
    }
  };

  // Switch between Course-Up and North-Up
  const handleToggleNorthUp = () => {
    if (onToggleCourseUp) {
      onToggleCourseUp();
    } else {
      if (mapRef.current && typeof mapRef.current.setHeading === 'function') {
        mapRef.current.setHeading(0);
      }
    }
  };

  // Speed calculation with fallback to displacement-derived velocity
  const speedObj = formatSpeedKmh(technicianLocation?.speed, technicianLocation?.derived_speed);
  const compassNeedleRotation = calculateCompassRotation(isCourseUp ? (heading || 0) : 0);

  return (
    <div className={`relative overflow-hidden bg-slate-900 ${className}`}>
      {/* Map Canvas Container */}
      <div ref={mapContainerRef} className="w-full h-full min-h-full" />

      {/* ── 1. Floating Speedometer Dial (Bottom-Left) ── */}
      <div className="absolute left-4 bottom-6 z-20 pointer-events-auto">
        <div className="w-16 h-16 rounded-full bg-white/95 backdrop-blur-md shadow-2xl border-2 border-slate-200 flex flex-col items-center justify-center text-slate-900 select-none">
          <span className="text-xl font-black leading-none tracking-tight">
            {speedObj.text}
          </span>
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tight mt-0.5">
            km/h
          </span>
        </div>
      </div>

      {/* ── 2. Floating Action Controls Column (Right Side) ── */}
      <div className="absolute right-4 bottom-6 z-20 flex flex-col items-center gap-3 pointer-events-auto">
        {/* Compass Rose Widget (North needle) */}
        <button
          type="button"
          onClick={handleToggleNorthUp}
          title={isCourseUp ? 'Switch to North-Up' : 'Switch to Course-Up'}
          className="w-12 h-12 rounded-full bg-white/95 backdrop-blur-md shadow-xl border border-slate-200 flex items-center justify-center transition-transform hover:scale-105 active:scale-95 cursor-pointer"
        >
          <div
            className="transition-transform duration-300 ease-out flex items-center justify-center"
            style={{ transform: `rotate(${compassNeedleRotation}deg)` }}
          >
            <svg width="28" height="28" viewBox="0 0 28 28">
              {/* North Red Pointer */}
              <polygon points="14,3 18,14 14,12 10,14" fill="#EF4444" />
              {/* South White/Slate Pointer */}
              <polygon points="14,25 18,14 14,12 10,14" fill="#94A3B8" />
              <circle cx="14" cy="13" r="1.5" fill="#334155" />
            </svg>
          </div>
        </button>

        {/* Search / Landmark button */}
        <button
          type="button"
          onClick={() => {}}
          title="Search along route"
          className="w-12 h-12 rounded-full bg-white/95 backdrop-blur-md shadow-xl border border-slate-200 flex items-center justify-center text-slate-700 hover:text-slate-900 transition-transform hover:scale-105 active:scale-95 cursor-pointer"
        >
          <Search className="w-5 h-5 text-slate-700" />
        </button>

        {/* Audio Mute / Unmute Button */}
        <button
          type="button"
          onClick={() => setIsMuted((prev) => !prev)}
          title={isMuted ? 'Unmute Guidance' : 'Mute Guidance'}
          className="w-12 h-12 rounded-full bg-white/95 backdrop-blur-md shadow-xl border border-slate-200 flex items-center justify-center text-slate-700 hover:text-slate-900 transition-transform hover:scale-105 active:scale-95 cursor-pointer"
        >
          {isMuted ? <VolumeX className="w-5 h-5 text-slate-500" /> : <Volume2 className="w-5 h-5 text-slate-700" />}
        </button>

        {/* Report / Hazard Button */}
        <button
          type="button"
          onClick={() => {}}
          title="Report Hazard"
          className="flex items-center gap-1 px-3 py-2 rounded-full bg-white/95 backdrop-blur-md shadow-xl border border-slate-200 text-slate-800 text-xs font-bold transition-transform hover:scale-105 active:scale-95 cursor-pointer"
        >
          <div className="p-1 rounded-full bg-amber-500/10 text-amber-600">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <span>Report</span>
        </button>
      </div>

      {/* ── 3. Recenter / Follow Button (appears only when follow mode is paused) ── */}
      {(!isFollowMode || cameraMode === 'overview') && (
        <div
          className="absolute right-4 z-30 animate-[scalein_0.18s_ease-out] pointer-events-auto"
          style={{ bottom: 'calc(1.5rem + 232px)' /* sits 8px above the controls column */ }}
        >
          <button
            type="button"
            onClick={handleRecenter}
            title="Recenter on my location"
            className="w-12 h-12 rounded-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white shadow-2xl border-2 border-white flex items-center justify-center transition-transform hover:scale-110 active:scale-95 cursor-pointer"
          >
            {/* GPS target / crosshair icon */}
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="4" />
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="2" y1="12" x2="6" y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
            </svg>
          </button>
        </div>
      )}

      {/* ── 4. Real GPS Accuracy Indicator ── */}
      {technicianLocation?.accuracy != null && (
        <div className="absolute left-4 top-4 z-10 px-2.5 py-1 bg-slate-900/80 backdrop-blur-xs text-white text-[10px] font-bold rounded-full border border-white/10 flex items-center gap-1.5 shadow-sm select-none">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>GPS ±{Math.round(technicianLocation.accuracy)}m</span>
        </div>
      )}
    </div>
  );
}
