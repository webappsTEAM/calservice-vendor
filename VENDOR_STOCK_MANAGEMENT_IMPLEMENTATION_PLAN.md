# Vendor Stock Management — Implementation Plan

## Why this exists

Today, all vegetable/package stock (restock, mark out of stock, price changes) is managed
through the **Customer app's Super Admin Edit Mode** (`Customer/backend/inventory/views.py`
— `VegetableStockListView`, `VegetableStockRestockView`, `VegetableStockAdjustView`,
`VegetableStockSetDefaultView`, `VegetableDetailsUpdateView`, plus the
`InventoryItemViewSet` CRUD). Vendors (service providers who join the platform) currently
have no stock UI of their own in `vendor/frontend`.

Confirmed decision (user, 2026-09-16): once vendors manage their own stock in the Vendor
app, Super Admin Edit Mode in the Customer app **loses write access to stock/price
entirely** — not just hidden in the UI, the backend endpoints stop accepting writes too.
Vendors become the single source of truth for their own company's stock. This avoids two
independent UIs racing to mutate the same `InventoryItem` rows.

## Architecture: why this is a shared-DB mirror, not a cross-service API call

`Customer/backend` and `vendor/backend` are two separate Django projects that already
share one Postgres database in production (`DB_NAME`/`DB_HOST`/`DB_PORT` env vars match
between `Customer/backend/*/settings.py` and `vendor/backend/workforce_core/settings.py`).
The codebase's existing convention for this — used throughout `vendor/backend/companies`
and `vendor/backend/service_requests` — is **unmanaged Django models** (`Meta.managed =
False`, `db_table = "<the real table name>"`) that point at tables owned and migrated by
`Customer/backend`. For example, `vendor/backend/companies/models.py` already has an
unmanaged `Company` model reading `companies_company`, and
`vendor/backend/service_requests/models.py` already mirrors `service_requests_service`,
`service_requests_catalogcategory`, etc.

Stock management follows the same pattern: add unmanaged mirrors in `vendor/backend` for
the tables that `Customer/backend/inventory` owns (`InventoryItem`, `StockMovement`) plus
the one table `vendor/backend/service_requests` doesn't yet mirror (`Package`, which is
what actually carries price/offer_price/stock_item). No new inter-service HTTP calls, no
new sync job, no dual-write risk — both backends read/write the exact same rows, and
`Customer/backend` keeps owning the migrations (mirrors never run migrations against these
tables).

Company scoping is already solved: `vendor/backend/companies/middleware.py` resolves
`request.company` from the JWT/cookie on every request, exactly the pattern
`Customer/backend/inventory/views.py`'s `_get_request_company(request)` reaches for. So a
vendor's stock endpoints scope every query to `request.company` with no new plumbing.

## Phase 1 — Backend: mirror the models into `vendor/backend`

1. Add `Package` (unmanaged, `db_table = "service_requests_package"`) to
   `vendor/backend/service_requests/models.py`, mirroring the fields
   `Customer/backend/service_requests/models.py`'s `Package` actually needs for stock
   management: `id, service (FK to the existing mirrored Service), name, slug, base_price,
   offer_price, duration, tag, sort_order, image, stock_item (FK to the new InventoryItem
   mirror), status`. Skip fields irrelevant to stock (reviews, faqs, includes/excludes,
   etc.) — an unmanaged model only needs the columns it actually reads/writes.
2. Add a new `vendor/backend/inventory/` app with unmanaged mirrors of `InventoryItem`
   (`db_table = "inventory_inventoryitem"`) and `StockMovement`
   (`db_table = "inventory_stockmovement"`), matching
   `Customer/backend/inventory/models.py` field-for-field. Register `"inventory"` in
   `vendor/backend/workforce_core/settings.py`'s `INSTALLED_APPS`.
3. Port the business logic vendors need from
   `Customer/backend/inventory/services/vegetable_stock_service.py` and
   `inventory/selectors/vegetable_stock_selectors.py` — these are pure functions over the
   models, so they can be copied into `vendor/backend/inventory/services.py` /
   `selectors.py` with imports adjusted to the local mirrors. (Not imported cross-project;
   the two Django projects don't share a Python path.)
4. New views in `vendor/backend/inventory/views.py`, permission-gated with the existing
   `is_vendor_admin(user)` check from `vendor/backend/accounts/permissions.py` (already
   used elsewhere in this backend for "this vendor's own admin/manager" — not
   `is_platform_admin`, since this must stay scoped to the vendor's own company):
   - `GET /api/vendor/stock/` — list this vendor's packages with live stock state (mirrors
     `VegetableStockListView`, filtered to `service__slug="vegetables"` initially since
     that's the only category with stock tracking today; structured so other stock-tracked
     categories can be added later without a rewrite).
   - `POST /api/vendor/stock/<package_id>/restock/`
   - `POST /api/vendor/stock/<package_id>/mark-out-of-stock/` (a thin wrapper around
     `adjust_stock(quantity=0, reason="Marked out of stock by vendor")` — vendors asked
     for this as an explicit one-tap action, not just "adjust to some number")
   - `PATCH /api/vendor/stock/<package_id>/update-details/` — price, offer_price, reorder
     level, restock level (mirrors `VegetableDetailsUpdateView`)
   - `GET /api/vendor/stock/<package_id>/history/` — restock/adjustment audit trail
   - Every one of these must filter/verify `product.service.org_id == request.company_id`
     (or equivalent ownership check once Package's company scoping is confirmed — see
     Phase 1.5 below) before allowing a write. **This is the one new correctness
     requirement that didn't exist before**: today's admin endpoints trust that only
     platform staff calls them, so they never checked "does this admin own this product."
     A vendor-facing endpoint must.
5. Register the new routes in `vendor/backend/workforce_core/urls.py` under
   `path("api/vendor/", include("inventory.vendor_urls"))`.

### Phase 1.5 — Resolve product ownership (blocking question, needs your input before Phase 1 step 4 can be finished correctly)

`Package` today has no direct company/vendor FK — stock ownership currently flows through
`InventoryItem.org` (the `Company` that owns the `InventoryItem` a `Package.stock_item`
points to). Two real-world models are possible and they lead to different permission
checks:
- **One vendor per product** (simplest): each `Package.stock_item.org` is exactly one
  vendor's company, and that vendor is the only one who can ever restock/reprice it. This
  matches the current data shape with zero schema changes.
- **Multiple vendors selling the same catalog product** (marketplace-style): several
  vendors each hold their own stock count against the same customer-facing `Package`. This
  needs a new per-vendor stock table (`VendorPackageStock: package, company, quantity,
  price_override, ...`) instead of writing directly to `Package`/`InventoryItem`, since
  those are currently 1:1 with a single company.

I'll assume the first model (matches what's built today) unless you tell me otherwise —
worth confirming before Phase 1 lands, since it changes the schema.

## Phase 2 — Backend: lock down Customer app's Super Admin Edit Mode

Per your confirmed decision, once Phase 1 is live and tested:
1. In `Customer/backend/inventory/views.py`, change `VegetableStockRestockView`,
   `VegetableStockAdjustView`, `VegetableStockSetDefaultView`,
   `VegetableDetailsUpdateView`, and `InventoryItemViewSet`'s `create`/`update`/`destroy`
   to return `403` ("Stock is now managed from the Vendor app.") instead of executing —
   keep the classes (don't delete the file) so `VegetableStockListView` and
   `VegetableStockHistoryView` can stay **read-only** for admin visibility/support, which
   costs nothing extra since GETs were never the risk.
2. Add a backend test asserting the write endpoints now 403, so this can't silently
   regress back open.

## Phase 3 — Frontend: Vendor app stock management UI

New page `vendor/frontend/src/pages/admin/AdminStockManagementPage.jsx` (same folder as
`AdminPricingPolicyPage.jsx`, `AdminOperationsPage.jsx` — this is vendor-company-admin
territory, not platform-admin), wired into the existing admin router/sidebar:
- A table of the vendor's products (mirrors the existing Customer-app Super Admin Edit
  Mode table: name, image, current stock, status, price, MRP) sourced from
  `GET /api/vendor/stock/`.
- Restock action (quantity + unit) → `POST .../restock/`.
- "Mark out of stock" one-tap action → `POST .../mark-out-of-stock/`.
- Price/offer-price/reorder-level editing inline or in a modal →
  `PATCH .../update-details/`.
- Per-product restock history view → `GET .../history/`.
- New `vendor/frontend/src/api/stockService.js` following the existing
  `vendorEstimationService.js` / `walletService.js` pattern (thin wrappers over the shared
  `api/client.js`).

## Phase 4 — Frontend: Customer app cleanup

Once Phase 2/3 are live: remove the write controls (restock/adjust/set-default/price-edit
buttons and forms) from the Customer app's Super Admin Edit Mode UI, leaving only the
read-only stock view. Don't delete the read view — it's still useful for admin
support/visibility, and Phase 2 already made the backend refuse writes regardless, so this
is UI cleanup rather than a safety-critical change.

## Sequencing note

This is independent of, and doesn't block, the Daily Essentials frontend work
(`DAILY_ESSENTIALS_FRONTEND_IMPLEMENTATION_PLAN.md`) already implemented in Phases 1-4
there. Recommend starting this after your end-to-end test of that work, since Phase 2 here
(locking down Customer app writes) is a live behavior change worth doing only once you're
confident the Daily Essentials checkout flow itself is solid — restock/price-edit bugs
during that testing window are easier to fix if Super Admin Edit Mode can still write.
