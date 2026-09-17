# 03. Multi-Vendor Marketplace API Specification

## 1. Public Customer Endpoints

### 1.1 List Nearby Stores
- **Endpoint**: `GET /api/workforce/public/stores/`
- **Query Parameters**:
  - `lat` (optional): Customer latitude
  - `lng` (optional): Customer longitude
- **Response**:
```json
[
  {
    "id": 1,
    "store_name": "Caldim Fresh Produce & Groceries",
    "store_slug": "caldim-fresh-produce",
    "tagline": "Organic Farm Direct Vegetables",
    "logo_url": "https://...",
    "banner_url": "https://...",
    "rating_average": 5.0,
    "total_reviews": 1,
    "delivery_radius_km": 15.0,
    "estimated_delivery_mins": 25,
    "minimum_order_amount": "0.00",
    "is_accepting_orders": true
  }
]
```

### 1.2 Storefront Page
- **Endpoint**: `GET /api/workforce/public/stores/{slug}/`
- **Response**: Full store profile, categorized produce items with strike-through deals, and available store coupons.

### 1.3 Cart Management (Single-Store Enforcement)
- **Endpoint**: `GET /api/workforce/public/cart/?customer_id={id}&coupon_code={code}`
- **Endpoint**: `POST /api/workforce/public/cart/`
  - **Payload**:
  ```json
  {
    "customer_id": "cust_123",
    "inventory_item_id": 1,
    "quantity": 2.5,
    "force_replace": false
  }
  ```
  - **Conflict Response** (HTTP 409):
  ```json
  {
    "error": {
      "code": "CART_STORE_CONFLICT",
      "message": "Your cart contains items from 'Caldim Fresh Produce'. Would you like to clear it and add items from 'Kovai Fresh Agro'?",
      "current_store_id": 1,
      "new_store_id": 2
    }
  }
  ```

### 1.4 Server-Driven Checkout
- **Endpoint**: `POST /api/workforce/public/checkout/`
- **Payload**:
```json
{
  "customer_id": "cust_123",
  "customer_name": "Rajesh Kumar",
  "customer_phone": "9876543210",
  "delivery_address": "12 Gandhi Nagar, Coimbatore",
  "coupon_code": "FRESH20",
  "payment_method": "COD"
}
```
- **Response** (HTTP 201): Order created, stock atomically reserved, delivery OTP generated.

---

## 2. Vendor Management Endpoints (`IsGrocerySupplier` Protected)

### 2.1 Inventory Management
- `GET /api/workforce/inventory/` — List vendor offers
- `POST /api/workforce/inventory/` — Add offer from Master Catalog
- `PATCH /api/workforce/inventory/{id}/` — Update price, MRP, stock, threshold
- `GET /api/workforce/inventory/ledger/` — Stock transaction audit trail

### 2.2 Store & Promotions
- `GET /api/workforce/store/profile/` — Fetch store settings
- `PUT /api/workforce/store/profile/` — Update branding, radius, ETA, open toggle
- `GET /api/workforce/promotions/deals/` — Active deals
- `POST /api/workforce/promotions/deals/` — Create strike-through deal
- `GET /api/workforce/promotions/coupons/` — Store coupons

### 2.3 Store Order Management
- `GET /api/workforce/orders/grocery/` — Orders list by status
- `POST /api/workforce/orders/grocery/{id}/accept/` — Accept order
- `POST /api/workforce/orders/grocery/{id}/reject/` — Reject order (auto-releases reserved stock)
- `POST /api/workforce/orders/grocery/{id}/status/` — Transition status (`PICKING`, `PACKED`, `OUT_FOR_DELIVERY`, `DELIVERED`)
- `GET /api/workforce/settlements/` — Financial settlements & ledger
