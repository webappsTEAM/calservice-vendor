# CalServices / Sevo Vendor & Workforce Platform Documentation

Welcome to the comprehensive technical documentation for the **Sevo / CalServices Vendor & Workforce Platform**. This repository powers the service provider operations, sub-vendor hierarchies, technician dispatch, live GPS tracking, quotations & estimations, double-entry financial settlements, and multi-vendor grocery stock fulfillment.

---

## 🏛️ System Architecture Overview

The platform operates as a unified multi-tenant engine integrated with the CalServices Customer Marketplace and Supabase PostgreSQL database.

```
                               ┌─────────────────────────────────────────┐
                               │       CalServices Customer App          │
                               │   (Booking / Grocery Cart / Tracking)   │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    SHARED POSTGRESQL (SUPABASE)                                │
│  - Companies (Service / Grocery / Hybrid)         - ServiceRequests (Canonical Job Records)    │
│  - Employees & Technicians                        - Inventory Items & Stock Movements          │
│  - Wallets & Financial Ledgers                    - Multi-Leg Trips, Stops & Proof of Work     │
└───────────────────▲────────────────────────────────────────────────────────▲───────────────────┘
                    │                                                        │
                    ▼                                                        ▼
┌─────────────────────────────────────────┐        ┌─────────────────────────────────────────────┐
│          Workforce Backend              │        │              Workforce Frontend             │
│   (Django REST Framework + Workers)     │◄──────►│             (React 18 + Vite)               │
│ - Spatial Dispatch Engine (20km / 10m)  │        │ - Vendor Admin & Dispatch Portal            │
│ - Live Breadcrumb GPS & Geofencing      │        │ - Mobile PWA Technician First-Person Nav    │
│ - Double-Entry Ledger & Wallets         │        │ - Customer Live Tracking (Map & ETA)        │
│ - Quotation & Estimation Builder        │        │ - Inventory & Stock Management Suite        │
└─────────────────────────────────────────┘        └─────────────────────────────────────────────┘
```

---

## 📚 Documentation Directory Map

The documentation is organized into two primary operational tracks: **Workforce Management Engine** and **Multi-Vendor Grocery Marketplace**.

### 1. 👷 Workforce Management Documentation (`vendor/docs/workforce/`)

| Document | Title | Description |
| :--- | :--- | :--- |
| [`01_WORKFORCE_ARCHITECTURE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/01_WORKFORCE_ARCHITECTURE.md) | **System Architecture & Core Design** | High-level architecture, tenant scoping, service provider vs sub-vendor hierarchies, and integration boundaries. |
| [`02_DATABASE_SCHEMA_MODELS.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/02_DATABASE_SCHEMA_MODELS.md) | **Relational Schema & Database Models** | Physical database tables, foreign keys, unmanaged mirror models, indexes, and constraints. |
| [`03_API_SPECIFICATION.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/03_API_SPECIFICATION.md) | **REST API Reference** | Complete endpoint catalogue covering Auth, Technicians, Dispatch, GPS Tracking, Estimations, Wallets, and Proof of Work. |
| [`04_STATE_MACHINES_AND_LIFECYCLES.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/04_STATE_MACHINES_AND_LIFECYCLES.md) | **State Machines & Transitions** | Explicit state machines for Service Requests, Job Offers, Estimations, Invoices, Presence, and Wallet Ledgers. |
| [`05_DISPATCH_AND_MATCHING_ENGINE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/05_DISPATCH_AND_MATCHING_ENGINE.md) | **Spatial Dispatch & Auto-Sweep** | 20km spatial candidate ranking, 10m tight geofence, multi-tier dispatch rings, VPS 5s sweep daemon, and concurrency locking. |
| [`06_LIVE_TRACKING_AND_NAVIGATION.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/06_LIVE_TRACKING_AND_NAVIGATION.md) | **Live Tracking & Mobile Navigation** | Real-time GPS stream, breadcrumb session logging, turn-by-turn first-person navigation, and battery optimization. |
| [`07_ESTIMATIONS_AND_QUOTATIONS.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/07_ESTIMATIONS_AND_QUOTATIONS.md) | **Estimations & Quotation Engine** | On-site technician inspection sheets, multi-item quotation builder, customer decision flow, and extension approval tokens. |
| [`08_WALLET_AND_FINANCIAL_SETTLEMENT.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/08_WALLET_AND_FINANCIAL_SETTLEMENT.md) | **Wallets, Ledger & Cash Collections** | Double-entry accounting, COD cash collection workflows, platform commissions, bank accounts, and withdrawal payouts. |
| [`09_STOCK_AND_INVENTORY_MANAGEMENT.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/09_STOCK_AND_INVENTORY_MANAGEMENT.md) | **Stock & Inventory System** | Mirror inventory models, gram-level precision, restock movements, daily resets, and unit conversions. |
| [`10_SECURITY_AND_TENANT_ISOLATION.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/10_SECURITY_AND_TENANT_ISOLATION.md) | **Security & Tenant Isolation** | Server-side company resolution, JWT authentication, anti-tampering guards, and permission matrices. |
| [`11_TESTING_AND_VERIFICATION_RUNBOOK.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/11_TESTING_AND_VERIFICATION_RUNBOOK.md) | **Testing & Verification Suite** | Comprehensive automated test suites, concurrency verifications, spatial accuracy tests, and latency profiling. |
| [`12_DEPLOYMENT_AND_OPERATIONS_GUIDE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/12_DEPLOYMENT_AND_OPERATIONS_GUIDE.md) | **VPS Deployment & Runbook** | Ubuntu VPS deployment, Gunicorn/Uvicorn configuration, Systemd dispatch daemon services, and Nginx reverse proxy. |
| [`CUSTOMER_WORKFORCE_INTEGRATION.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/CUSTOMER_WORKFORCE_INTEGRATION.md) | **Customer ↔ Workforce Integration** | Detailed contract for Customer App developers, covering OTP verification, live tracking endpoints, and extension approvals. |
| [`MARKETPLACE_INTEGRATION_CONTRACT.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/MARKETPLACE_INTEGRATION_CONTRACT.md) | **Shared Model & Ownership Contract** | Strict boundaries on `ServiceRequest` field ownership between Marketplace and Workforce platforms. |
| [`PRODUCTION_READINESS_REPORT.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/workforce/PRODUCTION_READINESS_REPORT.md) | **Production Verification Audit** | Audit checklist confirming zero fake data, tenant safety, concurrency safety, and live hardware readiness. |

---

### 2. 🛒 Multi-Vendor Grocery Marketplace Documentation (`vendor/docs/marketplace/`)

| Document | Title | Description |
| :--- | :--- | :--- |
| [`01_ARCHITECTURE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/01_ARCHITECTURE.md) | **Marketplace Architecture** | Canonical master catalogue, vendor offers, capability isolation (`grocery_supplier`), single-store cart invariant. |
| [`02_DATABASE_SCHEMA.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/02_DATABASE_SCHEMA.md) | **Database Schema Specification** | Relational physical tables for storefronts, deals, coupons, grocery orders, delivery OTPs, and settlement ledgers. |
| [`03_API_SPECIFICATION.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/03_API_SPECIFICATION.md) | **Marketplace API Specification** | REST endpoints for store setup, offers, deals, coupons, cart checkout, order management, and settlements. |
| [`04_PERMISSION_MATRIX.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/04_PERMISSION_MATRIX.md) | **Permission & Capability Matrix** | Strict RBAC rules isolating grocery modules from general service providers. |
| [`05_ORDER_STATE_MACHINE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/05_ORDER_STATE_MACHINE.md) | **Order State Machine** | Order lifecycle from `PENDING` → `CONFIRMED` → `PACKED` → `OUT_FOR_DELIVERY` → `DELIVERED`. |
| [`06_INVENTORY_STATE_MACHINE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/06_INVENTORY_STATE_MACHINE.md) | **Inventory & Stock Ledger** | Atomic stock reservation, decrement on dispatch, and restock on cancellation. |
| [`07_PAYMENT_FLOW.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/07_PAYMENT_FLOW.md) | **Payment & Commission Flow** | Gateway integration, cash on delivery verification, platform fee deduction, and net vendor payout calculation. |
| [`08_FULFILLMENT_FLOW.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/08_FULFILLMENT_FLOW.md) | **Fulfillment & Delivery Flow** | In-store picking, packing, dispatch, and 4-digit OTP handover verification. |
| [`09_SETTLEMENT_MODEL.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/09_SETTLEMENT_MODEL.md) | **Vendor Settlement Model** | Double-entry balance calculation, holding periods, payout schedules, and tax withholding. |
| [`10_SECURITY_MODEL.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/10_SECURITY_MODEL.md) | **Security & Fraud Protection** | Rate limiting, cart tampering protection, coupon misuse mitigation, and audit logging. |
| [`11_TEST_PLAN.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/11_TEST_PLAN.md) | **Quality Assurance & Test Plan** | End-to-end integration test scenarios and edge-case validations. |
| [`12_DEPLOYMENT_GUIDE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/12_DEPLOYMENT_GUIDE.md) | **Marketplace Deployment Guide** | Environment configuration, database migration execution, and static build deployment. |
| [`13_ROLLBACK_PLAN.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/13_ROLLBACK_PLAN.md) | **Disaster Recovery & Rollback** | Step-by-step procedures for zero-downtime rollback and schema recovery. |
| [`14_ADMIN_GUIDE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/14_ADMIN_GUIDE.md) | **Platform Operator Admin Guide** | Master catalogue management, vendor approvals, commission rule configuration, and dispute resolution. |
| [`15_VENDOR_GUIDE.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/15_VENDOR_GUIDE.md) | **Store Manager Vendor Guide** | Storefront setup, publishing offers, flash deals, coupons, and processing grocery orders. |
| [`16_CHANGELOG.md`](file:///c:/Users/USER/Desktop/caldim%20projects/sevo/sevo-vendor/vendor/docs/marketplace/16_CHANGELOG.md) | **Release Notes & Changelog** | Detailed release notes for multi-vendor features and platform enhancements. |

---

## ⚡ Quick Start for Developers

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL connection (Supabase or Local)

### 1. Backend Setup
```bash
cd vendor/backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```

### 2. Frontend Setup
```bash
cd vendor/frontend
npm install
npm run dev
```

### 3. Automated Verification Suites
Run any of the end-to-end verification suites to ensure zero regressions:
```bash
cd vendor/backend
python run_final_e2e_concurrency_and_regression.py
python run_master_customer_marketplace_handover_verification.py
```
