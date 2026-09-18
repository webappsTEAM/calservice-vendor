# 06. Live Location Tracking & First-Person Navigation

## 1. System Overview

The live tracking and navigation subsystem provides Uber/Rapido-style real-time tracking for customers and turn-by-turn first-person GPS navigation for technicians.

```
┌─────────────────────────────────┐
│     Technician Mobile Device    │
│  - Geolocation WatchPosition    │
│  - DeviceOrientation Compass    │
└────────────────┬────────────────┘
                 │
                 │ POST /api/workforce/jobs/{id}/location/ (Every 3-5s)
                 ▼
┌─────────────────────────────────┐
│        Workforce Backend        │
│  - Location Ingestion API       │
│  - Breadcrumb History Storage   │
│  - 10m Geofence Arrival Check   │
└────────────────┬────────────────┘
                 │
                 │ SSE / Polling Stream (1-2s latency)
                 ▼
┌─────────────────────────────────┐
│       Customer Live Map UI      │
│  - Smooth Marker Interpolation  │
│  - Real-Time ETA & Distance     │
│  - Direct Call Technician       │
└─────────────────────────────────┘
```

---

## 2. 10-Meter Tight Geofence Arrival Detection

Previous legacy implementations used a loose 250m geofence, which caused premature arrival status transitions while technicians were still minutes away in traffic. The engine now enforces a **10-meter precision geofence**:

```python
def check_geofence_arrival(technician_lat, technician_lng, destination_lat, destination_lng):
    """
    Calculates Haversine distance. Returns True only if within 10 meters.
    """
    distance_meters = haversine_distance_meters(
        technician_lat, technician_lng, 
        destination_lat, destination_lng
    )
    
    # 10-Meter Strict Arrival Constraint
    GEOFENCE_RADIUS_METERS = 10.0
    return distance_meters <= GEOFENCE_RADIUS_METERS
```

When the geofence check passes:
1. `ServiceRequest.status` automatically updates to `arrived`.
2. A 6-digit Customer Start OTP is generated and made visible on the Customer App.
3. The technician app unlocks the "Enter OTP to Start Work" interface.

---

## 3. First-Person Turn-by-Turn Mobile Navigation

The technician frontend (`useTechnicianNavigation.js`) delivers a mobile-native navigation experience within the browser/PWA:

### Features
- **Dynamic Compass & Bearing:** Uses device orientation API to rotate the map in the direction of travel.
- **Voice Navigation:** Integrates Web Speech API (`window.speechSynthesis`) to announce turn-by-turn maneuvers (e.g., *"In 200 meters, turn right onto Anna Salai"*).
- **Speed & Altitude Telemetry:** Tracks real-time velocity (km/h) to adapt map zoom levels dynamically (higher zoom at high speeds, street-level zoom at junctions).
- **Off-Route Detection:** Detects deviation $\ge 50\text{ meters}$ from planned polyline and triggers automatic route recalculation.

---

## 4. Customer Tracking Interface (`CustomerTrackingPage.jsx`)

The customer-facing tracking page provides transparency and security:
- **Live Technician Vehicle Marker:** Rotates according to heading and smoothly interpolates between coordinates.
- **Dynamic ETA Display:** Computes real-time remaining travel time considering live route distance.
- **Direct Phone Contact:** Embedded "Call Technician" button allowing customers to contact their assigned technician directly upon offer acceptance.
- **Safety Banner & Verification Code:** Prompts customer with their secret 6-digit Start OTP to be shared only upon physical arrival.
