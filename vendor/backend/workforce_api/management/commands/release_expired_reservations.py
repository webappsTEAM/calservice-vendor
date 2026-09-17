"""
Django Management Command: release_expired_reservations
Finds Grocery Orders pending payment exceeding the 15-minute window and automatically
releases reserved inventory back to available stock, logging immutable audit entries.
"""
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from workforce_api.models import GroceryOrder, InventoryTransaction


class Command(BaseCommand):
    help = "Releases reserved grocery stock for orders in PENDING_PAYMENT exceeding 15 minutes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout-minutes",
            type=int,
            default=15,
            help="Minutes after which unconfirmed reservations are expired (default: 15).",
        )

    def handle(self, *args, **options):
        timeout = options["timeout_minutes"]
        cutoff = timezone.now() - timedelta(minutes=timeout)

        expired_orders = GroceryOrder.objects.filter(
            status=GroceryOrder.Status.PENDING_PAYMENT,
            placed_at__lt=cutoff,
        ).select_related("vendor_store").prefetch_related("items__inventory_item")

        count = expired_orders.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS(f"No expired reservations found (Cutoff: {cutoff.isoformat()})."))
            return

        self.stdout.write(f"Found {count} expired order reservations. Releasing stock...")

        released_orders = 0
        for order in expired_orders:
            with transaction.atomic():
                # Re-verify order status in transaction
                order.refresh_from_db()
                if order.status != GroceryOrder.Status.PENDING_PAYMENT:
                    continue

                order.status = GroceryOrder.Status.CANCELLED
                order.cancelled_at = timezone.now()
                order.rejection_reason = f"Payment window expired ({timeout} minutes timeout)."
                order.save(update_fields=["status", "cancelled_at", "rejection_reason", "updated_at"])

                # Release reserved stock for each line item
                for item in order.items.all():
                    inv = item.inventory_item
                    if inv:
                        inv.reserved_quantity = max(
                            Decimal("0.000"),
                            (inv.reserved_quantity or Decimal("0.000")) - item.quantity,
                        )
                        inv.save(update_fields=["reserved_quantity", "updated_at"])

                        InventoryTransaction.objects.create(
                            inventory_item=inv,
                            transaction_type=InventoryTransaction.TransactionType.RESERVATION_RELEASE,
                            quantity=item.quantity,
                            balance_after=inv.available_quantity,
                            reference_id=order.order_number,
                            notes=f"Auto-released: 15-min reservation timeout on Order #{order.order_number}",
                        )

                released_orders += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully released stock for {released_orders} expired orders."))
