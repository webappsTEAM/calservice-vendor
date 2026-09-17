"""
vendor/backend/inventory/selectors.py

Vendor-facing stock status/reporting -- ported from
Customer/backend/inventory/selectors/vegetable_stock_selectors.py's admin
selectors (get_admin_stock_status, get_daily_stock_history). The
customer-facing get_stock_status() (in_stock/max_quantity, never exposes
exact numbers) stays exclusively in Customer/backend -- it's checkout-path
logic, not a vendor concern.
"""
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from django.utils import timezone

from inventory.models import StockMovement
from inventory.utils.unit_conversion import format_grams_for_display


def get_vendor_stock_status(product, for_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Same shape as Customer backend's get_admin_stock_status() -- kept
    identical so the two apps' stock cards render the same fields.
    """
    item = getattr(product, "stock_item", None)
    target_date = for_date or timezone.localdate()

    raw_base = float(product.base_price or 0)
    raw_offer = float(product.offer_price) if product.offer_price is not None else None

    if raw_offer is not None and raw_offer > 0:
        if raw_offer > raw_base:
            selling_price = raw_base
            mrp_price = raw_offer
        else:
            selling_price = raw_offer
            mrp_price = raw_base
        offer_pct = round(((mrp_price - selling_price) / mrp_price) * 100) if mrp_price > 0 else 0
    else:
        selling_price = raw_base
        mrp_price = raw_base
        offer_pct = 0
        tag_val = getattr(product, "tag", "") or ""
        if tag_val and "%" in tag_val:
            import re
            m = re.search(r"(\d+(?:\.\d+)?)\s*%", tag_val)
            if m:
                offer_pct = round(float(m.group(1)))
                if offer_pct > 0 and selling_price > 0:
                    mrp_price = round(selling_price / (1 - offer_pct / 100.0), 2)

    veg_gram = getattr(product, "duration", "") or "500 g"

    consumed_grams = 0
    opening_grams = None
    if item:
        day_movements = list(
            StockMovement.objects.filter(item=item, created_at__date=target_date).order_by("id")
        )
        if item.default_daily_quantity_grams is not None:
            opening_grams = item.default_daily_quantity_grams
        elif day_movements:
            earliest = day_movements[0]
            if earliest.movement_type == StockMovement.MovementType.DAILY_RESET:
                opening_grams = earliest.balance_after_grams
            else:
                opening_grams = earliest.balance_after_grams - earliest.delta_grams
        else:
            prev_m = StockMovement.objects.filter(
                item=item, created_at__date__lt=target_date,
            ).order_by("-created_at").first()
            opening_grams = prev_m.balance_after_grams if prev_m else (item.default_daily_quantity_grams or item.stock_quantity_grams or 0)

        if day_movements:
            consumed_grams = sum(abs(m.delta_grams) for m in day_movements if m.movement_type == StockMovement.MovementType.SOLD)

    reorder_threshold_grams = item.reorder_threshold if item and item.reorder_threshold else 0
    restock_level_grams = item.default_daily_quantity_grams if item and item.default_daily_quantity_grams else (item.reorder_quantity if item else 0)

    is_owned_by_another_vendor = bool(item and item.org_id is not None)

    base = {
        "consumed_stock_grams": consumed_grams,
        "consumed_stock_display": format_grams_for_display(consumed_grams),
        "consumed_date": target_date.strftime("%Y-%m-%d"),
        "restock_level_grams": restock_level_grams,
        "restock_level_display": format_grams_for_display(restock_level_grams) if restock_level_grams else "—",
        "reorder_level_grams": reorder_threshold_grams,
        "reorder_level_display": format_grams_for_display(reorder_threshold_grams) if reorder_threshold_grams else "—",
        "price": selling_price,
        "mrp": mrp_price,
        "offer_price": mrp_price if mrp_price != selling_price else None,
        "offer_percentage": offer_pct,
        "vegetable_gram": veg_gram,
        "is_claimed": is_owned_by_another_vendor,
        "owning_company_id": item.org_id if item else None,
    }

    if not item or item.stock_quantity_grams is None:
        base.update({
            "state": "not_tracked",
            "today_available_grams": None,
            "default_daily_grams": item.default_daily_quantity_grams if item else None,
            "today_available_display": "Not Tracked",
            "default_daily_display": format_grams_for_display(item.default_daily_quantity_grams) if item and item.default_daily_quantity_grams else "None",
            "opening_stock_grams": opening_grams,
            "opening_stock_display": format_grams_for_display(opening_grams) if opening_grams is not None else "—",
            "unit": item.unit if item else "g",
        })
        return base

    live_grams = item.stock_quantity_grams
    base.update({
        "state": "in_stock" if live_grams > 0 else "out_of_stock",
        "today_available_grams": live_grams,
        "default_daily_grams": item.default_daily_quantity_grams,
        "today_available_display": format_grams_for_display(live_grams),
        "default_daily_display": format_grams_for_display(item.default_daily_quantity_grams) if item.default_daily_quantity_grams is not None else "None",
        "opening_stock_grams": opening_grams if opening_grams is not None else live_grams,
        "opening_stock_display": format_grams_for_display(opening_grams if opening_grams is not None else live_grams),
        "unit": item.unit or "g",
    })
    return base


def get_daily_stock_history(product, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    item = getattr(product, "stock_item", None)
    if not item:
        return []

    movements = list(
        StockMovement.objects.filter(
            item=item, created_at__date__gte=start_date, created_at__date__lte=end_date,
        ).order_by("id")
    )

    movements_by_date: Dict[date, list] = {}
    for m in movements:
        d = timezone.localtime(m.created_at).date()
        movements_by_date.setdefault(d, []).append(m)

    history = []
    curr_date = start_date
    prior_closing = None
    prev_movement = StockMovement.objects.filter(
        item=item, created_at__date__lt=start_date,
    ).order_by("-created_at").first()
    if prev_movement:
        prior_closing = prev_movement.balance_after_grams

    today = timezone.localdate()

    while curr_date <= end_date:
        day_movements = movements_by_date.get(curr_date, [])

        if day_movements:
            earliest = day_movements[0]
            if earliest.movement_type == StockMovement.MovementType.DAILY_RESET:
                opening = earliest.balance_after_grams
            else:
                opening = earliest.balance_after_grams - earliest.delta_grams
            sold = sum(abs(m.delta_grams) for m in day_movements if m.movement_type == StockMovement.MovementType.SOLD)
            restocked = sum(m.delta_grams for m in day_movements if m.movement_type == StockMovement.MovementType.RESTOCK)
            adjustments = sum(m.delta_grams for m in day_movements if m.movement_type == StockMovement.MovementType.ADJUSTMENT)
            latest = day_movements[-1]
            closing = latest.balance_after_grams
            prior_closing = closing
            movement_items = [
                {
                    "id": m.id,
                    "type": m.movement_type,
                    "type_display": m.get_movement_type_display(),
                    "delta_grams": m.delta_grams,
                    "delta_display": f"{'+' if m.delta_grams > 0 else '-'}{format_grams_for_display(abs(m.delta_grams))}",
                    "balance_after_grams": m.balance_after_grams,
                    "balance_after_display": format_grams_for_display(m.balance_after_grams),
                    "reason": m.reason,
                    "booking_ref": m.booking_ref,
                    "time": timezone.localtime(m.created_at).strftime("%I:%M %p"),
                }
                for m in day_movements
            ]
            has_activity = True
        else:
            if curr_date == today and (item.stock_quantity_grams is not None or item.default_daily_quantity_grams is not None):
                opening = item.stock_quantity_grams or 0
                sold = restocked = adjustments = 0
                closing = item.stock_quantity_grams or 0
                movement_items = []
                has_activity = True
            elif prior_closing is not None:
                opening = closing = prior_closing
                sold = restocked = adjustments = 0
                movement_items = []
                has_activity = True
            else:
                opening = closing = sold = restocked = adjustments = 0
                movement_items = []
                has_activity = False

        if has_activity or curr_date == today:
            history.append({
                "date": curr_date.strftime("%Y-%m-%d"),
                "opening_grams": opening,
                "opening_display": format_grams_for_display(opening),
                "sold_grams": sold,
                "sold_display": format_grams_for_display(sold),
                "restocked_grams": restocked,
                "restocked_display": format_grams_for_display(restocked),
                "adjustments_grams": adjustments,
                "closing_grams": closing,
                "closing_display": format_grams_for_display(closing),
                "movements": movement_items,
            })

        curr_date += timedelta(days=1)

    return history
