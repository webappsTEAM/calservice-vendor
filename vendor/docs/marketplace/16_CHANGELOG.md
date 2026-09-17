# 16. Multi-Vendor Grocery Marketplace Changelog

## Release Version: `v2.4.0-marketplace` (September 2026)

### Added Features & Capabilities

#### 1. Database & Schema Enhancements
- Added `business_type` column to `companies_company` (`service_provider`, `grocery_supplier`, `hybrid`).
- Added `mrp` and `reserved_quantity` columns to `workforce_inventory_item`.
- Created `workforce_vendor_store` table for Amazon-style dedicated vendor storefronts with FSSAI, GPS coordinates, delivery radius, and live open status.
- Created `workforce_vendor_deal` table supporting strike-through pricing, flash sales, and volume discounts.
- Created `workforce_vendor_coupon` table supporting vendor-funded, store-scoped discount coupons with atomic usage limits.
- Created `workforce_inventory_transaction` table for an immutable double-entry stock ledger.
- Created `workforce_coupon_redemption` table tracking customer redemption history.
- Created `workforce_grocery_cart` and `workforce_grocery_cart_item` tables enforcing single-store cart atomicity.
- Created `workforce_grocery_order` and `workforce_grocery_order_item` tables with immutable price snapshots (`mrp_snapshot`, `regular_price_snapshot`, `deal_price_snapshot`, `final_unit_price`).
- Created `workforce_grocery_order_status_history` table tracking actor and state transitions.
- Created `workforce_grocery_delivery` table with 4-digit OTP handover verification.
- Created `workforce_commission_rule` table for configurable platform commission governance.
- Created `workforce_vendor_settlement` and `workforce_financial_ledger_entry` tables for immutable sales and payout tracking.
- Created `workforce_vendor_store_review` table for customer ratings and reviews.
- Migrations applied cleanly to production VPS Supabase PostgreSQL: `0030_vendor_store_and_capability` and `0031_multi_vendor_orders_ledger_and_cart`.

#### 2. Security & Role-Based Access Control
- Implemented `IsGrocerySupplier` permission guard protecting all grocery inventory, store, deal, coupon, order, and settlement endpoints.
- Non-grocery businesses (HVAC, plumbing, electrical, carpentry) strictly receive HTTP 403 Forbidden with `SUPPLIER_MODULE_RESTRICTED`.
- Enforced server-side company context resolution across all vendor endpoints; client-submitted `company_id` is never trusted.

#### 3. Pricing, Deals & Coupon Engine
- Implemented `GroceryPricingService` providing server-authoritative calculation for item prices, active deal validation within start/end dates, store coupon minimum order validation and discount application, delivery fees, and taxes.
- Enforced single-store cart invariant returning HTTP 409 `CART_STORE_CONFLICT` if items from multiple stores are added.
- Implemented atomic server-driven checkout with row-level locking (`select_for_update`) to guarantee stock reservations and prevent negative inventory.

#### 4. Vendor Portal Frontend UI
- Updated `Sidebar.jsx` with dynamic `isGrocerySupplier` capability check, isolating grocery links to verified grocery suppliers only.
- Created `AdminStoreProfilePage.jsx` (`/workforce/admin/store-profile`) with store branding, FSSAI license, delivery radius slider, and open/pause store toggle.
- Created `AdminPromotionsPage.jsx` (`/workforce/admin/promotions`) with Deals & Flash Sales tab and Store Coupons tab with creation modals.
- Created `AdminGroceryOrdersPage.jsx` (`/workforce/admin/grocery-orders`) with status tabs, customer details, produce item snapshots, and order lifecycle actions (Accept, Reject with reason, Mark Picking, Mark Packed, Dispatch, Mark Delivered).
- Created `AdminGrocerySettlementsPage.jsx` (`/workforce/admin/grocery-settlements`) with sales credited metrics, commission rates, and an immutable ledger transactions table.
- Extended `workforceService.js` with all multi-vendor API client methods.
- Registered all routes in `App.jsx` with `AdminRoute` protection.
- Compiled production frontend with Vite and deployed to VPS Nginx web root.

#### 5. Verification & Zero-Regression Guarantee
- Automated verification completed with 100% pass rate:
  - Multi-vendor store setup: PASS
  - Single-store cart conflict: PASS (HTTP 409)
  - Pricing & coupon calculation: PASS (₹38 discount applied)
  - Atomic stock reservation: PASS (5.0kg locked via ledger)
  - Vendor order lifecycle: PASS (transitioned to DELIVERED)
  - Physical stock deduction & financial ledger credit: PASS (₹142.50 credited)
  - Customer review & rating update: PASS (5.0★ avg)
  - HVAC provider isolation: PASS (HTTP 403 Forbidden)
  - Zero regression across all 158 existing service requests and home service categories.
