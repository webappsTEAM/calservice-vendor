"""
workforce_api/management/commands/process_seller_order_outbox.py

Management command to process and deliver pending SellerOrderStatusOutbox events
to the Customer marketplace webhook endpoint with retries and exponential backoff.
"""

import time
import logging
from django.core.management.base import BaseCommand
from workforce_api.services.seller_order_outbox import process_outbox_batch

logger = logging.getLogger("workforce_api.seller_order_outbox")


class Command(BaseCommand):
    help = "Processes pending Seller Order Status Outbox events and delivers them to the Customer app."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Maximum number of outbox events to process per sweep (default: 50).",
        )
        parser.add_argument(
            "--poll",
            action="store_true",
            help="Run continuously in a polling loop.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=5,
            help="Sleep interval in seconds when --poll is active (default: 5s).",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        poll = options["poll"]
        interval = options["interval"]

        self.stdout.write(self.style.NOTICE(f"[OUTBOX_WORKER] Starting outbox processor (batch_size={batch_size}, poll={poll})..."))

        if not poll:
            delivered, failed = process_outbox_batch(batch_size=batch_size)
            self.stdout.write(self.style.SUCCESS(f"[OUTBOX_WORKER] Completed sweep. Delivered: {delivered}, Failed/Retried: {failed}"))
            return

        try:
            while True:
                delivered, failed = process_outbox_batch(batch_size=batch_size)
                if delivered > 0 or failed > 0:
                    self.stdout.write(self.style.SUCCESS(f"[OUTBOX_WORKER] Processed sweep. Delivered: {delivered}, Failed/Retried: {failed}"))
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.NOTICE("[OUTBOX_WORKER] Stopped by user."))
