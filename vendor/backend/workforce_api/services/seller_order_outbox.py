"""
workforce_api/services/seller_order_outbox.py

Transactional event outbox for SellerOrder lifecycle state transitions.
Ensures reliable, ordered, at-least-once status notification delivery
from Vendor/Seller Hub to the Sevo-Customer marketplace backend.
"""

import os
import uuid
import logging
import threading
import requests
from datetime import timedelta
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings

from workforce_api.models import SellerOrder, SellerOrderStatusOutbox

logger = logging.getLogger("workforce_api.seller_order_outbox")

_WEBHOOK_TIMEOUT_SECONDS = 5
_BACKOFF_DELAYS_SECONDS = [15, 60, 300, 900, 3600]
_MAX_RETRY_ATTEMPTS = 5


def build_sanitized_order_payload(order, previous_status, new_status, actor=None, cancellation_source=None):
    """
    Constructs a customer-facing sanitized payload for a SellerOrder status transition.
    Strictly excludes internal notes, cost prices, inventory stock balances, or seller private metadata.
    """
    timestamps = {}
    if order.created_at:
        timestamps["created_at"] = order.created_at.isoformat()
    if order.accepted_at:
        timestamps["accepted_at"] = order.accepted_at.isoformat()
    if order.picking_at:
        timestamps["picking_at"] = order.picking_at.isoformat()
    if order.packed_at:
        timestamps["packed_at"] = order.packed_at.isoformat()
    if order.ready_at:
        timestamps["ready_at"] = order.ready_at.isoformat()
    if order.assigned_at:
        timestamps["assigned_at"] = order.assigned_at.isoformat()
    if order.handed_over_at:
        timestamps["handed_over_at"] = order.handed_over_at.isoformat()
    if order.delivered_at:
        timestamps["delivered_at"] = order.delivered_at.isoformat()
    if order.cancelled_at:
        timestamps["cancelled_at"] = order.cancelled_at.isoformat()
    if order.updated_at:
        timestamps["updated_at"] = order.updated_at.isoformat()

    cancelled_by_role = None
    if new_status == SellerOrder.Status.CANCELLED:
        if cancellation_source:
            cancelled_by_role = cancellation_source
        elif actor and getattr(actor, "is_authenticated", False):
            cancelled_by_role = "SELLER"
        else:
            cancelled_by_role = "INTEGRATION"

    rider_info = None
    if order.handling_technician:
        tech = order.handling_technician
        user = getattr(tech, "user", None)
        rider_info = {
            "id": tech.id,
            "name": (user.get_full_name() or user.username) if user else getattr(tech, "name", f"Rider #{tech.id}"),
            "phone": getattr(user, "mobile_number", "") or getattr(user, "phone", "") or getattr(tech, "phone", "") if user else getattr(tech, "phone", ""),
        }

    return {
        "source_order_id": order.source_order_id,
        "vendor_order_number": order.order_number,
        "vendor_order_id": order.id,
        "seller_id": order.company_id,
        "seller_name": getattr(order.company, "company_name", ""),
        "previous_status": previous_status,
        "current_status": new_status,
        "fulfillment_type": order.fulfillment_type,
        "delivery_slot": order.delivery_slot or "",
        "handover_ref": order.handover_ref or "",
        "dispatch_job_id": order.dispatch_job_id,
        "rider": rider_info,
        "cancellation_reason": order.cancellation_reason if new_status == SellerOrder.Status.CANCELLED else None,
        "cancelled_by": cancelled_by_role,
        "timestamps": timestamps,
    }


_outbox_table_available = None


def _is_outbox_table_available():
    global _outbox_table_available
    if _outbox_table_available is not None:
        return _outbox_table_available
    try:
        from django.db import connection
        tables = connection.introspection.table_names()
        _outbox_table_available = "workforce_seller_order_status_outbox" in tables
        return _outbox_table_available
    except Exception:
        return True


def record_seller_order_status_event(
    order,
    previous_status,
    new_status,
    event_type="seller_order.status_updated",
    actor=None,
    cancellation_source=None,
    trigger_immediate=True,
):
    """
    Records an outbox event INSIDE the calling atomic database transaction.
    Must be called alongside the SellerOrder status update.
    Calculates monotonically increasing per-order sequence.
    """
    if not order or not order.source_order_id:
        return None

    if not _is_outbox_table_available():
        logger.warning("Outbox table 'workforce_seller_order_status_outbox' not yet migrated on database; skipping outbox insert.")
        return None

    import django.db.utils

    try:
        # Calculate next sequence number for this specific order
        max_seq = SellerOrderStatusOutbox.objects.filter(order=order).aggregate(
            m=models.Max("sequence")
        )["m"]
        sequence = (max_seq or 0) + 1

        event_id = f"evt_{uuid.uuid4().hex}"
        payload = build_sanitized_order_payload(
            order=order,
            previous_status=previous_status,
            new_status=new_status,
            actor=actor,
            cancellation_source=cancellation_source,
        )

        outbox_event = SellerOrderStatusOutbox.objects.create(
            event_id=event_id,
            source_order_id=order.source_order_id,
            order=order,
            sequence=sequence,
            previous_status=previous_status,
            new_status=new_status,
            event_type=event_type,
            payload=payload,
            status=SellerOrderStatusOutbox.DeliveryStatus.PENDING,
        )

        if trigger_immediate:
            event_pk = outbox_event.pk
            transaction.on_commit(lambda: _trigger_background_dispatch(event_pk))

        return outbox_event
    except (django.db.utils.ProgrammingError, django.db.utils.OperationalError) as exc:
        logger.warning("Outbox table not yet migrated or inaccessible: %s", exc)
        return None


def _trigger_background_dispatch(event_pk):
    """
    Launches a daemon thread to attempt immediate outbox delivery after commit.
    """
    if os.environ.get("SEVO_E2E_SQLITE_PATH"):
        return

    def _run():
        try:
            event_obj = SellerOrderStatusOutbox.objects.filter(pk=event_pk).first()
            if event_obj and event_obj.status == SellerOrderStatusOutbox.DeliveryStatus.PENDING:
                deliver_outbox_event(event_obj)
        except Exception as exc:
            logger.info("Background dispatch attempt for outbox event %s failed: %s", event_pk, exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def deliver_outbox_event(event_obj):
    """
    Delivers a single outbox event to the Customer app endpoint via HTTP POST.
    Reuses WORKFORCE_WEBHOOK_SECRET authentication contract.
    Updates delivery status, retry backoff timestamp, and error logs safely.
    """
    base_url = getattr(settings, "CUSTOMER_APP_BASE_URL", None) or os.environ.get("CUSTOMER_APP_BASE_URL")
    if not base_url:
        logger.error("CUSTOMER_APP_BASE_URL is unset; defaulting to fallback http://127.0.0.1:8000")
        base_url = "http://127.0.0.1:8000"

    url = f"{base_url.rstrip('/')}/api/workforce-integration/webhook/"
    body = {
        "event": event_obj.event_type,
        "event_id": event_obj.event_id,
        "sequence": event_obj.sequence,
        "payload": event_obj.payload,
    }

    secret = getattr(settings, "WORKFORCE_WEBHOOK_SECRET", "")
    headers = {
        "Content-Type": "application/json",
        "X-Workforce-Webhook-Secret": secret,
    }

    now = timezone.now()
    try:
        response = requests.post(
            url,
            json=body,
            headers=headers,
            timeout=_WEBHOOK_TIMEOUT_SECONDS,
        )

        if 200 <= response.status_code < 300:
            event_obj.status = SellerOrderStatusOutbox.DeliveryStatus.DELIVERED
            event_obj.delivered_at = now
            event_obj.last_error = ""
            event_obj.next_retry_at = None
            event_obj.save(update_fields=["status", "delivered_at", "last_error", "next_retry_at"])
            logger.info(
                "Delivered outbox event '%s' (order %s, seq %s, status %s).",
                event_obj.event_id, event_obj.source_order_id, event_obj.sequence, event_obj.new_status
            )
            return True
        else:
            err_msg = f"HTTP {response.status_code}: {response.text[:300]}"
            _record_delivery_failure(event_obj, err_msg, now, unrecoverable=(response.status_code in (400, 422)))
            return False

    except Exception as exc:
        err_msg = f"Delivery exception: {str(exc)}"
        _record_delivery_failure(event_obj, err_msg, now, unrecoverable=False)
        return False


def _record_delivery_failure(event_obj, error_message, now, unrecoverable=False):
    """
    Computes exponential backoff or marks FAILED if max retries exceeded or unrecoverable error.
    """
    event_obj.retry_count += 1
    event_obj.last_error = error_message

    if unrecoverable or event_obj.retry_count >= _MAX_RETRY_ATTEMPTS:
        event_obj.status = SellerOrderStatusOutbox.DeliveryStatus.FAILED
        event_obj.next_retry_at = None
        logger.warning(
            "Outbox event '%s' for order %s failed permanently: %s",
            event_obj.event_id, event_obj.source_order_id, error_message
        )
    else:
        delay_idx = min(event_obj.retry_count - 1, len(_BACKOFF_DELAYS_SECONDS) - 1)
        delay_sec = _BACKOFF_DELAYS_SECONDS[delay_idx]
        event_obj.next_retry_at = now + timedelta(seconds=delay_sec)
        logger.warning(
            "Outbox event '%s' for order %s failed attempt %d: %s (next retry in %ds)",
            event_obj.event_id, event_obj.source_order_id, event_obj.retry_count, error_message, delay_sec
        )

    event_obj.save(update_fields=["retry_count", "last_error", "status", "next_retry_at"])


def process_outbox_batch(batch_size=50):
    """
    Durable worker sweep: finds PENDING outbox records due for delivery and processes them.
    Returns (delivered_count, failed_count).
    """
    now = timezone.now()
    qs = SellerOrderStatusOutbox.objects.filter(
        status=SellerOrderStatusOutbox.DeliveryStatus.PENDING
    ).filter(
        models.Q(next_retry_at__isnull=True) | models.Q(next_retry_at__lte=now)
    ).order_by("created_at")[:batch_size]

    delivered = 0
    failed = 0
    for evt in qs:
        success = deliver_outbox_event(evt)
        if success:
            delivered += 1
        else:
            failed += 1

    return delivered, failed
