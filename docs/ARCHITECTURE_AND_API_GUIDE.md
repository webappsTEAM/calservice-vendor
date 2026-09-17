# SEVO Platform — Architecture & API Technical Guide

This document provides a comprehensive technical overview of the **SEVO Vendor & Workforce Management Platform**, detailing system components, relational database architecture, multi-tenant isolation, dispatch state machines, estimation workflows, and API specifications.

---

## 1. System Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │          SEVO Client Tier              │
                      ├───────────────────┬────────────────────┤
                      │  React Admin/     │  Flutter Mobile    │
                      │  Vendor Dashboard │  (Field Tech App)  │
                      └─────────┬─────────┴─────────┬──────────┘
                                │                   │
                                ▼                   ▼
                      ┌────────────────────────────────────────┐
                      │    Workforce Backend (Django REST)     │
                      ├───────────────────┬────────────────────┤
                      │ • JWT Auth & RLS  │ • Dispatch Pipeline│
                      │ • Rate Engine     │ • Wallet / Ledger  │
                      │ • Geofence & GPS  │ • State Machines   │
                      └─────────┬─────────┴─────────┬──────────┘
                                │                   │
                                ▼                   ▼
                      ┌────────────────────────────────────────┐
                      │      Supabase PostgreSQL Database      │
                      │  (Multi-tenant, Relational Schema, RLS)│
                      └────────────────────────────────────────┘
```

---

## 2. Core Backend Modules & Schema Design

### A. Accounts & Tenant Isolation (`accounts/`, `companies/`)
* **`User`**: Core authentication model supporting roles: `SUPERADMIN`, `ADMIN`, `VENDOR_OWNER`, `VENDOR_MANAGER`, `TECHNICIAN`.
* **`Company` / `Tenant`**: Represents the vendor or service provider organization. All operational tables (technicians, jobs, rate cards, wallets) maintain strict `company_id` foreign keys.
* **Server-Side Enforcement**: Backend determines `company_id` directly from the authenticated JWT session. Frontend `company_id` inputs are strictly ignored to prevent tenant leakage.

### B. Employee & Technician Management (`employees/`)
* **`Employee`**: Profile linking a `User` to a `Company`, tracking employment status (`PENDING`, `APPROVED`, `SUSPENDED`), trade skills, base payout rates, and operational state (`ONLINE`, `OFFLINE`, `BUSY`, `ON_LEAVE`).
* **`EmployeeDocument`**: KYC documents (Aadhaar, Driving License, PAN, Trade Certificates). Tracks approval status (`PENDING_REVIEW`, `VALID`, `EXPIRED`, `REJECTED`).
* **`EmployeeSkill` & `EmployeeService`**: Relational mappings connecting technicians to canonical database service categories and skill proficiencies.

### C. Service Request, Dispatch & Estimation (`service_requests/`)
* **`ServiceRequest`**: Operational job record shared with Marketplace. Tracks customer requirement, schedule, assigned technician, operational status, and payment summary.
* **`WorkforceJobOffer`**: Ephemeral dispatch record sent to eligible candidate technicians within a 20km radius with an expiration timer (e.g. 5 minutes).
* **`RateCard` & `RateCardItem`**: Database-driven pricing tables defining base inspection charges, standard labor rates, and part catalog costs.
* **`Quotation` & `QuotationItem`**: Line-item estimates created by technicians during on-site inspections. Supports live rate calculation, customer authorization, and automated invoicing.

### D. Time Tracking & Presence (`time_tracking/`)
* **`AttendanceRecord`**: Daily clock-in/out records with geofence verification and GPS capture.
* **`TechnicianLocationLog`**: High-frequency GPS breadcrumbs recording technician movement during active transit (`on_the_way`).

### E. Vendor Wallet & Financials (`vendor_wallet/`)
* **`VendorWallet`**: Balance ledger for service providers and independent technicians.
* **`WalletTransaction`**: Immutable double-entry ledger records for job credits, commission deductions, cash-on-delivery adjustments, and bank payouts.

---

## 3. Operational State Machines

### A. Job Lifecycle State Transitions
```
                [Marketplace Booking Created]
                              │
                              ▼
                      status = 'new_request'
                              │
                    (Automatic Dispatch)
                              │
                              ▼
                      status = 'assigned'
                              │
                   (Technician Accepts)
                              │
                              ▼
                      status = 'accepted'
                              │
                   (Technician En Route)
                              │
                              ▼
                      status = 'on_the_way'
                              │
                     (Arrival / Checklist)
                              │
                              ▼
                      status = 'arrived'
                              │
                   (Work Started / Quotation)
                              │
                              ▼
                      status = 'in_progress'
                              │
                    (OTP & Work Proof Done)
                              │
                              ▼
                      status = 'completed'
```

### B. Document Verification State Transitions
```
   [Uploaded] ──► PENDING_REVIEW ──┬──► VALID (Approved)
                                    └──► REJECTED (Needs re-upload)
                                    └──► EXPIRED (Date-based)
```

---

## 4. Key API Endpoints Catalog

### Authentication & Profile
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/accounts/login/` | Authenticate and obtain JWT access & refresh tokens | No |
| `POST` | `/api/v1/accounts/token/refresh/` | Refresh expired JWT access token | No |
| `GET` | `/api/v1/accounts/me/` | Fetch current authenticated user, role, and tenant context | Yes |

### Technician Operations & Dispatch
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/employees/offers/` | List active job offers available to the logged-in technician | Yes (Tech) |
| `POST` | `/api/v1/employees/offers/{id}/accept/` | Atomically accept a job offer (with row-lock protection) | Yes (Tech) |
| `POST` | `/api/v1/employees/offers/{id}/reject/` | Decline a job offer | Yes (Tech) |
| `POST` | `/api/v1/employees/availability/` | Update technician status (`ONLINE`, `OFFLINE`, `BUSY`) | Yes (Tech) |

### Active Job Cockpit & Execution
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/service-requests/active/` | Get current active job details for the technician | Yes (Tech) |
| `POST` | `/api/v1/service-requests/{id}/status/` | Transition job status (`on_the_way`, `arrived`, `in_progress`) | Yes (Tech) |
| `POST` | `/api/v1/service-requests/{id}/arrival-checklist/`| Submit pre-service inspection & arrival photos | Yes (Tech) |
| `POST` | `/api/v1/service-requests/{id}/complete/` | Complete job with customer OTP verification & final proof | Yes (Tech) |

### Estimation & Invoicing Engine
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/estimations/rate-cards/` | Fetch available service rate cards & line-item prices | Yes |
| `POST` | `/api/v1/estimations/quotes/` | Create or revise quotation with dynamic rate calculation | Yes |
| `GET` | `/api/v1/estimations/quotes/{id}/` | Get quotation details & line-item breakdown | Yes |
| `POST` | `/api/v1/estimations/quotes/{id}/approve/` | Customer approval endpoint (via OTP or signature) | Yes |
| `GET` | `/api/v1/estimations/invoices/{id}/pdf/` | Generate & download official PDF tax invoice | Yes |

### Location & Attendance
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/time-tracking/clock-in/` | Clock in with GPS coordinates & geofence validation | Yes (Tech) |
| `POST` | `/api/v1/time-tracking/clock-out/` | Clock out of active shift | Yes (Tech) |
| `POST` | `/api/v1/time-tracking/location-update/` | Stream live GPS breadcrumb during transit | Yes (Tech) |

### Wallet & Financial Settlements
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/wallet/summary/` | Get wallet balance, pending payouts, and earnings overview | Yes (Vendor/Tech) |
| `GET` | `/api/v1/wallet/transactions/` | Paginated transaction history and settlement entries | Yes (Vendor/Tech) |
| `POST` | `/api/v1/wallet/payout-request/` | Request bank payout withdrawal | Yes (Vendor) |

---

## 5. Engineering Invariants & Security Principles

As codified in [`AGENTS.md`](file:///c:/Users/USER/Desktop/caldim%20projects/calservice-vendor/AGENTS.md):
1. **Relational Source of Truth**: All dynamic data (rates, services, locations, company tiers) is fetched from Supabase PostgreSQL. Hardcoded catalogs or mock fallbacks are prohibited.
2. **Concurrency & Double Assignment**: All dispatch operations execute within `transaction.atomic()` with `select_for_update()` to ensure exactly one technician can accept any job offer.
3. **No Fake / Demo Data**: Empty database queries must render clear empty UI states across web and mobile.
4. **Tenant Security**: All queries are automatically scoped by the user's validated tenant. No user can view or mutate records belonging to other companies.
