# CALTRACK WORKFORCE — LOCATION SHARING, MOBILE NAVIGATION & LIVE CUSTOMER TRACKING
## Production Hardening Walkthrough & Verification Report

---

## 1. Executive Summary

This document details the production hardening of the end-to-end location persistence, mobile navigation, and live customer tracking flow for the CalTrack Workforce application. The complete lifecycle operates as a unified, low-latency, and highly resilient system—from mobile browser GPS acquisition to backend database persistence, SSE event distribution, and customer map rendering.

```
+---------------------------------------------------------------------------------------------------+
|                                  END-TO-END TELEMETRY PIPELINE                                    |
+---------------------------------------------------------------------------------------------------+

   [Mobile Device GPS]
          │
          ▼
   [useLocationTracker (Single Watcher)]  <--- continuous GPS watch, adaptive transmission policy
          │
          ▼ (Kinematic Jump Filter + Accuracy Tiers)
   [EmployeeRuntimeProvider]              <--- Canonical Telemetry Context Owner
          │
          ▼ HTTP POST /workforce/presence/location/ (Throttled by movement & heartbeat)
   [WorkforceLocationUpdateView]
          │
          ├──> Atomic DB Update (User.last_known_location)
          ├──> Concurrency-Safe Session (JobTrackingSession via select_for_update)
          ├──> Throttled History Points (JobLocationPoint: >=20m or >=30s)
          ├──> 2-Fix Automatic Arrival (Geofence <=250m, Single OTP Resolution)
          └──> Enriched SSE Dispatch (WorkforceEventLog: Customer + Tenant Admin Visibility)
                 │
                 ├──> [Customer App SSE Stream / Map View] (Live marker, accurate distance/ETA)
                 └──> [Technician First-Person Map] (60fps rAF interpolation, Course-Up, stabilized heading)
```

---

## 2. Core Architectural Pillars

### A. Single Authoritative GPS Owner
- **`EmployeeRuntimeProvider` / `useLocationTracker`**: Remains the **only** producer of device coordinates and continuous telemetry transmission in the frontend.
- Removed legacy duplicate GPS watchers across `TopHeader.jsx`, `JobTrackingMap.jsx`, `ClockInCard.jsx`, and `EmployeeDashboardPage.jsx`.
- Standardized continuous GPS watching without stop/start thrashing: Adaptive telemetry policies modulate network transmissions rather than restarting the hardware GPS sensor.

### B. Mobile-First GPS Acquisition & Accuracy Tiers
- Coordinates are classified according to strict physical accuracy tiers:
  - **`EXCELLENT`**: $\le 10\text{ m}$
  - **`GOOD`**: $\le 25\text{ m}$
  - **`USABLE`**: $\le 50\text{ m}$
  - **`POOR`**: $\le 100\text{ m}$
  - **`VERY_POOR`**: $> 100\text{ m}$
- **Adaptive Telemetry Transmission Policies**:
  - `ACTIVE_NAV` (active job transit): Dispatches on $\ge 8\text{m}$ movement or $10\text{s}$ heartbeat.
  - `ONLINE_IDLE` (clocked in / waiting): Dispatches on $\ge 25\text{m}$ movement or $30\text{s}$ heartbeat.
  - `STATIONARY` (stopped at light / idle): Dispatches on $\ge 15\text{m}$ movement or $40\text{s}$ heartbeat.

### C. Kinematic Velocity Jump & Out-of-Order Packet Defense
- **Frontend Filter (`isPlausibleMovement`)**: Evaluates displacement $\Delta d$, elapsed time $\Delta t$, and implied speed $v = \frac{\Delta d}{\Delta t}$. Rejects physical teleportation anomalies ($v > 45\text{ m/s} \approx 162\text{ km/h}$ over displacements $> 150\text{m}$).
- **Backend Filter (`WorkforceLocationUpdateView`)**: Evaluates incoming fixes against stored DB state (`User.last_known_location`). Rejects velocities exceeding $55\text{ m/s} \approx 198\text{ km/h}$ over $>200\text{m}$ jumps.
- **Out-of-Order Packet Defense**: GPS fixes received with `captured_at` older than the DB's latest recorded timestamp are safely recorded as historical telemetry without overwriting current active coordinates.

### D. Strict Separation of Distance Types
The platform strictly separates geospatial calculations across different layers:
1. **`GPS_DISTANCE_METERS`**: Direct Haversine straight-line distance. Used for live GPS telemetry, distance sanity checks, and coarse proximity.
2. **`ROAD_DISTANCE_METERS`**: Real turn-by-turn road distance returned by Google Directions API. Used for navigation prompts and route planning.
3. **`ARRIVAL_DISTANCE_METERS`**: Raw Haversine distance ($\le 250\text{m}$) used strictly for geofence validation and automatic arrival.
4. **`DISPATCH_DISTANCE_KM`**: Haversine distance used for 20 km candidate ranking and offer dispatching.
5. **Presentation Formatting Standards**:
   - $< 1\text{ km}$: Formatted as whole meters (e.g., `231 m`, `578 m`, `999 m`).
   - $1\text{--}10\text{ km}$: Formatted with 2 decimal places (e.g., `1.20 km`, `1.70 km`, `2.45 km`, `8.01 km`).
   - $> 10\text{ km}$: Formatted with 1 decimal place (e.g., `12.0 km`, `13.0 km`, `20.5 km`).

### E. Navigation State Machine & Routing Request Coalescing
- **Generation Counter (`routeRequestIdRef`)**: Every navigation routing request increments a generation counter. Stale or delayed Google Directions callbacks are discarded if a newer route request was dispatched.
- **In-Flight Request Coalescing (`inFlightRoutingRef` & `pendingRouteCoordsRef`)**: Prevents duplicate concurrent Directions API calls during rapid GPS fixes, queueing pending target coordinates.
- **Heading Stabilization**:
  - In motion ($\text{speed} \ge 1.2\text{ m/s}$ or displacement $\ge 4\text{m}$): Calculates forward bearing or adopts device GPS compass heading.
  - Stationary ($\text{speed} < 0.4\text{ m/s}$ and displacement $< 3\text{m}$): Locks heading orientation to prevent camera spinning or marker jitter when parked or stopped at red lights.

### F. Presentation-Only 60fps Marker Animation
- Marker interpolation runs strictly via browser `requestAnimationFrame` using spherical linear interpolation (Slerp) / linear lerping.
- Interpolated positions are **never** persisted to the backend database or used for geofence arrival decisions.

### G. Realtime SSE Propagation & Tenant Isolation
- **`JOB_LOCATION_UPDATE` SSE Events**: Dispatched upon every valid GPS fix, carrying complete tracking metadata (`job_id`, `company_id`, `employee_id`, `movement_status`, `geofence_status`, `freshness_state`, `distance_km`, `distance_m`, `start_otp`).
- **Tenant & Customer Scoping**: REST endpoints and SSE streams enforce tenant isolation and customer ownership (e.g., cross-tenant queries return HTTP 403/404).

---

## 3. Automated Test Suite Results

### A. Comprehensive Hardening Test Suite (`test_location_navigation_production_hardening.py`)

| Test Phase | Scope / Focus | Result |
| :--- | :--- | :---: |
| **[TEST A-G]** | Coordinate & Telemetry Validation (Out-of-range lat/lon rejection) | **PASSED** |
| **[TEST H-I]** | Telemetry Jump Protection (20 km teleportation velocity rejection) | **PASSED** |
| **[TEST J]** | Out-of-Order Packet Defense (Stale packet ignored) | **PASSED** |
| **[TEST K-P]** | Active Tracking Session Uniqueness & SSE Events (`company_id` enriched) | **PASSED** |
| **[TEST Q-V]** | 250m Geofence Boundary & Idempotent Automatic Arrival (Single OTP preserved) | **PASSED** |
| **[TEST W-AD]** | Customer Live Tracking REST & Separation of Distance | **PASSED** |
| **[TEST AE-AM]**| Tenant Isolation & Reassignment Safety (Cross-tenant HTTP 403/404) | **PASSED** |
| **[TEST AN-AT]**| DB Write Efficiency & Query Latency ($\approx 338\text{ms}$ total roundtrip) | **PASSED** |

```
===========================================================================
ALL PRODUCTION HARDENING VERIFICATION TESTS PASSED SUCCESSFULLY (A through AT)!
===========================================================================
```

### B. Regression Test Suite (`test_location_tracking_flow.py`)

```
======================================================================
LOCATION TRACKING & LIVE CUSTOMER VISIBILITY TEST SUITE
======================================================================
[TEST 1] Out-of-Range Coordinate Validation                     --> PASS
[TEST 2] Technician Moving Towards Customer                     --> PASS
[TEST 3] Out-of-Order Packet Protection                         --> PASS
[TEST 4] Approaching Customer (<1.0 km) Stationary at Light     --> PASS
[TEST 5] Entering Geofence (150m) Fix #1                        --> PASS
[TEST 6] Automatic Arrival (Fix #2 with >=2s separation)        --> PASS
[TEST 7] WorkforceJobLiveTrackingView REST Endpoint             --> PASS
[TEST 8] Concurrency & Reassignment Safety on Acceptance        --> PASS
======================================================================
ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY!
======================================================================
```

### C. Frontend Production Build (`npm run build`)

```
> caltrack-workforce-frontend@1.0.0 build
> vite build

vite v6.4.3 building for production...
transforming...
✓ 1900 modules transformed.
rendering chunks...
dist/index.html                     1.22 kB │ gzip:   0.60 kB
dist/assets/index-BrrTvHzM.css     82.05 kB │ gzip:  13.28 kB
dist/assets/index-vE_qayCi.js   1,020.69 kB │ gzip: 235.12 kB
✓ built in 7.74s
```

---

## 4. Key Modified Files & Artifacts

1. **`frontend/src/hooks/useGPSPosition.js`**:
   - Implemented `ACCURACY_TIER`, `classifyAccuracy`, `TELEMETRY_POLICIES`, `isPlausibleMovement`, and adaptive transmission throttling without restarting the GPS watcher.
2. **`frontend/src/context/EmployeeRuntimeProvider.jsx`**:
   - Canonical telemetry context exporting `gpsState`, `liveLocation`, `latitude`, `longitude`, `accuracyTier`, `movementStatus`, `freshnessState`, `geofenceStatus`, and `scanCurrentLocation`.
3. **`frontend/src/components/employee/navigation/navigationUtils.js`**:
   - Presentation distance formatter implementing whole meters for $<1\text{km}$, 2 decimals for $1\text{--}10\text{km}$, and 1 decimal for $>10\text{km}$.
4. **`frontend/src/components/employee/navigation/useTechnicianNavigation.js`**:
   - Navigation state machine with generation counter (`routeRequestIdRef`), in-flight request coalescing, off-route deviation detection, and heading stabilization.
5. **`backend/workforce_api/views.py`**:
   - Velocity jump safety filter and out-of-order packet protection in `WorkforceLocationUpdateView`.
   - `company_id` enriched in `WorkforceEventLog` for tenant admin and customer visibility.
   - Idempotent 2-fix automatic geofence arrival and single authoritative OTP resolution.
6. **`backend/test_location_navigation_production_hardening.py`**:
   - Complete automated test suite verifying points A through AT.

---

## 5. Conclusion & Operational Readiness

The location sharing, mobile navigation, and live customer tracking flow is fully hardened, tenant-isolated, concurrency-safe, and validated against all production criteria.
