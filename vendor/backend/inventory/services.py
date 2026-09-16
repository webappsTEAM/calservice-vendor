"""
vendor/backend/inventory/services.py

Vendor-facing stock mutation logic -- ported from
Customer/backend/inventory/services/vegetable_stock_service.py, trimmed to
what a vendor's own restock/adjust/reprice actions need. Booking-time
reservation and cancellation-release logic stays exclusively in
Customer/backend (that's checkout-path logic, not vendor-facing) and is
deliberately NOT duplicated here.

Ownership: a Package has no direct company FK -- ownership flows through
Package.stock_item.org (see VENDOR_STOCK_MANAGEMENT_IMPLEMENTATION_PLAN.md,
Phase 1.5: confirmed one-vendor-per-product). A product with no stock_item
yet is unclaimed; the first vendor to restock/reprice/adjust it claims it by
having its InventoryItem created with org=that vendor's company. Every
mutation in this module enforces that once a product IS claimed, only the
owning company's requests can touch it.
"""
import logging
from django.db import transaction
from django.utils import timezone

from inventory.models import InventoryItem, StockMovement
from inventory.utils.unit_conversion import to_grams

logger = logging.getLogger(__name__)


class NotYourProductError(Exception):
    """Raised when a vendor tries to mutate a product owned by a different company."""
    def __init__(self, product_name: str):
        self.product_name = product_name
        super().__init__(f"'{product_name}' is managed by a different vendor.")


def assert_owns_product(product, company) -> None:
    """
    Raises NotYourProductError if `product` already has a stock_item owned by
    a company other than `company`. Unclaimed products (stock_item is None)
    pass -- the calling mutation is what claims them.
    """
    item = getattr(product, "stock_item", None)
    if item is not None and item.org_id is not None and item.org_id != getattr(company, "id", None):
        raise NotYourProductError(product_name=getattr(product, "name", "This product"))


@transaction.atomic
def add_stock(product, quantity, unit, company, entered_by_user=None) -> InventoryItem:
    """ADDITIVE RESTOCK. Adds converted grams to stock_quantity_grams."""
    assert_owns_product(product, company)
    grams_to_add = to_grams(quantity, unit)

    item = product.stock_item
    if not item:
        item = InventoryItem.objects.create(
            org=company,
            name=f"{product.name} (Produce)",
            category=InventoryItem.Category.CONSUMABLE,
            sku=f"VEG-{product.slug.upper()[:20]}",
            unit=unit or "g",
            stock_quantity_grams=0,
            default_daily_quantity_grams=None,
            total_quantity=0,
            available_quantity=0,
        )
        product.stock_item = item
        product.save(update_fields=["stock_item"])
    else:
        item = InventoryItem.objects.select_for_update().get(id=item.id)

    current_stock = item.stock_quantity_grams if item.stock_quantity_grams is not None else 0
    new_stock = current_stock + grams_to_add
    item.stock_quantity_grams = new_stock
    if unit:
        item.unit = unit
    item.save(update_fields=["stock_quantity_grams", "unit"])

    StockMovement.objects.create(
        org=company,
        item=item,
        movement_type=StockMovement.MovementType.RESTOCK,
        delta_grams=grams_to_add,
        balance_after_grams=new_stock,
        reason=f"Restocked {quantity} {unit}",
        entered_by=entered_by_user,
    )
    return item


@transaction.atomic
def adjust_stock(product, quantity, unit, reason: str, company, entered_by_user=None) -> InventoryItem:
    """
    ABSOLUTE SET. Sets stock_quantity_grams to the exact converted value.
    Also used for "mark out of stock" (quantity=0).
    """
    assert_owns_product(product, company)
    if not reason or not str(reason).strip():
        raise ValueError("Reason is required for a stock adjustment.")

    target_grams = to_grams(quantity, unit, allow_zero=True)
    item = product.stock_item
    if not item:
        item = InventoryItem.objects.create(
            org=company,
            name=f"{product.name} (Produce)",
            category=InventoryItem.Category.CONSUMABLE,
            sku=f"VEG-{product.slug.upper()[:20]}",
            unit=unit or "g",
            stock_quantity_grams=target_grams,
            default_daily_quantity_grams=None,
            total_quantity=0,
            available_quantity=0,
        )
        product.stock_item = item
        product.save(update_fields=["stock_item"])
        delta = target_grams
    else:
        item = InventoryItem.objects.select_for_update().get(id=item.id)
        current_stock = item.stock_quantity_grams if item.stock_quantity_grams is not None else 0
        delta = target_grams - current_stock
        item.stock_quantity_grams = target_grams
        if unit:
            item.unit = unit
        item.save(update_fields=["stock_quantity_grams", "unit"])

    StockMovement.objects.create(
        org=company,
        item=item,
        movement_type=StockMovement.MovementType.ADJUSTMENT,
        delta_grams=delta,
        balance_after_grams=target_grams,
        reason=str(reason).strip(),
        entered_by=entered_by_user,
    )
    return item


def mark_out_of_stock(product, company, entered_by_user=None) -> InventoryItem:
    """One-tap 'mark out of stock' -- adjusts live stock to 0."""
    return adjust_stock(
        product=product,
        quantity=0,
        unit="g",
        reason="Marked out of stock by vendor",
        company=company,
        entered_by_user=entered_by_user,
    )


@transaction.atomic
def update_price_and_levels(product, company, *, price=None, offer_price=None,
                             reorder_level_grams=None, restock_level_grams=None,
                             entered_by_user=None) -> None:
    """
    Price/offer-price update on the Package itself, plus reorder/restock
    level updates on its InventoryItem. Levels only touch config fields, not
    live stock_quantity_grams -- restocking/adjusting is a separate explicit
    action so a price edit can never silently change how much stock exists.
    """
    assert_owns_product(product, company)

    pkg_fields = []
    if price is not None:
        product.base_price = price
        pkg_fields.append("base_price")
    if offer_price is not None:
        product.offer_price = offer_price
        pkg_fields.append("offer_price")
    if pkg_fields:
        product.save(update_fields=pkg_fields)

    if reorder_level_grams is None and restock_level_grams is None:
        return

    item = product.stock_item
    if not item:
        item = InventoryItem.objects.create(
            org=company,
            name=f"{product.name} (Produce)",
            category=InventoryItem.Category.CONSUMABLE,
            sku=f"VEG-{product.slug.upper()[:20]}",
            unit="g",
            total_quantity=0,
            available_quantity=0,
        )
        product.stock_item = item
        product.save(update_fields=["stock_item"])
    else:
        item = InventoryItem.objects.select_for_update().get(id=item.id)

    item_fields = []
    if reorder_level_grams is not None:
        item.reorder_threshold = reorder_level_grams
        item_fields.append("reorder_threshold")
    if restock_level_grams is not None:
        item.reorder_quantity = restock_level_grams
        item.default_daily_quantity_grams = restock_level_grams
        item_fields.extend(["reorder_quantity", "default_daily_quantity_grams"])
    if item_fields:
        item.save(update_fields=item_fields)
