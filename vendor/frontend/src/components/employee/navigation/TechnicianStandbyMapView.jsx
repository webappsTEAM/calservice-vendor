/**
 * TechnicianStandbyMapView.jsx
 *
 * Clean, modern Standby / Dispatch Radar Map View for CalTrack Technicians.
 * Renders when the technician has no active assignments or in-flight navigation.
 *
 * Features:
 *  - High-accuracy Google Maps view centered on technician live GPS coordinates.
 *  - Animated pulse marker & coverage perimeter indicating active dispatch radar.
 *  - Contextual Status Pill (Online Standby vs Offline Paused).
 *  - GPS Telemetry info & 1-click recenter button.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Radio, Crosshair, MapPin } from 'lucide-react';
import { loadMapsApi } from '../../../utils/loadGoogleMaps.js';

export function TechnicianStandbyMapView({
  technicianLocation,
  isOnline = true,
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const techMarkerRef = useRef(null);
  const radarCircleRef = useRef(null);
  const [apiLoaded, setApiLoaded] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [retryTick, setRetryTick] = useState(0);

  const resolveCoord = (...candidates) => {
    for (const c of candidates) {
      if (c !== null && c !== undefined && c !== '') {
        const num = parseFloat(c);
        if (!isNaN(num)) return num;
      }
    }
    return null;
  };

  const techLat = resolveCoord(technicianLocation?.latitude, technicianLocation?.lat) ?? 12.9716;
  const techLon = resolveCoord(technicianLocation?.longitude, technicianLocation?.lng, technicianLocation?.lon) ?? 77.5946;
  const accuracyMeters = technicianLocation?.accuracy ? Math.round(technicianLocation.accuracy) : null;

  // Load Google Maps API singleton
  useEffect(() => {
    let mounted = true;
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_KEY || import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
    if (!apiKey) {
      setApiError('Google Maps API key is not configured.');
      return;
    }
    setApiError(null);
    loadMapsApi(apiKey)
      .then(() => {
        if (mounted) setApiLoaded(true);
      })
      .catch((err) => {
        console.error('[STANDBY_MAP_LOAD_ERROR]', err);
        // Bug found: this component had no apiError state or fallback UI at
        // all -- a failed Google Maps load (bad key, network block,
        // ad-blocker) just left the map container permanently blank with
        // no explanation and no way to retry. Mirrors the fallback pattern
        // already used correctly on LocationPickerMap.jsx.
        if (mounted) setApiError('Could not load the map. Check your connection and try again.');
      });
    return () => {
      mounted = false;
    };
  }, [retryTick]);

  // Initialize Standby map
  useEffect(() => {
    if (!apiLoaded || !mapContainerRef.current || mapRef.current) return;
    if (!window.google?.maps?.Map) return;

    try {
      const google = window.google;
      const map = new google.maps.Map(mapContainerRef.current, {
        center: { lat: techLat, lng: techLon },
        zoom: 15,
        tilt: 0,
        heading: 0,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: true,
        styles: [
          { featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] },
          { featureType: 'transit', elementType: 'labels', stylers: [{ visibility: 'off' }] },
        ],
      });

      mapRef.current = map;
    } catch (err) {
      console.error('[STANDBY_MAP_INIT_ERROR]', err);
    }
  }, [apiLoaded, techLat, techLon]);

  // Update Technician Marker and Radar Circle on location changes
  useEffect(() => {
    if (!apiLoaded || !mapRef.current || !window.google?.maps) return;
    const google = window.google;
    const map = mapRef.current;
    const techPos = { lat: techLat, lng: techLon };

    if (!techMarkerRef.current) {
      techMarkerRef.current = new google.maps.Marker({
        position: techPos,
        map,
        title: 'Your Current Location',
        icon: {
          url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="16" fill="${isOnline ? '#10B981' : '#64748B'}" fill-opacity="0.2"/>
              <circle cx="18" cy="18" r="11" fill="${isOnline ? '#059669' : '#475569'}" stroke="#FFFFFF" stroke-width="3"/>
              <circle cx="18" cy="18" r="4.5" fill="#FFFFFF"/>
            </svg>
          `)}`,
          scaledSize: new google.maps.Size(32, 32),
          anchor: new google.maps.Point(16, 16),
        },
      });
    } else {
      techMarkerRef.current.setPosition(techPos);
    }

    // Radar perimeter circle (1km standby zone)
    if (!radarCircleRef.current) {
      radarCircleRef.current = new google.maps.Circle({
        map,
        center: techPos,
        radius: 1000,
        strokeColor: isOnline ? '#059669' : '#94A3B8',
        strokeOpacity: 0.6,
        strokeWeight: 1.5,
        fillColor: isOnline ? '#10B981' : '#CBD5E1',
        fillOpacity: 0.08,
      });
    } else {
      radarCircleRef.current.setCenter(techPos);
      radarCircleRef.current.setOptions({
        strokeColor: isOnline ? '#059669' : '#94A3B8',
        fillColor: isOnline ? '#10B981' : '#CBD5E1',
      });
    }
  }, [apiLoaded, techLat, techLon, isOnline]);

  const handleRecenter = () => {
    if (mapRef.current && window.google?.maps) {
      mapRef.current.panTo({ lat: techLat, lng: techLon });
      mapRef.current.setZoom(16);
    }
  };

  return (
    <div className="w-full h-full flex-1 flex flex-col min-h-0 bg-slate-900 relative overflow-hidden">
      {/* ── Top Floating Standby Status Banner ── */}
      <div className="absolute top-4 left-4 right-4 z-20 pointer-events-auto">
        <div className="bg-slate-900/90 backdrop-blur-md text-white rounded-2xl px-4 py-3 shadow-xl border border-slate-700/60 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
              isOnline ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700/50 text-slate-400'
            }`}>
              <Radio className={`w-5 h-5 ${isOnline ? 'animate-pulse' : ''}`} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full shrink-0 ${
                  isOnline ? 'bg-emerald-400 animate-ping' : 'bg-slate-400'
                }`} />
                <h2 className="text-xs font-black uppercase tracking-wider text-slate-100 truncate">
                  {isOnline ? 'Standby Radar Active' : 'Technician Offline'}
                </h2>
              </div>
              <p className="text-[11px] text-slate-400 truncate mt-0.5">
                {isOnline
                  ? 'Location broadcast active • Waiting for dispatch requests'
                  : 'Turn online to receive exclusive job dispatch requests'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleRecenter}
            title="Recenter Map to Current Location"
            className="p-2 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 text-slate-300 rounded-xl transition-all border border-slate-700 cursor-pointer shrink-0 shadow-2xs"
          >
            <Crosshair className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Map Container ── */}
      <div className="w-full flex-1 min-h-0 relative bg-slate-950">
        <div ref={mapContainerRef} className="w-full h-full absolute inset-0" />
        {apiError && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950 z-10 p-4">
            <div className="text-center">
              <MapPin className="w-6 h-6 text-rose-400 mx-auto mb-2" />
              <p className="text-xs text-rose-300 font-medium mb-3">{apiError}</p>
              <button
                type="button"
                onClick={() => setRetryTick((t) => t + 1)}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
              >
                Retry
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Telemetry Footer ── */}
      <div className="px-4 py-2 bg-slate-900/95 backdrop-blur-sm border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400 shrink-0">
        <div className="flex items-center gap-2">
          <MapPin className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
          <span>
            {techLat.toFixed(5)}, {techLon.toFixed(5)}
          </span>
          {accuracyMeters != null && (
            <span className="text-slate-500">
              (±{accuracyMeters}m GPS fix)
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-slate-500'}`} />
          <span>{isOnline ? 'DISPATCH_ONLINE' : 'DISPATCH_OFFLINE'}</span>
        </div>
      </div>
    </div>
  );
}

export default TechnicianStandbyMapView;
