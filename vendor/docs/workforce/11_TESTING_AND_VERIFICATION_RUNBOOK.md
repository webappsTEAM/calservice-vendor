# 11. Testing & Verification Runbook

## 1. Automated Verification Suites

The Workforce platform features comprehensive end-to-end verification scripts covering concurrency, spatial accuracy, state transitions, and performance profiling.

```
┌─────────────────────────────────────────────────────────────┐
│                 TESTING PYRAMID & SUITES                    │
│                                                             │
│       ▲                                                     │
│      ╱ ╲     E2E Concurrency & Master Handover             │
│     ╱   ╲    - run_final_e2e_concurrency_and_regression.py  │
│    ╱─────╲   - run_master_customer_marketplace_handover.py  │
│   ╱       ╲                                                 │
│  ╱         ╲   Integration & Operational Verification       │
│ ╱           ╲  - test_job_dispatch_reliability.py           │
│╱─────────────╲ - test_estimation_and_quotation_suite.py     │
│               - test_location_tracking_flow.py              │
│                                                             │
│   Database Query Profiling & Performance                    │
│   - explain_analyze_audit.py                                │
│   - measure_browser_network_timing.py                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Test Execution Commands

All test scripts should be executed from within `vendor/backend` with the active Python virtual environment:

### 2.1 Master E2E Concurrency & Regression
```bash
cd vendor/backend
python run_final_e2e_concurrency_and_regression.py
```
**Validates:**
- 10 concurrent requests attempting to accept the same job offer (verifies only 1 succeeds).
- Multi-tier dispatch rings and automatic offer expirations.
- Double-entry ledger balance conservation.

### 2.2 Customer & Marketplace Handover Verification
```bash
cd vendor/backend
python run_master_customer_marketplace_handover_verification.py
```
**Validates:**
- Booking creation to technician arrival within 10m geofence.
- Customer Start OTP validation and proof photo uploads.
- Full quotation submission, customer approval, and cash collection.

### 2.3 Spatial Dispatch & 20km Radius Matching
```bash
cd vendor/backend
python test_admin_20km_spatial_dispatch.py
```
**Validates:**
- Haversine candidate scoring accurately prioritizes nearest qualified technician.
- Rejection of technicians outside the 20km geographic perimeter.

### 2.4 Live Location Tracking & Geofencing
```bash
cd vendor/backend
python test_location_tracking_flow.py
python test_stage2_live_location_flow.py
```
**Validates:**
- High-frequency GPS stream latency and breadcrumb trail persistence.
- 10m geofence trigger accuracy.

### 2.5 Database Query Count & Latency Audit
```bash
cd vendor/backend
python explain_analyze_audit.py
python measure_all_app_endpoints.py
```
**Validates:**
- PostgreSQL execution time vs WAN roundtrip time.
- Verifies absence of N+1 queries across core list endpoints.
