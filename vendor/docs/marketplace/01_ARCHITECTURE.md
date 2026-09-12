# 01. Multi-Vendor Marketplace Architecture

## System Overview
CalServices Multi-Vendor Grocery Marketplace is an enterprise marketplace extension built within the unified CalServices ecosystem. It bridges platform-owned produce master catalogs with independent grocery vendor storefronts, real-time inventory ledgers, location-based serviceability, single-store cart atomicity, and an immutable financial settlement system.

```
                    CALSERVICES PLATFORM
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
  Customer App           Vendor App            Admin App
 (Store Discovery,      (Store Setup,      (Vendor Approvals,
  Cart & Checkout)     Offers, Orders)      Catalog Governance)
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                  Unified Backend / API Layer
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
PostgreSQL (Shared Supabase)            Storage / Media CDN
```

## Non-Negotiable Core Principles

### Principle 1: Master Catalog is Platform-Owned
- The Master Produce Catalog (67 canonical vegetable items) belongs strictly to CalServices.
- Vendors cannot alter canonical SKUs, botanical/common names, master categories, base units, or canonical imagery.
- Platform administrators retain exclusive CRUD authority over canonical catalog entities.

### Principle 2: Vendor Offers are Vendor-Owned
- Each vendor publishes an independent **Vendor Offer** against a canonical product.
- Vendor offers specify:
  - Custom selling price
  - Maximum Retail Price (MRP) for strike-through discounting
  - Available stock & unit
  - Time-bounded deals (strike-through discounts, flash sales)
- Vendor A has zero access to or influence over Vendor B's offers.

### Principle 3: Strict Tenant & Capability Isolation
- Only companies configured with `business_type = 'grocery_supplier'` or `'hybrid'` can access grocery inventory, storefronts, deals, coupons, orders, and settlements.
- Traditional service providers (HVAC, plumbing, electrical, carpentry) receive immediate HTTP 403 Forbidden with `SUPPLIER_MODULE_RESTRICTED` if attempting to reach grocery endpoints.
- Frontend navigation and route guards dynamically hide and prevent entry into grocery modules for non-grocery vendors.

### Principle 4: Single-Store Cart Invariant
- A customer cart can contain items from only one vendor store at any time.
- Adding an item from another store triggers a `CART_STORE_CONFLICT` (HTTP 409) with explicit prompt to keep or replace.

### Principle 5: Concurrency-Safe Stock Reservations
- Scalar stock decrementing without reservation is prohibited.
- Checkout executes within a database transaction using `select_for_update()` row-locking to verify `available_quantity >= requested_quantity`.
- Inventory is reserved immediately with an auditable transaction ledger entry. Rejected orders or payment failures release reservations atomically.
