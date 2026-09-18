# 01. Workforce Management System Architecture

## 1. System Vision & Core Objectives

The **CalServices / Sevo Workforce Platform** is an enterprise-grade field service management and technician dispatch engine. It manages service providers, independent contractors, sub-vendor networks, and field technicians across various home services (HVAC, plumbing, electrical, carpentry, painting, masonry) as well as grocery delivery logistics.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                    PLATFORM CORE                                       │
│                                                                                        │
│   ┌───────────────────────────┐                     ┌──────────────────────────────┐   │
│   │   Marketplace / Customer  │                     │   Vendor & Workforce Admin   │   │
│   │  - Service Booking        │                     │  - Technician Management     │   │
│   │  - Live Tracking UI       │                     │  - Spatial Dispatch Control  │   │
│   │  - Quotation Approval     │                     │  - Quotation Builder         │   │
│   │  - Payment (Online/COD)   │                     │  - Double-Entry Wallets      │   │
│   └─────────────┬─────────────┘                     └──────────────┬───────────────┘   │
│                 │                                                  │                   │
│                 └─────────────────────────┬────────────────────────┘                   │
│                                           │                                            │
│                                           ▼                                            │
│                   ┌───────────────────────────────────────────────┐                    │
│                   │        Shared PostgreSQL Database Layer       │                    │
│                   │               (Supabase Cloud)                │                    │
│                   └───────────────────────┬───────────────────────┘                    │
│                                           │                                            │
│                                           ▼                                            │
│                   ┌───────────────────────────────────────────────┐                    │
│                   │            Workforce Mobile / PWA             │                    │
│                   │  - First-Person Turn-by-Turn GPS Navigation   │                    │
│                   │  - Real-Time Geofence Arrival (10m accuracy)  │                    │
│                   │  - Job Execution & Pre/Post Photo Proof       │                    │
│                   │  - On-Site Inspection & Quotation Submission  │                    │
│                   │  - Cash Collection (COD) & Wallet Balances    │                    │
│                   └───────────────────────────────────────────────┘                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Components

### 2.1 Multi-Tenant Company & Entity Hierarchy
- **Platform Operator (`is_staff` / Platform Admin):** System-wide authority for verifying vendor credentials, approving master categories, reviewing platform scorecards, and overseeing commission settlements.
- **Service Provider / Vendor Company (`companies.Company`):** Business entity with dedicated tenant scoping. Can operate as a service provider, grocery supplier, or hybrid vendor.
- **Sub-Vendor / Partner Network:** Vendor companies can invite or establish parent-child partnerships with sub-contractors or specialized trade businesses.
- **Employees & Field Technicians (`employees.Employee`):** Field technicians attached to a vendor company. Possess skill sets, catalog service mappings, mandatory compliance documents, real-time presence (online/busy/offline), and dedicated payout wallets.

### 2.2 Shared Model Contract (`ServiceRequest`)
The platform does not duplicate job records between Marketplace and Workforce. The single canonical entity `service_requests.ServiceRequest` serves as the contract:
- **Marketplace owns:** Customer user reference, requested service category, initial description, booking address, schedule slot, and base price.
- **Workforce owns:** Technician assignment, spatial dispatch eligibility, job offers, operational states (`assigned`, `accepted`, `on_the_way`, `in_progress`, `completed`), photo proof of work, on-site inspection sheets, and quotation extensions.

### 2.3 Dispatch & Spatial Matching Engine
- **Spatial Filter (20km Radius):** Haversine spatial ranking identifies eligible technicians within reachable distance of the customer's coordinates.
- **Multi-Tier Dispatch Rings:**
  1. *Ring 1 (Vendor Internal):* Offered first to available technicians within the booking's assigned vendor company.
  2. *Ring 2 (Sub-Vendor / Partner Network):* Offered to trusted partner networks if internal technicians are unavailable.
  3. *Ring 3 (Cross-Vendor Marketplace Fallback):* Distributed across verified platform technicians for high availability.
- **VPS 5-Second Sweep Daemon:** A persistent systemd daemon continuously sweeps for unassigned pending jobs, eliminating manual dispatch delays.
- **Frontend 30s Safety-Net Polling:** Client-side safety-net polls for active offers ensuring immediate technician notification.

### 2.4 Live Location & First-Person Navigation
- **High-Frequency GPS Stream:** Technicians stream location updates with battery and network throttling protection.
- **10-Meter Tight Geofence:** Accurate site arrival detection triggering auto-prompting of customer work start OTP.
- **First-Person Turn-by-Turn Navigation:** In-app SVG compass heading, live velocity, bearing rotation, and speech synthesized voice alerts (`useTechnicianNavigation`).

### 2.5 Quotation & Estimation Architecture
- **On-Site Inspection:** Technicians submit structured inspection sheets (e.g., masonry, painting, AC diagnostics) with photos and measurements.
- **Vendor Quotation Builder:** Vendor admins review inspection data, configure line items (materials, labor, spares), apply taxes, and submit quotations.
- **Customer Decision Flow:** Customer receives push notification / SMS token to review, approve with OTP, or decline quotations.

### 2.6 Immutable Financial Ledger & Wallet
- **Double-Entry Ledger:** Every financial movement (job earning, commission deduction, cash collection, withdrawal) generates balanced debit/credit ledger records.
- **COD Cash Collection:** Technicians collect cash on delivery, immediately debiting technician floating wallet and crediting vendor settlement accounts.
- **Automated Payouts:** Bank account verification via IFSC/account number with admin approval for withdrawal payouts.

---

## 3. High-Level Data Flow

```
1. Customer Booking ───► Supabase PostgreSQL (status = 'confirmed')
                               │
2. VPS Dispatch Daemon ────────┼───► Reads unassigned jobs every 5s
                               │     Calculates 20km spatial candidate ranking
                               ▼
3. Job Offer Issued ───────────┼───► workforce_job_offer (status = 'OFFERED', expires_at = +5 min)
                               │
4. Technician Accepts ─────────┼───► ServiceRequest (status = 'accepted', assigned_employee = emp)
                               │     Technician switches presence to 'BUSY'
                               ▼
5. Navigation & Arrival ───────┼───► Live GPS Stream updates breadcrumb session
                               │     10m Geofence triggers status = 'arrived' + 6-digit OTP
                               ▼
6. Work & Estimation ──────────┼───► Pre-service 3 photos + OTP verification -> status = 'in_progress'
                               │     Optional: Inspection Sheet -> Quotation -> Customer Approval
                               ▼
7. Completion & Settlement ────┼───► Post-service photos + Cash Collection (COD) -> status = 'completed'
                               │     Double-entry wallet credit/debit + Platform commission deducted
                               ▼
8. Customer Review ────────────┴───► 5-Star Rating & Performance Scorecard updated
```
