# 14. Marketplace Administrator Guide

## Platform Administrator Responsibilities

Platform administrators govern the marketplace, verify supplier onboarding, maintain the Master Catalog, configure commission policies, and arbitrate customer disputes.

## 1. Master Catalog Management
- **URL**: `/workforce/admin/catalog`
- Admins can create new canonical produce items, configure master images, canonical SKUs, and default pack sizes.
- **Rule**: Vendors can never modify master catalog entries; vendors only create offers against them.

## 2. Grocery Supplier Onboarding & Approvals
- **URL**: `/workforce/admin/applications`
- Inspect business documentation, FSSAI registration certificate, store address, and bank details.
- Approve or reject supplier applications. Approving an application sets `Company.business_type = 'grocery_supplier'`, automatically provisioning their `VendorStore` record.

## 3. Store Governance & Emergency Controls
- **Pause Store**: If a supplier has quality or fulfillment issues, the admin can toggle `is_accepting_orders = false` or suspend the store.
- **Dispute & Refund Arbitration**: Admins can issue full or partial refunds for perishable produce complaints (`DAMAGED`, `ROTTEN`, `WRONG_ITEM`) directly from the order monitor.

## 4. Commission Rules
- Default commission is 5.0% on gross item sales.
- Custom commission rules can be configured per vendor or category under `CommissionRule`.
