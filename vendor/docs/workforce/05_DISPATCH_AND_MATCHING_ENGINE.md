# 05. Dispatch & Spatial Matching Engine

## 1. Dispatch Architecture & Design Goals

The Dispatch Engine matches customer service bookings with qualified, active, and nearby field technicians. It guarantees low allocation latency, zero double-assignments under high concurrency, and hierarchical vendor prioritization.

```
                              Marketplace Service Booking
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │      VPS Dispatch Daemon (5s Loop)    │
                      │       or Realtime Trigger Signal      │
                      └───────────────────┬───────────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │       Eligibility Pre-Filtering       │
                      │  - Mandatory Documents APPROVED       │
                      │  - Mandatory Compliance VALID         │
                      │  - Skill & Service Mapped             │
                      │  - Shift CLOCKED_IN & is_online = True│
                      │  - is_busy = False (Not on active job)│
                      └───────────────────┬───────────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    Spatial Haversine Ranking (≤20km)  │
                      │  - Distance weight (60%)              │
                      │  - Rating average (25%)               │
                      │  - Completed jobs count (15%)         │
                      └───────────────────┬───────────────────┘
                                          │
                        ┌─────────────────┴─────────────────┐
                        ▼                                   ▼
              Tier 1: Internal Vendor             Tier 2 & 3 Fallback
              Technicians within assigned         Sub-Vendor Partners &
              Company network                     Cross-Vendor Network
                        │                                   │
                        └─────────────────┬─────────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │   Issue WorkforceJobOffer (5m TTL)    │
                      │       select_for_update Lock          │
                      └───────────────────────────────────────┘
```

---

## 2. Candidate Eligibility & Ranking Algorithm

### 2.1 Server-Side Eligibility Checks
A candidate technician is eligible only if ALL of the following criteria pass:
1. `account_type` is valid (`technician` or `driver`).
2. `approval_status == 'APPROVED'` and `registration_status == 'APPROVED'`.
3. All mandatory KYC documents are approved and unexpired.
4. Active `WorkShift` exists (technician is clocked in).
5. `is_online == True` (presence active).
6. `is_busy == False` (technician is not currently executing an active job).
7. Possesses the specific `Service` and `Skill` requirements for the booking category.
8. Current GPS location updated within the last 15 minutes and distance to booking site $\le 20\text{ km}$.

### 2.2 Spatial Scoring Formula
Eligible candidates are ranked using a multi-factor score:

$$\text{Score} = \left(1 - \frac{\text{Distance}}{20\text{ km}}\right) \times 0.60 + \left(\frac{\text{Rating}}{5.0}\right) \times 0.25 + \min\left(1.0, \frac{\text{Completed Jobs}}{100}\right) \times 0.15$$

---

## 3. Multi-Tier Dispatch Rings

To protect vendor autonomy while ensuring 100% booking fulfillment:
1. **Ring 1 — Assigned Vendor Network (0–5 mins):** The offer is dispatched exclusively to technicians belonging to the vendor company assigned to the booking.
2. **Ring 2 — Sub-Vendor & Partner Network (5–10 mins):** If internal technicians decline or timeout, the offer escalates to contracted sub-vendors and partner companies in the geographic cluster.
3. **Ring 3 — Cross-Vendor Marketplace Pool (10+ mins):** If unfulfilled, the offer enters the open platform pool to ensure customer SLA is met.

---

## 4. VPS Background Daemon & Auto-Sweep Architecture

To prevent customer booking delays:
- **VPS Systemd Service (`workforce-dispatch.service`):** Runs a continuous 5-second asynchronous sweep loop inspecting all unassigned bookings (`status = 'confirmed'`).
- **Frontend Safety-Net Polling (30s):** Technician frontend mobile dashboards execute a lightweight 30-second poll to ensure push notification misses are instantly recovered.
- **Immediate Push Webhook:** Real-time triggers fire immediately upon new booking creation.

---

## 5. Concurrency & Double-Assignment Protection

When a technician clicks "Accept Offer", the backend uses PostgreSQL row-level locking:
```python
with transaction.atomic():
    offer = WorkforceJobOffer.objects.select_for_update().get(id=offer_id)
    if offer.status != 'OFFERED' or offer.is_expired():
        raise ConcurrencyConflictError("Offer is no longer available.")
    
    sr = ServiceRequest.objects.select_for_update().get(id=offer.service_request_id)
    if sr.assigned_employee is not None:
        raise ConcurrencyConflictError("Job has already been assigned to another technician.")
    
    # Assign job and mark technician busy
    sr.assigned_employee = offer.employee
    sr.status = 'accepted'
    sr.save()
    
    offer.status = 'ACCEPTED'
    offer.save()
    
    offer.employee.is_busy = True
    offer.employee.save()
```
