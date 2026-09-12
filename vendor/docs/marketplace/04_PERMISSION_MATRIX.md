# 04. Role & Capability Permission Matrix

## Overview
Marketplace capabilities are strictly decoupled using capability flags (`Company.business_type`) and role-based permissions (`IsGrocerySupplier`, `VendorOwner`, `StoreManager`, `OrderManager`, `FinanceManager`).

| Role / Capability | Master Catalog (Read) | Master Catalog (Write) | Vendor Storefront | Stock & Deals | Order Fulfillment | Financial Ledger |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Platform Superadmin** | Full | Full | View / Suspend | View All | Audit All | Manage / Audit |
| **Grocery Supplier (Owner)** | Browse | Denied | Configure | Full | Full | Full View |
| **Grocery Store Manager** | Browse | Denied | Configure | Update Stock | Accept/Pack | Denied |
| **Grocery Order Dispatcher** | Browse | Denied | View Only | View Only | Update Status | Denied |
| **Service Provider (HVAC/Plumber)** | Denied (403) | Denied (403) | Denied (403) | Denied (403) | Denied (403) | Denied (403) |
| **Customer (Public)** | Public View | Denied | Public View | Read Deals | Track Own | View Receipt |

## Backend Guard Implementation

```python
class IsGrocerySupplier(permissions.BasePermission):
    message = "This module is restricted to verified Grocery Suppliers."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False) or getattr(user, "role", "") == "SUPERADMIN":
            return True
        emp = getattr(user, "employee_profile", None)
        company = getattr(user, "company", None) or (emp.company if emp else None)
        if not company:
            return False
        return getattr(company, "business_type", "service_provider") in ["grocery_supplier", "hybrid"]
```

## Security Invariants
1. **Server-Side Ownership Lookup**: Every vendor query resolves `company_id` from the JWT session (`request.user.company`). Any client-supplied `?company_id=...` parameter is strictly ignored.
2. **403 Rejection**: Non-grocery providers calling `/api/workforce/inventory/*`, `/api/workforce/orders/grocery/*`, or `/api/workforce/store/*` receive HTTP 403 Forbidden with `SUPPLIER_MODULE_RESTRICTED`.
3. **Frontend Guarding**: The vendor portal sidebar evaluates `isGrocerySupplier` and suppresses all produce links for non-grocery businesses.
