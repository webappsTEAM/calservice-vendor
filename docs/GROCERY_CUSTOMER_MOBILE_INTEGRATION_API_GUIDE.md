# Sevo Grocery Hub — Customer Mobile App API & Integration Guide

This document is the verified integration blueprint for Flutter developers implementing the **Grocery Shopping Experience** in the Customer Mobile App against the **Vendor Grocery Hub** backend.

Every endpoint, header, query parameter, request payload, response schema, error structure, and business rule documented here is extracted directly from the actual codebase.

---

## 1. Network & Architecture Overview

### 1.1 Base URL & Routing
* **Backend Protocol & Port:** `http://<BACKEND_HOST>:8001` (Development) or `https://<API_DOMAIN>` (Production)
* **URL Namespaces:**
  * Marketplace Integration Engine: `/api/workforce/marketplace/`
  * Category Catalog & Hierarchy: `/api/workforce/seller-hub/categories/`
  * Public Storefront & Direct Cart: `/api/workforce/public/`
  * Promotions (Deals & Coupons): `/api/workforce/promotions/`

---

## 2. Authentication & Authorization Specifications

Authentication is determined strictly by the backend view permission classes:

| Endpoint Group | Permission Class | Required Headers | Description |
| :--- | :--- | :--- | :--- |
| **Marketplace APIs** (`/marketplace/*`) | `IsMarketplaceIntegrationCaller` | `Authorization: Bearer <API_KEY>`<br>*(or `X-Workforce-Webhook-Secret: <SECRET>`)* | Used for catalog synchronization, cart pre-checkout validation, order intake, and cancellation. |
| **Public Storefront** (`/public/*`) | `AllowAny` | *No auth required* | Used for public store browsing, customer cart, public checkout, and live order tracking. |
| **Category Tree** (`/seller-hub/categories/*`) | `IsAuthenticated` | `Authorization: Bearer <JWT_TOKEN>` *(or user session)* | Read-only category tree & hierarchy data. |

---

## 3. Image URL Resolution

* **Image URL Format:** Image fields (`primary_image`, `images`, `logo_url`, `banner_url`, `image`) return either:
  1. A relative media path: `"/media/seller_products/<uuid>.<ext>"`
  2. A fully-qualified CDN URL: `"https://<storage_bucket>/seller_products/<uuid>.<ext>"`
* **Flutter Resolution Rule:**
  ```dart
  String resolveImageUrl(String? rawUrl, String baseUrl) {
    if (rawUrl == null || rawUrl.isEmpty) return "";
    if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) {
      return rawUrl;
    }
    return "$baseUrl$rawUrl";
  }
  ```

---

## 4. End-to-End Grocery Mobile App Flow

```
[ Grocery Home Screen ]
   ├── Public Stores Feed: GET /api/workforce/public/stores/
   ├── Category Carousel: GET /api/workforce/seller-hub/categories/active/?tree=true
   └── Deals & Offers: GET /api/workforce/promotions/deals/
            │
            ▼
[ Categories & Subcategories Screen ]
   ├── Category Tree: GET /api/workforce/seller-hub/categories/active/?tree=true
   └── Category Products: GET /api/workforce/marketplace/products/?category_id={id}
            │
            ▼
[ Product Listing, Search & Filters ]
   └── GET /api/workforce/marketplace/products/?search={query}&category_id={id}&seller_id={id}&page={page}&page_size=20
            │
            ▼
[ Product Details Screen ]
   └── GET /api/workforce/marketplace/products/{id}/
            │
            ▼
[ Cart & Pre-Checkout Validation ]
   ├── Validate Stock & Prices: POST /api/workforce/marketplace/cart/validate/
   └── Direct Cart Storage: GET/POST /api/workforce/public/cart/
            │
            ▼
[ Checkout & Order Intake ]
   └── POST /api/workforce/marketplace/orders/intake/ (or POST /api/workforce/public/checkout/)
```

---

## 5. API Reference Guide

---

### 5.1 Category & Subcategory Hierarchy APIs

#### 1. Get Active Category Tree
* **Endpoint:** `GET /api/workforce/seller-hub/categories/active/?tree=true`
* **Auth:** Authenticated User / Caller (`Authorization: Bearer <TOKEN>`)
* **Description:** Retrieves the recursive category tree with full ancestor-lineage active validation.
* **Query Parameters:**
  * `tree` *(boolean)*: Pass `true` for nested child hierarchy.
* **Response Status:** `200 OK`
* **Response Payload:**
```json
[
  {
    "id": 1,
    "name": "Groceries",
    "slug": "groceries",
    "description": "Daily staples and fresh grocery items",
    "icon": "Store",
    "image": "/media/categories/groceries.jpg",
    "is_active": true,
    "sort_order": 1,
    "parent_id": null,
    "level": 0,
    "children_count": 2,
    "services_count": 0,
    "inventory_items_count": 25,
    "children": [
      {
        "id": 4,
        "name": "Dairy & Breakfast",
        "slug": "dairy-breakfast",
        "description": "Milk, butter, cheese, and breakfast essentials",
        "icon": "Milk",
        "image": "",
        "is_active": true,
        "sort_order": 1,
        "parent_id": 1,
        "level": 1,
        "children_count": 1,
        "services_count": 0,
        "inventory_items_count": 12,
        "children": [
          {
            "id": 10,
            "name": "Fresh Milk & Curd",
            "slug": "fresh-milk-curd",
            "description": "Pasteurized cow milk, toned milk, and curd",
            "icon": "Milk",
            "image": "",
            "is_active": true,
            "sort_order": 1,
            "parent_id": 4,
            "level": 2,
            "children_count": 0,
            "services_count": 0,
            "inventory_items_count": 6,
            "children": []
          }
        ]
      }
    ]
  }
]
```

#### 2. Get Full Category Tree
* **Endpoint:** `GET /api/workforce/seller-hub/categories/tree/?active_only=true`
* **Auth:** `Authorization: Bearer <TOKEN>`
* **Description:** Returns the global category hierarchy starting from root nodes.

---

### 5.2 Product Catalog, Search, Filters & Brands

#### 1. Search & Filter Products
* **Endpoint:** `GET /api/workforce/marketplace/products/`
* **Auth:** `Authorization: Bearer <SECRET>` or `X-Workforce-Webhook-Secret: <SECRET>`
* **Description:** Returns all published, approved, in-stock grocery items. Automatically cascades through subcategory trees.
* **Query Parameters:**
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `search` | `string` | No | Case-insensitive match against `title`, `brand`, `sku`, and `description`. |
  | `category_id` | `integer` | No | Filters by category ID (includes all child subcategories). |
  | `category_slug`| `string` | No | Filters by category slug (includes all child subcategories). |
  | `company_id` | `integer` | No | Filters to a specific seller store (alias `seller_id`). |
  | `page` | `integer` | No | Page number (default: `1`). |
  | `page_size` | `integer` | No | Items per page (default: `20`, max: `100`). |

* **Response Status:** `200 OK`
* **Response Payload:**
```json
{
  "count": 48,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "results": [
    {
      "id": 101,
      "sku": "MILK-AMUL-500ML",
      "title": "Amul Taaza Homogenised Toned Milk 500 ml",
      "brand": "Amul",
      "unit": "pack",
      "pack_size": "500 ml",
      "mrp": "30.00",
      "selling_price": "28.00",
      "currency": "INR",
      "primary_image": "/media/seller_products/amul_taaza_500.jpg",
      "images": [
        "/media/seller_products/amul_taaza_500.jpg",
        "/media/seller_products/amul_taaza_back.jpg"
      ],
      "description": "Fresh toned milk with 3.0% fat and 8.5% SNF.",
      "storage_info": "Keep refrigerated below 4°C",
      "expiry_info": "Best before 2 days from packaging",
      "tax_rate": "0.00",
      "hsn_code": "0401",
      "seller_id": 5,
      "seller_name": "Fresh Express Grocery Mart",
      "category_path": "Groceries > Dairy & Breakfast > Fresh Milk & Curd",
      "category_hierarchy": [
        {
          "id": 1,
          "name": "Groceries",
          "slug": "groceries"
        },
        {
          "id": 4,
          "name": "Dairy & Breakfast",
          "slug": "dairy-breakfast"
        },
        {
          "id": 10,
          "name": "Fresh Milk & Curd",
          "slug": "fresh-milk-curd"
        }
      ],
      "available_stock": 45,
      "in_stock": true,
      "seller": {
        "id": 5,
        "name": "Fresh Express Grocery Mart",
        "slug": "fresh-express-grocery-mart"
      },
      "category": {
        "id": 10,
        "name": "Fresh Milk & Curd",
        "slug": "fresh-milk-curd",
        "path": "Groceries > Dairy & Breakfast > Fresh Milk & Curd",
        "hierarchy": [
          { "id": 1, "name": "Groceries", "slug": "groceries" },
          { "id": 4, "name": "Dairy & Breakfast", "slug": "dairy-breakfast" },
          { "id": 10, "name": "Fresh Milk & Curd", "slug": "fresh-milk-curd" }
        ]
      },
      "availability": {
        "in_stock": true,
        "available_quantity": "45.000",
        "unit": "pack"
      },
      "updated_at": "2026-09-19T10:15:30.123456Z"
    }
  ]
}
```

---

### 5.3 Product Details API

* **Endpoint:** `GET /api/workforce/marketplace/products/<int:pk>/`
* **Auth:** `Authorization: Bearer <SECRET>`
* **Description:** Retrieves detailed product specifications, multi-image gallery, storage, and live availability. Returns `404` if unapproved or out of stock.
* **Response Status:** `200 OK`
* **Response Payload:** Same object format as an individual item in `results`.

---

### 5.4 Pre-Checkout Cart Validation API

* **Endpoint:** `POST /api/workforce/marketplace/cart/validate/`
* **Auth:** `Authorization: Bearer <SECRET>`
* **Description:** Server-to-server or app-level validation checking stock availability, active merchant status, single-store integrity, and price consistency before payment/checkout.
* **Request Body:**
```json
{
  "seller_id": 5,
  "items": [
    {
      "product_id": 101,
      "quantity": 2,
      "expected_unit_price": "28.00"
    }
  ]
}
```
* **Response Status:** `200 OK`
* **Response Payload:**
```json
{
  "is_valid": true,
  "currency": "INR",
  "seller_id": 5,
  "seller_name": "Fresh Express Grocery Mart",
  "subtotal": "56.00",
  "total_items": 1,
  "total_quantity": "2.000",
  "items": [
    {
      "product_id": 101,
      "sku": "MILK-AMUL-500ML",
      "title": "Amul Taaza Homogenised Toned Milk 500 ml",
      "unit": "pack",
      "status": "AVAILABLE",
      "is_available": true,
      "requested_quantity": "2.000",
      "available_quantity": "45.000",
      "unit_price": "28.00",
      "mrp": "30.00",
      "line_total": "56.00",
      "price_changed": false,
      "current_selling_price": "28.00"
    }
  ],
  "errors": []
}
```

* **Validation Conflict Errors (if any):**
  * `STOCK_UNAVAILABLE` / `INSUFFICIENT_STOCK`: Available stock is less than requested.
  * `PRODUCT_UNAVAILABLE`: Product is paused, rejected, or draft.
  * `STORE_INACTIVE`: Merchant store is inactive.
  * `STORE_MISMATCH`: Items from multiple stores detected.
  * `PRICE_MISMATCH`: Price has changed since added to cart.

---

### 5.5 Public Stores & Deals (Storefront Direct Experience)

#### 1. List Active Stores
* **Endpoint:** `GET /api/workforce/public/stores/`
* **Auth:** `None` (Public `AllowAny`)
* **Response Status:** `200 OK`
* **Response Payload:**
```json
[
  {
    "id": 2,
    "store_name": "Fresh Express Grocery Mart",
    "store_slug": "fresh-express-grocery-mart",
    "tagline": "Farm fresh vegetables & dairy delivered in 30 mins",
    "logo_url": "/media/stores/fresh_express_logo.png",
    "banner_url": "/media/stores/fresh_express_banner.png",
    "rating_average": 4.8,
    "total_reviews": 124,
    "delivery_radius_km": 10.0,
    "estimated_delivery_mins": 30,
    "minimum_order_amount": "100.00"
  }
]
```

#### 2. Get Store Details, Products, Deals & Coupons
* **Endpoint:** `GET /api/workforce/public/stores/<slug>/`
* **Auth:** `None` (Public `AllowAny`)
* **Response Status:** `200 OK`
* **Response Payload:**
```json
{
  "store": {
    "id": 2,
    "store_name": "Fresh Express Grocery Mart",
    "store_slug": "fresh-express-grocery-mart",
    "tagline": "Farm fresh vegetables & dairy",
    "description": "Your neighborhood trusted grocery partner.",
    "logo_url": "/media/stores/fresh_express_logo.png",
    "banner_url": "/media/stores/fresh_express_banner.png",
    "rating_average": 4.8,
    "total_reviews": 124,
    "delivery_radius_km": 10.0,
    "estimated_delivery_mins": 30,
    "minimum_order_amount": "100.00",
    "is_accepting_orders": true
  },
  "products": [
    {
      "id": 101,
      "catalogue_service_id": null,
      "name": "Amul Taaza Toned Milk 500ml",
      "category": "Fresh Milk & Curd",
      "image": "/media/seller_products/amul_taaza_500.jpg",
      "price": "28.00",
      "mrp": "30.00",
      "has_deal": true,
      "deal_badge": "Special Offer",
      "discount_percent": 7,
      "unit": "pack",
      "in_stock": true
    }
  ],
  "coupons": [
    {
      "code": "WELCOME50",
      "description": "Flat ₹50 OFF on first grocery order above ₹299",
      "discount_type": "flat",
      "discount_value": "50.00",
      "min_order_amount": "299.00"
    }
  ]
}
```

---

### 5.6 Customer Cart API (Single-Store Invariant)

#### 1. Fetch Current Cart
* **Endpoint:** `GET /api/workforce/public/cart/?customer_id={customer_id}&coupon_code={code}`
* **Auth:** `None` (Public `AllowAny`)
* **Response Status:** `200 OK`
* **Response Payload:**
```json
{
  "cart_id": 14,
  "customer_id": "cust_98765",
  "store": {
    "id": 2,
    "store_name": "Fresh Express Grocery Mart",
    "store_slug": "fresh-express-grocery-mart"
  },
  "items": [
    {
      "inventory_item_id": 101,
      "name": "Amul Taaza Toned Milk 500ml",
      "quantity": 2.0,
      "unit_price": "28.00",
      "mrp": "30.00",
      "line_total": "56.00"
    }
  ],
  "subtotal": 56.0,
  "deal_discount": 4.0,
  "coupon_discount": 0.0,
  "delivery_fee": 25.0,
  "tax_amount": 0.0,
  "total_amount": 81.0
}
```

#### 2. Add / Update Cart Item
* **Endpoint:** `POST /api/workforce/public/cart/`
* **Auth:** `None` (Public `AllowAny`)
* **Request Body:**
```json
{
  "customer_id": "cust_98765",
  "inventory_item_id": 101,
  "quantity": 3.0,
  "force_replace": false
}
```
* **Single-Store Conflict Behavior (HTTP 409):**
  If adding an item from a different store when `force_replace` is `false`, the API returns `409 Conflict`:
```json
{
  "error": {
    "code": "CART_STORE_CONFLICT",
    "message": "Your cart contains items from 'Store A'. Would you like to clear it and add items from 'Store B'?",
    "current_store_id": 1,
    "current_store_name": "Store A",
    "new_store_id": 2,
    "new_store_name": "Store B"
  }
}
```
* **Resolution in Flutter:** Display a dialog asking the user if they want to replace their cart. If confirmed, re-send `POST /api/workforce/public/cart/` with `"force_replace": true`.

#### 3. Clear Cart
* **Endpoint:** `POST /api/workforce/public/cart/clear/`
* **Request Body:**
```json
{
  "customer_id": "cust_98765"
}
```

---

### 5.7 Order Intake & Checkout APIs

#### 1. Marketplace Order Intake (with Atomic Stock Reservation)
* **Endpoint:** `POST /api/workforce/marketplace/orders/intake/`
* **Auth:** `Authorization: Bearer <SECRET>`
* **Request Body:**
```json
{
  "source_order_id": "ORD-SEVO-2026-0001",
  "company_id": 5,
  "customer_id": "cust_98765",
  "customer_name": "Ananya Sharma",
  "customer_phone": "+919876543210",
  "delivery_address": "Flat 402, Green Valley Apts, Bangalore",
  "payment_method": "ONLINE_PAID",
  "delivery_notes": "Please ring the doorbell",
  "items": [
    {
      "product_id": 101,
      "quantity": 2,
      "unit_price": "28.00"
    }
  ]
}
```
* **Response Status:** `201 Created`
* **Response Payload:**
```json
{
  "message": "Order accepted and inventory reserved.",
  "order_id": 88,
  "order_number": "ORD-SEVO-2026-0001",
  "status": "RECEIVED",
  "total_amount": "56.00",
  "created_at": "2026-09-19T10:30:00Z"
}
```

#### 2. Cancel Order & Stock Release
* **Endpoint:** `POST /api/workforce/marketplace/orders/<source_order_id>/cancel/`
* **Auth:** `Authorization: Bearer <SECRET>`
* **Request Body:**
```json
{
  "reason": "Customer cancelled order before dispatch"
}
```
* **Response Status:** `200 OK`
* **Response Payload:**
```json
{
  "message": "Order cancelled and reserved stock released.",
  "order_number": "ORD-SEVO-2026-0001",
  "status": "CANCELLED",
  "released_items_count": 1
}
```

#### 3. Live Order Tracking Status
* **Endpoint:** `GET /api/workforce/marketplace/orders/<source_order_id>/status/`
* **Auth:** `Authorization: Bearer <SECRET>`
* **Response Status:** `200 OK`
* **Status Lifecycle Values:**
  * `RECEIVED` → `ACCEPTED` → `PICKING` → `PACKED` → `READY_FOR_PICKUP` → `OUT_FOR_DELIVERY` → `DELIVERED` (or `CANCELLED`).

---

## 6. Flutter Mobile Implementation Models

Here are the Dart models ready for the Customer Mobile App:

```dart
// Category Model
class CategoryItem {
  final int id;
  final String name;
  final String slug;
  final String description;
  final String icon;
  final String image;
  final bool isActive;
  final int sortOrder;
  final int? parentId;
  final int level;
  final int childrenCount;
  final List<CategoryItem> children;

  CategoryItem({
    required this.id,
    required this.name,
    required this.slug,
    required this.description,
    required this.icon,
    required this.image,
    required this.isActive,
    required this.sortOrder,
    this.parentId,
    required this.level,
    required this.childrenCount,
    required this.children,
  });

  factory CategoryItem.fromJson(Map<String, dynamic> json) {
    return CategoryItem(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      slug: json['slug'] as String? ?? '',
      description: json['description'] as String? ?? '',
      icon: json['icon'] as String? ?? 'Store',
      image: json['image'] as String? ?? '',
      isActive: json['is_active'] as bool? ?? true,
      sortOrder: json['sort_order'] as int? ?? 0,
      parentId: json['parent_id'] as int?,
      level: json['level'] as int? ?? 0,
      childrenCount: json['children_count'] as int? ?? 0,
      children: (json['children'] as List<dynamic>?)
              ?.map((c) => CategoryItem.fromJson(c as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

// Product Model
class GroceryProduct {
  final int id;
  final String sku;
  final String title;
  final String brand;
  final String unit;
  final String packSize;
  final double mrp;
  final double sellingPrice;
  final String currency;
  final String primaryImage;
  final List<String> images;
  final String description;
  final String storageInfo;
  final String expiryInfo;
  final int sellerId;
  final String sellerName;
  final String categoryPath;
  final double availableStock;
  final bool inStock;

  GroceryProduct({
    required this.id,
    required this.sku,
    required this.title,
    required this.brand,
    required this.unit,
    required this.packSize,
    required this.mrp,
    required this.sellingPrice,
    required this.currency,
    required this.primaryImage,
    required this.images,
    required this.description,
    required this.storageInfo,
    required this.expiryInfo,
    required this.sellerId,
    required this.sellerName,
    required this.categoryPath,
    required this.availableStock,
    required this.inStock,
  });

  factory GroceryProduct.fromJson(Map<String, dynamic> json) {
    return GroceryProduct(
      id: json['id'] as int,
      sku: json['sku'] as String? ?? '',
      title: json['title'] as String? ?? '',
      brand: json['brand'] as String? ?? '',
      unit: json['unit'] as String? ?? 'piece',
      packSize: json['pack_size'] as String? ?? '1',
      mrp: double.tryParse(json['mrp']?.toString() ?? '0.0') ?? 0.0,
      sellingPrice:
          double.tryParse(json['selling_price']?.toString() ?? '0.0') ?? 0.0,
      currency: json['currency'] as String? ?? 'INR',
      primaryImage: json['primary_image'] as String? ?? '',
      images: (json['images'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      description: json['description'] as String? ?? '',
      storageInfo: json['storage_info'] as String? ?? '',
      expiryInfo: json['expiry_info'] as String? ?? '',
      sellerId: json['seller_id'] as int? ?? 0,
      sellerName: json['seller_name'] as String? ?? '',
      categoryPath: json['category_path'] as String? ?? '',
      availableStock:
          double.tryParse(json['available_stock']?.toString() ?? '0.0') ?? 0.0,
      inStock: json['in_stock'] as bool? ?? false,
    );
  }

  double get discountPercent {
    if (mrp > 0 && mrp > sellingPrice) {
      return ((mrp - sellingPrice) / mrp) * 100;
    }
    return 0.0;
  }
}
```

---

## 7. Feature-by-Feature Implementation Checklist

| Flow / Feature | Backend API to Call | Parameters / Keys | Notes |
| :--- | :--- | :--- | :--- |
| **1. Grocery Home** | `GET /api/workforce/public/stores/`<br>`GET /api/workforce/seller-hub/categories/active/?tree=true`<br>`GET /api/workforce/promotions/deals/` | N/A | Renders nearby delivery stores, top-level root categories (`level: 0`), and deals carousel. |
| **2. Categories & Subcategories** | `GET /api/workforce/seller-hub/categories/active/?tree=true` | `tree=true` | Parent categories display `children`. Subcategories render with their respective products count. |
| **3. Products Feed** | `GET /api/workforce/marketplace/products/` | `category_id`, `page`, `page_size` | Returns products belonging to the selected category and any descendant subcategories. |
| **4. Brands** | `GET /api/workforce/marketplace/products/` | `search={brand_name}` | Extract unique `brand` values from the product feed for filter pills. |
| **5. Product Details** | `GET /api/workforce/marketplace/products/{id}/` | `id` (path param) | Displays full photo gallery (`images`), storage recommendations, expiry info, and seller details. |
| **6. Search** | `GET /api/workforce/marketplace/products/?search={query}` | `search` | Searches product titles, brands, SKUs, and descriptions concurrently. |
| **7. Filters** | `GET /api/workforce/marketplace/products/` | `category_id`, `category_slug`, `company_id` | Allows narrowing down by store and sub-department. |
| **8. Pricing & Offers** | Product attributes: `mrp`, `selling_price`, `has_deal`, `deal_badge` | In response payload | App computes strike-through MRP and discount badges (`(mrp - selling_price) / mrp * 100`). |
| **9. Stock & Availability** | `POST /api/workforce/marketplace/cart/validate/` | `items: [{product_id, quantity}]` | Live server check ensuring item has not sold out before customer proceeds to checkout. |
| **10. Images** | Product `primary_image` & `images` | Full or relative path | App prepends base URL `http://<HOST>:8001` if path starts with `/media/`. |

---

## 8. Summary of Codes and Responses

* **Success Responses:**
  * `200 OK`: Standard data return.
  * `201 Created`: Order successfully placed and inventory reserved.
* **Error Handling Codes:**
  * `400 BAD REQUEST`: Invalid payload or missing fields.
  * `403 FORBIDDEN`: Missing or invalid integration key / permissions.
  * `404 NOT FOUND`: Product unapproved or out of stock.
  * `409 CONFLICT` (`CART_STORE_CONFLICT`): Attempting to mix items from two different grocery vendors in the same cart.
  * `409 CONFLICT` (`STOCK_UNAVAILABLE`): Insufficient stock on hand for the requested quantity.
