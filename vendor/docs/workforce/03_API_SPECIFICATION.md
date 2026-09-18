# 03. Workforce API Specification

## 1. Authentication & Security Headers

All Workforce endpoints require standard JWT Bearer authentication:
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

All responses strictly follow the standard JSON envelope structure:
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

Error responses:
```json
{
  "error": "Error description message",
  "code": "ERROR_CODE",
  "details": {}
}
```

---

## 2. Core Endpoint Catalogue

### 2.1 Authentication & Session
- `POST /api/workforce/auth/login/`
  - Body: `{ "email": "tech@example.com", "password": "..." }`
  - Returns: JWT access & refresh tokens, user role (`admin`, `technician`, `sub_vendor`), company ID.
- `GET /api/workforce/auth/me/`
  - Returns authenticated user details, resolved company profile, active technician assignments, and permission flags.

### 2.2 Technician Presence & Clock-In
- `POST /api/workforce/technician/presence/`
  - Body: `{ "is_online": true }`
  - Updates availability status in real-time.
- `POST /api/workforce/technician/clock-in/`
  - Body: `{ "latitude": 13.0827, "longitude": 80.2707, "photo_url": "..." }`
  - Starts work shift and creates active attendance record.
- `POST /api/workforce/technician/clock-out/`
  - Body: `{ "latitude": 13.0827, "longitude": 80.2707 }`
  - Closes active shift; automatically denied if technician has active ongoing jobs (`is_busy = true`).

### 2.3 Dispatch & Job Offers
- `GET /api/workforce/offers/`
  - Lists pending job offers for the authenticated technician (`status = OFFERED`, `expires_at > now`).
- `POST /api/workforce/offers/{offer_id}/accept/`
  - Concurrency-safe acceptance (`select_for_update`).
  - Sets `ServiceRequest.status = 'accepted'`, assigns employee, and flags employee as `is_busy = true`.
- `POST /api/workforce/offers/{offer_id}/reject/`
  - Body: `{ "reason": "DISTANCE_TOO_FAR" }`
  - Rejects offer and triggers immediate candidate ranking re-dispatch to the next tier ring.

### 2.4 Job Operational Execution
- `POST /api/workforce/jobs/{job_id}/start-trip/`
  - Sets `ServiceRequest.status = 'on_the_way'` and initializes live GPS tracking session.
- `POST /api/workforce/jobs/{job_id}/arrived/`
  - Geofence verification check (10m accuracy).
  - Transitions status to `arrived` and triggers 6-digit Customer Start OTP.
- `POST /api/workforce/jobs/{job_id}/verify-otp/`
  - Body: `{ "otp": "481920", "pre_service_photos": ["url1", "url2", "url3"] }`
  - Validates customer OTP and transitions status to `in_progress`.
- `POST /api/workforce/jobs/{job_id}/submit-proof/`
  - Body: `{ "post_service_photos": ["url1", "url2"], "completion_notes": "...", "parts_replaced": [] }`
  - Transitions status to `proof_submitted`.
- `POST /api/workforce/jobs/{job_id}/cash-collection/`
  - Body: `{ "amount_collected": 450.00, "payment_method": "COD" }`
  - Updates `payment_status = 'collected'`, updates financial ledger, and debits technician floating cash.
- `POST /api/workforce/jobs/{job_id}/complete/`
  - Finalizes job lifecycle, marks `ServiceRequest.status = 'completed'`, and resets technician `is_busy = false`.

### 2.5 Live Location Stream & Customer Tracking
- `POST /api/workforce/jobs/{job_id}/location/`
  - Body: `{ "latitude": 13.0827, "longitude": 80.2707, "speed": 24.5, "heading": 180.2 }`
  - Streams high-frequency GPS breadcrumb.
- `GET /api/workforce/customer/jobs/{job_id}/tracking/`
  - Public/Customer-authenticated tracking endpoint.
  - Returns current technician latitude/longitude, heading, ETA (mins), distance remaining (km), and operational stage.

### 2.6 Estimations & Quotations
- `POST /api/workforce/inspection-sheets/`
  - Body: `{ "job_id": 105, "inspection_type": "PAINTING", "measurements": { "sqft": 1200 }, "images": [...] }`
  - Technician submits on-site diagnostic report.
- `POST /api/workforce/quotations/`
  - Body: `{ "job_id": 105, "items": [{ "type": "MATERIAL", "description": "Asian Paints Royal 20L", "qty": 2, "price": 4200 }], "tax_rate": 18.0 }`
  - Vendor Admin submits official multi-item quotation.
- `POST /api/workforce/customer/quotations/{quote_id}/decision/`
  - Body: `{ "decision": "APPROVED", "otp": "771928" }`
  - Customer approves or declines quotation with OTP.

### 2.7 Wallets & Financial Settlements
- `GET /api/workforce/wallet/balance/`
  - Returns company / technician current balance, floating cash balance, and pending payouts.
- `GET /api/workforce/wallet/ledger/`
  - Paginated list of double-entry ledger transactions (`JOB_EARNING`, `COMMISSION`, `CASH_COLLECTION`, `WITHDRAWAL`).
- `POST /api/workforce/wallet/withdraw/`
  - Body: `{ "amount": 5000.00, "bank_account_id": 12 }`
  - Submits payout withdrawal request for admin processing.

### 2.8 Stock & Inventory Management
- `GET /api/workforce/stock/`
  - Paginated list of inventory items with stock levels, gram precision, and category filters.
- `POST /api/workforce/stock/{id}/adjust/`
  - Body: `{ "delta_grams": 5000, "movement_type": "RESTOCK", "reason": "Weekly vendor restock batch #48" }`
  - Updates stock and logs immutable `StockMovement` entry.
- `GET /api/workforce/stock/{id}/movements/`
  - Full audit trail of stock adjustments, sales deductions, and cancellation restocks.
