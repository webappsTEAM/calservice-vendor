"""
Multi-Vendor Grocery Pricing Service
Server-authoritative calculation for item prices, active deals, store coupons, delivery fees, and order totals.
"""
from decimal import Decimal
from django.utils import timezone
from workforce_api.models import InventoryItem, VendorDeal, VendorCoupon, CouponRedemption


class GroceryPricingService:

    @staticmethod
    def calculate_item_offer(inventory_item: InventoryItem, quantity=Decimal("1.0")):
        """
        Computes the effective unit price, MRP, deal discount, and total for an inventory item offer.
        """
        quantity = Decimal(str(quantity))
        regular_price = inventory_item.custom_price or Decimal("0.00")
        mrp = inventory_item.mrp or regular_price

        # Check for active deals
        now = timezone.now()
        active_deal = (
            VendorDeal.objects.filter(inventory_item=inventory_item, is_active=True)
            .filter(
                (django_db_models_Q(deal_start_at__isnull=True) | django_db_models_Q(deal_start_at__lte=now)) &
                (django_db_models_Q(deal_end_at__isnull=True) | django_db_models_Q(deal_end_at__gte=now))
            )
            .first()
        )

        final_unit_price = regular_price
        deal_info = None

        if active_deal and active_deal.deal_price < regular_price:
            final_unit_price = active_deal.deal_price
            deal_info = {
                "deal_id": active_deal.id,
                "deal_type": active_deal.deal_type,
                "badge_text": active_deal.badge_text or f"{active_deal.discount_percent}% OFF",
                "deal_price": float(active_deal.deal_price),
                "original_price": float(active_deal.original_price),
                "discount_percent": active_deal.discount_percent,
            }

        line_total = final_unit_price * quantity
        deal_savings = (regular_price - final_unit_price) * quantity if deal_info else Decimal("0.00")

        return {
            "inventory_item_id": inventory_item.id,
            "product_name": inventory_item.display_name,
            "sku": inventory_item.catalogue_service_id or f"ITEM-{inventory_item.id}",
            "unit": inventory_item.unit,
            "quantity": float(quantity),
            "mrp": float(mrp),
            "regular_unit_price": float(regular_price),
            "final_unit_price": float(final_unit_price),
            "line_total": float(line_total),
            "deal_savings": float(deal_savings),
            "deal": deal_info,
        }

    @staticmethod
    def validate_and_apply_coupon(store, coupon_code, subtotal, customer_id=None):
        """
        Validates a store-scoped or platform coupon and calculates the discount.
        """
        if not coupon_code:
            return None, Decimal("0.00"), None

        now = timezone.now()
        coupon = VendorCoupon.objects.filter(
            company=store.company,
            code__iexact=coupon_code.strip(),
            is_active=True,
        ).first()

        if not coupon:
            return False, Decimal("0.00"), "Invalid or expired coupon code for this store."

        # Date validity
        if coupon.valid_from and coupon.valid_from > now:
            return False, Decimal("0.00"), "Coupon is not active yet."
        if coupon.valid_until and coupon.valid_until < now:
            return False, Decimal("0.00"), "Coupon has expired."

        # Min order amount
        if subtotal < coupon.min_order_amount:
            return False, Decimal("0.00"), f"Minimum order amount of ₹{coupon.min_order_amount} required to use this coupon."

        # Global usage limit
        if coupon.usage_limit_total and coupon.times_used >= coupon.usage_limit_total:
            return False, Decimal("0.00"), "Coupon usage limit has been reached."

        # Per customer usage limit
        if customer_id and coupon.usage_limit_per_user:
            used_count = CouponRedemption.objects.filter(coupon=coupon, customer_id=customer_id).count()
            if used_count >= coupon.usage_limit_per_user:
                return False, Decimal("0.00"), "You have already used this coupon maximum allowed times."

        # Compute discount
        if coupon.discount_type == VendorCoupon.DiscountType.PERCENT:
            discount = (subtotal * coupon.discount_value) / Decimal("100.00")
            if coupon.max_discount_amount:
                discount = min(discount, coupon.max_discount_amount)
        else:
            discount = min(coupon.discount_value, subtotal)

        discount = round(discount, 2)
        return coupon, discount, None

    @classmethod
    def calculate_order_summary(cls, store, cart_items, coupon_code=None, customer_id=None, delivery_distance_km=0.0):
        """
        Calculates the complete order price snapshot including subtotal, deal savings,
        coupons, delivery fees, and final grand total.
        """
        subtotal = Decimal("0.00")
        total_deal_savings = Decimal("0.00")
        line_items_output = []

        for item in cart_items:
            inv = item["inventory_item"]
            qty = Decimal(str(item["quantity"]))
            calc = cls.calculate_item_offer(inv, qty)
            subtotal += Decimal(str(calc["line_total"]))
            total_deal_savings += Decimal(str(calc["deal_savings"]))
            line_items_output.append(calc)

        # Coupon calculation
        coupon_obj, coupon_discount, coupon_error = cls.validate_and_apply_coupon(
            store=store,
            coupon_code=coupon_code,
            subtotal=subtotal,
            customer_id=customer_id,
        )

        # Delivery fee calculation (Standard: ₹25 if subtotal < ₹200, free otherwise)
        delivery_fee = Decimal("0.00")
        if subtotal < Decimal("200.00") and subtotal > Decimal("0.00"):
            delivery_fee = Decimal("25.00")

        # Tax calculation (Produce: HSN 0701-0714 fresh vegetables 0% GST; Logistics: 18% GST on delivery fee)
        # Displayed product prices are GST-inclusive.
        delivery_taxable = round(delivery_fee / Decimal("1.18"), 2) if delivery_fee > Decimal("0.00") else Decimal("0.00")
        delivery_tax = delivery_fee - delivery_taxable
        cgst = round(delivery_tax / Decimal("2.0"), 2)
        sgst = delivery_tax - cgst
        tax = Decimal("0.00")  # Since delivery fee of ₹25 is inclusive of 18% GST

        total_amount = max(Decimal("0.00"), subtotal - coupon_discount + delivery_fee + tax)

        tax_breakdown = {
            "is_inclusive": True,
            "taxable_amount": float(subtotal - coupon_discount + delivery_taxable),
            "cgst": float(cgst),
            "sgst": float(sgst),
            "igst": 0.0,
            "total_tax": float(delivery_tax),
            "hsn_summary": [
                {"hsn_code": "0701-0714", "description": "Fresh Vegetables (Exempt)", "rate_percent": 0.0, "amount": float(subtotal - coupon_discount)},
                {"hsn_code": "9968", "description": "Logistics & Delivery (18% GST Incl)", "rate_percent": 18.0, "amount": float(delivery_fee)},
            ]
        }

        return {
            "vendor_store_id": store.id,
            "vendor_store_name": store.store_name,
            "subtotal": float(subtotal),
            "deal_discount": float(total_deal_savings),
            "coupon_discount": float(coupon_discount),
            "coupon_code": coupon_obj.code if coupon_obj else (coupon_code if not coupon_error else None),
            "coupon_error": coupon_error,
            "delivery_fee": float(delivery_fee),
            "tax": float(tax),
            "tax_breakdown": tax_breakdown,
            "total_amount": float(total_amount),
            "items": line_items_output,
        }


# Helper for Q query without import cycles
from django.db.models import Q as django_db_models_Q
