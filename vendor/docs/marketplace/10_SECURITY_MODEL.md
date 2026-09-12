# 10. Security & Hardening Model

## Security Architecture Highlights

### 1. Multi-Tenant Isolation
- **Rule 5 Compliance**: Tenant company ID is never trusted from frontend payloads. The backend strictly resolves:
  ```python
  company_id = emp.company_id if (emp and emp.company_id) else getattr(request.user, 'company_id', None)
  ```
- Any cross-tenant data query or mutation attempt results in HTTP 403 Forbidden.

### 2. Grocery Supplier Capability Isolation
- Traditional service providers (HVAC, plumbing, electrical, carpentry) have `business_type = 'service_provider'`.
- All grocery inventory, promotions, store, order, and settlement views enforce `IsGrocerySupplier`.
- Non-grocery businesses receive HTTP 403 with error code `SUPPLIER_MODULE_RESTRICTED`.

### 3. Server-Authoritative Pricing & Snapshots
- Prices, deal discounts, coupons, and delivery fees are computed server-side in `GroceryPricingService`.
- Client-submitted totals or unit prices are discarded.
- Completed orders store frozen snapshots of all line items (`mrp_snapshot`, `regular_price_snapshot`, `deal_price_snapshot`, `final_unit_price`).

### 4. Concurrency & Race Condition Protection
- Row-locking via PostgreSQL `select_for_update()` during checkout reservations prevents race conditions or negative inventory.
- Coupon usage limits are updated atomically with unique constraint on `[company, code]`.

### 5. Media Upload Security
- Store logos and banners enforce MIME type verification (`image/jpeg`, `image/png`, `image/webp`), 5MB size limits, and sanitization of filenames using random UUIDs.

### 6. Secrets & Environment Security
- Zero hardcoded API keys or database credentials in source code. All secrets are loaded from environment variables.
