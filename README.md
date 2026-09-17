# SEVO Vendor & Workforce Management Platform (CalService)

An enterprise-grade, multi-tenant workforce and vendor operations platform connecting service providers, field technicians, customers, and platform administrators. Built with a unified Django REST backend, React web portal, and Flutter mobile application powered by Supabase PostgreSQL.

---

## 🏗️ High-Level Architecture

```
                 ┌────────────────────────────────┐
                 │       Customer Web / App       │
                 └──────────────┬─────────────────┘
                                │
                                ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                 Shared Supabase PostgreSQL                  │
  │  (Multi-tenant Relational DB, RLS, Operational Contracts)    │
  └─────────────────────────────┬───────────────────────────────┘
                                ▲
                                │
       ┌────────────────────────┴────────────────────────┐
       │                                                 │
       ▼                                                 ▼
┌──────────────┐                                 ┌──────────────┐
│  Workforce   │                                 │  Workforce   │
│   Backend    │                                 │   Mobile /   │
│ (Django REST)│                                 │ Web Frontend │
└──────────────┘                                 └──────────────┘
```

The system operates across three core tiers:
1. **Workforce Backend (`backend/` & `vendor/backend/`)**: Django REST Framework API engine handling multi-tenant isolation, spatial dispatch, state machines, rates, estimations, wallet reconciliation, and live tracking.
2. **Vendor & Admin Web Portal (`frontend/` & `vendor/frontend/`)**: React + Vite single-page application for dispatch coordination, company network management, rate cards, and financial audit.
3. **Technician & Vendor Mobile App (`mobile/`)**: Flutter application providing field technicians and vendors with job offer feeds, turn-by-turn navigation, pre-service inspection checklists, OTP completion, and instant earnings.

---

## 🚀 Key Modules & Capabilities

### 1. Spatial Dispatch & Candidate Ranking
* **20km Spatial Matching**: Distance-calculated ranking considering technician GPS location, rating, availability, and active job count.
* **Tiered Expiration & Expansion**: Offers transition cleanly across time windows with automatic ring expansion if unclaimed.
* **Busy State & Concurrency Protection**: Atomic database transactions and row-level locks prevent double-assignment and protect technicians during active execution.

### 2. Estimation & Quotation Engine
* **Dynamic Rate Cards**: Base diagnostic pricing, category line-items, and unit rate lookups directly configured from database models.
* **Real-Time Live Pricing**: Instant price calculation as line items are entered during on-site inspections.
* **Customer Approvals & Revisions**: Transparent customer approval workflows before extra work or parts replacement begins.
* **Invoicing & PDF Generation**: Automated invoice generation, breakdown of platform fees vs. technician payout, and instant settlement.

### 3. Technician Lifecycle & Verification
* **Multi-Step Onboarding**: KYC identity proofs, background verification, trade certificates, and service categorizations.
* **Admin Verification Workflow**: Document review, verification state transitions (`PENDING_REVIEW` → `VALID` / `REJECTED`), and automated eligibility gates.
* **Presence & Attendance**: Geofenced auto clock-in/out, live battery/network status reporting, and fine-grained availability toggle (`Online`, `Busy`, `Offline`, `On Leave`).

### 4. Vendor Wallet & Financial Settlement
* **Double-Entry Ledger**: Accurate tracking of credits, debits, advance payouts, and completed job settlements.
* **Cash-on-Delivery (COD) Reconciliation**: Handshake flows for cash collection with platform commission deductions.
* **Razorpay Payment Gateway**: Seamless in-app payments for customer quotes, wallet top-ups, and payout withdrawals.

---

## 📂 Project Directory Structure

```plaintext
calservice-vendor/
├── backend/                       # Primary Django REST API backend
│   ├── accounts/                  # User auth, roles, JWT & tenant permissions
│   ├── companies/                 # Vendor companies & organizational hierarchy
│   ├── employees/                 # Technician profiles, skills, documents & approvals
│   ├── service_requests/          # Dispatch pipeline, state machines & estimations
│   ├── time_tracking/             # Geofence attendance, live GPS & location logs
│   ├── vendor_wallet/             # Wallet ledgers, payout & payment reconciliation
│   ├── workforce_api/             # Core URL routing & API versioning
│   ├── workforce_core/            # Settings, database configuration & WSGI/ASGI
│   └── manage.py                  # Django management CLI
├── frontend/                      # React + Vite Vendor & Admin Web Dashboard
│   ├── src/
│   │   ├── components/            # Reusable UI components & layouts
│   │   ├── pages/                 # Estimation, Invoicing, Dispatch & Network pages
│   │   ├── services/              # Axios API clients & WebSocket listeners
│   │   └── utils/                 # Data formatters, geocoders & route guards
│   ├── package.json
│   └── vite.config.js
├── mobile/                        # Flutter Technician & Vendor Mobile App
│   ├── lib/
│   │   ├── core/                  # Theme, network client, storage & constants
│   │   ├── features/              # Modular features (auth, jobs, location, wallet, etc.)
│   │   └── shared/                # Shared reusable Flutter widgets
│   └── pubspec.yaml
├── docs/                          # Comprehensive technical documentation & contracts
│   ├── workforce/                 # Integration contracts & readiness reports
│   └── PLAY_STORE_LISTING.md      # Play Store metadata & store guidelines
└── AGENTS.md                      # Mandatory engineering rules & architectural invariants
```

---

## ⚙️ Environment Setup & Installation

### 1. Backend (Django)
```bash
# Navigate to backend
cd backend

# Create & activate virtual environment
python -m venv venv
venv\Scripts\activate      # Windows (PowerShell: .\venv\Scripts\Activate.ps1)

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Apply database migrations
python manage.py migrate

# Start development server
python manage.py runserver 8000
```

### 2. Frontend (React / Vite)
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Mobile App (Flutter)
```bash
# Navigate to mobile
cd mobile

# Get Flutter dependencies
flutter pub get

# Run on connected device / emulator
flutter run
```

---

## 🧪 Testing & Quality Assurance

Run the comprehensive test suites to ensure compliance with database consistency and tenant isolation:

```bash
# Backend E2E & regression suite
cd backend
python run_stabilization_suite.py
python run_final_e2e_concurrency_and_regression.py

# Estimation & quotation validation
python test_estimation_and_quotation_suite.py

# Spatial dispatch & 20km radius verification
python test_admin_20km_spatial_dispatch.py
```

---

## 📜 Architectural Invariants & Rules

Refer to [`AGENTS.md`](file:///c:/Users/USER/Desktop/caldim%20projects/calservice-vendor/AGENTS.md) for strict architectural rules:
1. **Never hardcode database entities**: All service catalogs, rates, and locations must resolve from relational DB models.
2. **Tenant Isolation**: Every operational query must be tenant-scoped and server-authorized.
3. **No Mock / Fake Data**: Empty database states must render clean empty UI states.
4. **Relational Integrity**: Row locking and atomic transactions must protect dispatch and payment state changes.
