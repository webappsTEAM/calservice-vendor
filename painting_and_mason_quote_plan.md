# Painting & Masonry Quotation System — Master Specification & Plan

## 1. Executive Summary & Architecture

The **Quotation Engine** in Calservices manages high-value, site-specific home improvement and civil services (**Painting, Waterproofing, and Masonry**). These services cannot be fulfilled through fixed e-commerce checkout because their final scope depends on physical on-site assessment.

The system uses a unified **Two-Stage Booking & Quotation Lifecycle**:
1. **Stage 1 (Consultation & Site Inspection):** Customer books a consultation. A technician visits the property to take laser measurements, inspect surface/structural conditions, and formulate the quote.
2. **Stage 2 (Quoted Work Execution):** The vendor creates an itemized digital quotation on the Vendor App. The customer receives a secure tokenized link to approve, pay the advance, and initiate execution.

```mermaid
flowchart TD
    A[Customer Books Consultation (Painting or Masonry)] --> B{Haversine Distance Check from Hosur Hub}
    B -- "<= 15 km" --> C1[Consultation Fee: ₹0.00 (Free)]
    B -- "> 15 km" --> C2[Consultation Fee: ₹300.00]
    C1 --> D[Vendor Dispatched & Arrives on Site]
    C2 --> D
    D --> E[Technician Status: ARRIVED (Arrival Gate Enforcement)]
    E --> F[Vendor Opens App & Clicks 'Create Quote']
    F --> G[Select Service from Dropdown e.g., Painting or Masonry]
    G --> H[System Auto-Fills Fixed Base Rates, Units & Warranties]
    H --> I[Vendor Enters Site Measurements & Material Specs]
    I --> J[App Auto-Calculates Total & Advance Split]
    J --> K{Grand Total > ₹30,000? (Painting)}
    K -- Yes --> L[Status: PENDING_ADMIN_REVIEW -> Admin Approves]
    K -- No --> M[Status: SENT_TO_CUSTOMER]
    L --> M
    M --> N[Customer Receives Token Link via SMS/WhatsApp]
    N --> O{Customer Decision}
    O -- 'Change Requested' --> P[Status: REQUESTED_CHANGES -> Vendor Revises v2]
    O -- 'Declined' --> Q[Status: DECLINED -> Booking Closed]
    O -- 'Approved' --> R[Status: APPROVED -> Customer Pays Advance]
    R --> S[Create Child 'quoted_work' Service Request]
    S --> T[Vendor Procures Materials & Begins Execution]
```

---

## 2. Universal Consultation Policy (Stage 1)

All consultation bookings across **both Painting and Masonry** follow the single distance-based rule calculated from the Hosur Central Hub $(12.7409, 77.8253)$:

$$\text{Consultation Fee} = \begin{cases} \textbf{₹0.00 (FREE)} & \text{if distance } \le 15\text{ km} \\ \textbf{₹300.00} & \text{if distance } > 15\text{ km} \end{cases}$$

> [!IMPORTANT]
> There are **no arbitrary ₹49 slot fees**. The consultation fee is strictly governed by the $15\text{ km}$ geofence.

---

## 3. Painting & Waterproofing Quotation Plan

### 3.1 Standard Rate Cards & Units

| Category | Service / Treatment | Base Rate | Unit | Classification | Warranty Provided |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Waterproofing** | 3 mm Tar Sheet / Gas Heating Waterproofing | **₹100.00** | / sq.ft | Material + Labour | **10-Year Warranty** |
| **Waterproofing** | Terrace Waterproofing — 4 Coat | **₹50.00** | / sq.ft | Material + Labour | **5-Year Warranty** (Labour-only) |
| **Waterproofing** | Terrace Waterproofing — 2 Coat | **₹20.00** | / sq.ft | Material + Labour | — |
| **Waterproofing** | Roof Repair / Patch Work | **₹25.00** | / sq.ft | Material + Labour | — |
| **Waterproofing** | PU Coating / Dampness Treatment | **₹35.00** | / sq.ft | Material + Labour | — |
| **Interior Painting** | Premium Interior Emulsion | **₹15.00** | / sq.ft | Material + Labour | — |
| **Interior Painting** | Ceiling Painting | **₹12.00** | / sq.ft | Material + Labour | — |
| **Exterior Painting** | Weatherproof Exterior Emulsion | **₹18.00** | / sq.ft | Material + Labour | — |
| **Wood & Metal** | PU Coat Gates, Doors & Grills | **₹85.00** | / sq.ft | Material + Labour | — |
| **Texture Decor** | Royal Texture Play / Stencil Design | **₹120.00** | / sq.ft | Material + Labour | — |

### 3.2 Fixed Slabs & Flat Rates
* **Industrial Epoxy Flooring:** $1\text{ mm} \rightarrow \textbf{₹60/sq.ft}$ | $2\text{ mm} \rightarrow \textbf{₹90/sq.ft}$ | $3\text{ mm} \rightarrow \textbf{₹110/sq.ft}$
* **Water Tank Waterproofing:** $\le 1,000\text{L} \rightarrow \textbf{₹1,700 flat}$ | $1,000\text{L}-5,000\text{L} \rightarrow \textbf{₹1.50/Litre}$ | $10,000\text{L} \rightarrow \textbf{₹17,000 flat}$
* **Bathroom Waterproofing:** Small/Medium: **₹3,500 flat** | Large: **₹8,000 flat**

### 3.3 Strict Warranty Tiers
The system supports **strictly two warranty options**:
1. **5-Year Warranty** (e.g., Terrace Waterproofing — 4 Coat)
2. **10-Year Warranty** (e.g., 3 mm Bituminous Tar Sheet)

---

## 4. Masonry Quotation Plan (Exactly 2 Services)

Masonry is strictly focused on **two specialized services**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. BATHROOM TILE FIXING                                                     │
│ • Pricing Model: Bathroom Size Slabs                                        │
│   - Small Bathroom (up to 50 sq.ft):    ₹10,000.00 flat                     │
│   - Medium Bathroom (50 – 80 sq.ft):    ₹10,000.00 flat                     │
│   - Large Bathroom (80+ sq.ft):         ₹20,000.00 flat                     │
│ • Scope: Surface leveling, adhesive laying, spacers, epoxy waterproof grout │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. MINOR MASONRY / SMALL CONSTRUCTION WORK                                  │
│ • Pricing Model: Area Rate with Minimum Area Threshold                      │
│   - Unit Rate:                          ₹120.00 / sq.ft                     │
│   - Minimum Area Requirement:           500 sq.ft (Strict minimum rule)     │
│   - Base Starting Total (500 × ₹120):   ₹60,000.00                          │
│ • Scope: M-sand, cement, bricks/blocks, wall building, plaster leveling     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Masonry Payment Schedule
Every Masonry quote enforces a **mandatory 50/50 payment split**:
* **50% Advance Upfront:** Paid by customer upon quote approval to procure cement, sand, bricks, and tile adhesive.
* **50% Balance on Completion:** Paid upon physical inspection and job sign-off.

---

## 5. Vendor App — Quotation Screen Specification

When the vendor arrives on site and opens the **"Create Quote"** screen, the interface provides a 5-step guided form:

```
┌────────────────────────────────────────────────────────────────────────┐
│ VENDOR APP — CREATE QUOTATION SCREEN                                   │
├────────────────────────────────────────────────────────────────────────┤
│ STEP 1: SELECT SERVICE (DROPDOWN)                                      │
│ Category: [ Painting & Waterproofing  OR  Masonry Work ]               │
│ Service Item: [ Select from Rate Card Dropdown ▼ ]                     │
│                                                                        │
│ • Auto-Filled Base Rate: (e.g. ₹50.00 / sq.ft or ₹120.00 / sq.ft)      │
│ • Auto-Filled Unit: (sq.ft / flat / Litre)                             │
│ • Auto-Filled Warranty: (5-Year / 10-Year / None)                      │
├────────────────────────────────────────────────────────────────────────┤
│ STEP 2: SITE MEASUREMENTS                                              │
│ • Room / Area Name: [ e.g., Master Bedroom / Terrace Floor / Wall 1 ]  │
│ • Dimensions: Length (ft) [ 25.0 ] × Width/Height (ft) [ 20.0 ]        │
│ • Deductions: Windows / Doors (sq.ft) [ -50.0 ]                        │
│ • Calculated Net Area: 450.0 sq.ft                                     │
│ [ + Add Another Room / Area ]                                          │
├────────────────────────────────────────────────────────────────────────┤
│ STEP 3: MATERIAL SPECIFICATIONS                                        │
│ • Brand: [ Asian Paints / Dr. Fixit / Ultratech / Roff / Berger ▼ ]    │
│ • Product Tier / Name: [ e.g., Royale Luxury / Raincoat Neo / M-Sand ] │
│ • Finish / Shade Code: [ e.g., Matte - Terracotta 04 ]                 │
│ • Condition Photos: [ + Take Before-Work Camera Photos ]               │
├────────────────────────────────────────────────────────────────────────┤
│ STEP 4: FINANCIAL SUMMARY (AUTO-CALCULATED)                            │
│ • Subtotal:                                                ₹22,500.00  │
│ • Taxes (GST 18%):                                         + ₹4,050.00 │
│ • Grand Total:                                             ₹26,550.00  │
│                                                                        │
│ PAYMENT SCHEDULE:                                                      │
│ • Advance Required (50% Waterproofing/Masonry):            ₹13,275.00  │
│ • Balance on Completion:                                   ₹13,275.00  │
├────────────────────────────────────────────────────────────────────────┤
│ STEP 5: ACTION                                                         │
│ [ SEND QUOTE TO CUSTOMER ]                                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Customer Decision Portal & Actions

The customer receives a link `https://calservices.com/booking/quote/<token>`:

```
┌────────────────────────────────────────────────────────────────────────┐
│ CUSTOMER QUOTE DECISION PORTAL (MOBILE VIEW)                           │
├────────────────────────────────────────────────────────────────────────┤
│ 📄 Quotation #PQ-20260904-4950                                         │
│ Service: Terrace Waterproofing — 4 Coat                                │
│ Area: 450 sq.ft | Material: Dr. Fixit Raincoat Neo                     │
│ Warranty: 5-Year Comprehensive Warranty Card Included                  │
│                                                                        │
│ Total Project Cost: ₹26,550.00                                         │
│ Advance Payable Now (50%): ₹13,275.00                                  │
│ Balance on Completion (50%): ₹13,275.00                                │
│                                                                        │
│ [ ⬇ Download Official PDF Quote ]                                      │
├────────────────────────────────────────────────────────────────────────┤
│ [ ✅ APPROVE & PAY ADVANCE (₹13,275) ]                                 │
│   -> Spawns execution booking & dispatches technician                  │
│                                                                        │
│ [ 🔄 REQUEST CHANGES / RE-QUOTE ]                                      │
│   -> Opens notes box for customer to request scope/material edits      │
│                                                                        │
│ [ ❌ DECLINE QUOTE ]                                                   │
│   -> Asks for reason and closes consultation                           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Business Rules & Guardrails Summary

| Parameter | Rule & Implementation | Rationale |
| :--- | :--- | :--- |
| **Arrival Gate** | Quotation creation is locked until technician status is `ARRIVED`. | Ensures all quotes are based on physical inspection, never phone estimates. |
| **No Customer Materials** | Items with `source_type == "CUSTOMER"` are strictly rejected. | Protects workmanship warranties and prevents failure from expired chemicals/poor sand. |
| **High-Value Gate** | Painting quotes $> ₹30,000$ enter `PENDING_ADMIN_REVIEW`. | Supervisors verify measurements and margins before customer sees high-value quotes. |
| **Masonry Minimum Area** | Minor Masonry requires $\ge 500\text{ sq.ft}$ at ₹120/sq.ft. | Ensures viability for mobilizing mason labor, cement bags, and M-sand transport. |
| **Advance Payment Split** | **50% Advance** for Waterproofing ($\ge ₹1,000$) & Masonry; **100% Upfront** for standard painting. | Covers high initial raw material and chemical procurement expenses. |
| **Child Booking Creation** | Approving a quote creates a child `ServiceRequest` (`request_kind="quoted_work"`). | Links execution history directly to the parent inspection booking. |

---

## 8. Summary Table of Services, Pricing & Warranties

| Service Name | Category | Pricing Basis | Rate / Slabs | Advance % | Warranty |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **3mm Tar Sheet Waterproofing** | Waterproofing | Area | **₹100.00 / sq.ft** | 50% | **10-Year Warranty** |
| **Terrace Waterproofing (4-Coat)** | Waterproofing | Area | **₹50.00 / sq.ft** | 50% | **5-Year Warranty** |
| **Terrace Waterproofing (2-Coat)** | Waterproofing | Area | **₹20.00 / sq.ft** | 50% | — |
| **Roof Repair / Patch Work** | Waterproofing | Area | **₹25.00 / sq.ft** | 50% | — |
| **PU Dampness Injection** | Waterproofing | Area | **₹35.00 / sq.ft** | 50% | — |
| **Bathroom Waterproofing** | Waterproofing | Flat Tier | **₹3,500** (S/M) / **₹8,000** (L) | 50% | — |
| **Industrial Epoxy Flooring** | Waterproofing | Tiered Slabs | **₹60** (1mm) / **₹90** (2mm) / **₹110** (3mm) | 50% | — |
| **Water Tank Waterproofing** | Waterproofing | Capacity | **₹1,700** ($\le 1\text{kL}$) / **₹1.50/L** / **₹17,000** ($10\text{kL}$) | 50% | — |
| **Premium Interior Emulsion** | Painting | Area | **₹15.00 / sq.ft** | 100% | — |
| **Ceiling Painting** | Painting | Area | **₹12.00 / sq.ft** | 100% | — |
| **Weatherproof Exterior Emulsion** | Painting | Area | **₹18.00 / sq.ft** | 100% | — |
| **Wood & Metal PU Polish/Paint** | Painting | Area | **₹85.00 / sq.ft** | 100% | — |
| **Royal Texture / Stencil Decor** | Painting | Area | **₹120.00 / sq.ft** | 100% | — |
| **Bathroom Tile Fixing** | Masonry | Flat Slabs | **₹10,000** (Small/Med) / **₹20,000** (Large) | 50% | — |
| **Minor Masonry & Construction** | Masonry | Area ($\ge 500\text{ sq.ft}$) | **₹120.00 / sq.ft** | 50% | — |
