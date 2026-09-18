# 10. Security Model & Tenant Isolation

## 1. Non-Negotiable Tenant Scoping Principles

Tenant isolation is strictly enforced at the backend query level. The frontend is treated as completely untrusted.

```
┌─────────────────────────────────────────────────────────────┐
│                      REQUEST INGESTION                      │
│                                                             │
│   HTTP Request Headers: Authorization: Bearer <JWT>         │
│   Request Body: { ... }                                     │
│                                                             │
│                             │                               │
│                             ▼                               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │            Backend Security Context Layer           │   │
│   │                                                     │   │
│   │ 1. Validate JWT Signature & Expiry                  │   │
│   │ 2. Resolve Authenticated User                       │   │
│   │ 3. Resolve User's Company / Tenant Link             │   │
│   │ 4. DISCARD any client-supplied `company_id`         │   │
│   │    or `employee_id` in request body                 │   │
│   └─────────────────────────┬───────────────────────────┘   │
│                             │                               │
│                             ▼                               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                Tenant-Scoped Query                  │   │
│   │                                                     │   │
│   │ Example:                                            │   │
│   │ ServiceRequest.objects.filter(                      │   │
│   │     company_id=request.user.employee.company_id     │   │
│   │ )                                                   │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Capability & Permission Guards

The backend employs specialized DRF permission classes:

| Permission Class | Allowed User Types | Protected Resources |
| :--- | :--- | :--- |
| `IsCompanyAdmin` | Vendor Company Admins & Staff | Company profile, technician roster, company wallet, invoices, quotation builder. |
| `IsTechnician` | Active, Approved Field Technicians | Job offers, assigned jobs, live location stream, shift clock-in/out, inspection sheets. |
| `IsGrocerySupplier` | Companies with `business_type IN ('grocery_supplier', 'hybrid')` | Grocery inventory, store profile, flash deals, store coupons, grocery orders. |
| `IsPlatformAdmin` | Superusers & Platform Staff | Vendor verification, KYC document approvals, platform scorecards, treasury payouts. |

---

## 3. Cryptographic Token & OTP Security

- **Work Start OTP:** 6-digit cryptographically random numeric string generated upon geofence arrival. Stored with a 15-minute TTL and single-use invalidation.
- **Quotation Decision Tokens (`decision_token`):** 32-byte URL-safe cryptographic hash (`secrets.token_urlsafe(32)`) enabling secure one-click review without exposing internal entity primary keys.
- **JWT Key Strength:** Configured with minimum 256-bit secret entropy (`HS256` / `RS256`) preventing brute-force token tampering.
