/**
 * speedAndCompassUtils.js
 *
 * Utilities for real device speed conversion, derived GPS velocity from displacement,
 * magnetic compass needle orientation, and shortest-path angular interpolation.
 */

/**
 * Derives speed in m/s from consecutive trusted GPS fixes if device GPS speed is null.
 * @param {{ latitude: number, longitude: number, timestamp?: number, captured_at?: string }} prevFix
 * @param {{ latitude: number, longitude: number, timestamp?: number, captured_at?: string }} currentFix
 * @returns {number|null} Speed in meters per second, or null if insufficient displacement/time
 */
export function deriveSpeedFromFixes(prevFix, currentFix) {
  if (!prevFix || !currentFix) return null;
  if (prevFix.latitude == null || currentFix.latitude == null) return null;

  const t1 = prevFix.timestamp || (prevFix.captured_at ? new Date(prevFix.captured_at).getTime() : 0);
  const t2 = currentFix.timestamp || (currentFix.captured_at ? new Date(currentFix.captured_at).getTime() : 0);
  if (!t1 || !t2 || t2 <= t1) return null;

  const dtSec = (t2 - t1) / 1000;
  if (dtSec < 0.5 || dtSec > 30) return null; // Reject sub-second noise or stale fixes

  // Haversine distance in meters
  const R = 6371000;
  const dLat = ((currentFix.latitude - prevFix.latitude) * Math.PI) / 180;
  const dLon = ((currentFix.longitude - prevFix.longitude) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((prevFix.latitude * Math.PI) / 180) *
      Math.cos((currentFix.latitude * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distMeters = R * c;

  if (distMeters < 1.0) return 0; // Stationary
  const speedMps = distMeters / dtSec;
  if (speedMps > 45) return null; // Filter implausible velocity spikes (>162 km/h)
  return speedMps;
}

/**
 * Converts real device speed from m/s to integer km/h with fallback to displacement-derived speed.
 * @param {number|null} speedMps - Speed in meters per second from device Geolocation
 * @param {number|null} [fallbackDerivedSpeedMps] - Speed derived from consecutive GPS fixes
 * @returns {{ value: number, text: string, unit: string, isAvailable: boolean }}
 */
export function formatSpeedKmh(speedMps, fallbackDerivedSpeedMps = null) {
  const effectiveSpeed = (speedMps != null && !isNaN(speedMps) && speedMps >= 0)
    ? speedMps
    : (fallbackDerivedSpeedMps != null && !isNaN(fallbackDerivedSpeedMps) && fallbackDerivedSpeedMps >= 0 ? fallbackDerivedSpeedMps : null);

  if (effectiveSpeed == null || effectiveSpeed < 0.3) {
    return {
      value: 0,
      text: '0',
      unit: 'km/h',
      isAvailable: effectiveSpeed != null,
    };
  }
  const kmh = Math.round(effectiveSpeed * 3.6);
  return {
    value: kmh,
    text: String(kmh),
    unit: 'km/h',
    isAvailable: true,
  };
}

/**
 * Calculates the counter-rotation angle for the North-pointing magnetic needle.
 * If the map is rotated to heading `mapHeading`, the needle must rotate `-mapHeading`
 * so it continues pointing towards true North.
 * @param {number} mapHeading - Current map heading in degrees (0 - 360)
 * @returns {number} Needle rotation in degrees
 */
export function calculateCompassRotation(mapHeading) {
  if (mapHeading == null || isNaN(mapHeading)) return 0;
  return (-mapHeading + 360) % 360;
}

/**
 * Shortest-path angular interpolation across the 360/0 degree boundary.
 * Prevents 350° -> 10° from spinning backwards through 180°.
 * @param {number} fromAngle - Starting angle in degrees
 * @param {number} toAngle - Target angle in degrees
 * @param {number} t - Interpolation factor (0 to 1)
 * @returns {number} Interpolated angle in degrees
 */
export function interpolateShortestAngle(fromAngle, toAngle, t) {
  const diff = ((toAngle - fromAngle + 180) % 360) - 180;
  const shortestDiff = diff < -180 ? diff + 360 : diff;
  return (fromAngle + shortestDiff * t + 360) % 360;
}
