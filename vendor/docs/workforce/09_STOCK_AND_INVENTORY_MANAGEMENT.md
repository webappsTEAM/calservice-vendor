# 09. Stock & Inventory Management System

## 1. System Overview

The Stock & Inventory subsystem provides real-time stock control, daily replenishment automation, and gram-level precision for perishable grocery produce, consumable spare parts, and vendor tools.

```
┌─────────────────────────────────────────────────────────────┐
│                    STOCK MOVEMENT ENGINE                    │
│                                                             │
│   Daily Replenishment   ◄───►   Customer Orders / Sales     │
│  (default_daily_grams)         (Atomic Stock Reservation)   │
│            │                               │                │
│            └───────────────┬───────────────┘                │
│                            ▼                                │
│        ┌───────────────────────────────────────┐            │
│        │        Central Stock Movement         │            │
│        │   - RESTOCK                           │            │
│        │   - ADJUSTMENT                        │            │
│        │   - DAILY_RESET                       │            │
│        │   - SOLD                              │            │
│        │   - RESTOCKED_ON_CANCELLATION         │            │
│        └───────────────────┬───────────────────┘            │
│                            │                                │
│                            ▼                                │
│        ┌───────────────────────────────────────┐            │
│        │      Real-Time Balance In Grams       │            │
│        │        (Zero-Drift Auditing)          │            │
│        └───────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Gram-Level Precision & Unit Conversion

To eliminate rounding errors when measuring bulk produce (e.g. 250g beans vs 1.5kg potatoes):
- All physical weights are stored internally in integer grams (`stock_quantity_grams`).
- Unit conversion utilities seamlessly parse kilograms, grams, pieces, packets, and bunches:

```python
# inventory/utils/unit_conversion.py
def convert_to_grams(quantity, unit):
    unit = unit.lower().strip()
    if unit in ('kg', 'kilogram', 'kilograms'):
        return int(Decimal(quantity) * 1000)
    elif unit in ('g', 'gram', 'grams'):
        return int(Decimal(quantity))
    elif unit in ('piece', 'pc', 'bunch', 'packet'):
        return int(quantity) # Discrete items handled as unit count
    raise ValueError(f"Unsupported unit: {unit}")
```

---

## 3. Stock Movement Types & Audit Trails

Every change to stock creates an immutable `StockMovement` row:
1. **`RESTOCK`:** Adding fresh shipments or procurement inventory.
2. **`DAILY_RESET`:** Automated morning reset bringing stock levels to `default_daily_quantity_grams`.
3. **`SOLD`:** Decremented atomically upon order checkout confirmation.
4. **`RESTOCKED_ON_CANCELLATION`:** Restores reserved stock when a customer or vendor cancels an order.
5. **`ADJUSTMENT`:** Manual corrections due to wastage, damage, or discrepancy audits.

---

## 4. Frontend Management (`AdminStockManagementPage.jsx`)

The vendor management UI allows store managers to:
- Filter stock items by category (Produce, Spare Parts, Tools, Consumables).
- Perform instant 1-click restocks with note logs.
- Configure daily auto-reset baselines.
- View real-time visual progress bars indicating remaining stock against low-stock alert thresholds.
