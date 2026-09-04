"""
workforce_api/services/customer_webhook.py

Fixes X-01: nothing on the vendor side ever notified the Customer app of
technician lifecycle events, even though the Customer app has a fully-built
idempotent webhook receiver (workforce_integration/views.py,
WorkforceWebhookEvent model) sitting there unused. This module is the
sender half of that contract.

Design notes:
  - Fire-and-forget: runs the actual HTTP POST in a background thread with a
    short timeout, and every call site wraps its own state change (already
    committed before this fires) so a webhook failure NEVER undoes or blocks
    a real vendor-side action. Mirrors how the Customer app's own
    WorkforceIntegrationService.dispatch_job() call was made non-blocking in
    the same pass (see BookingCreateView, X-02).
  - Matches the Customer app's expected payload shape exactly (see
    workforce_integration/views.py: `event`, `event_id`, `sequence`,
    `payload.booking_id` and friends) so no receiver-side changes are
    needed.
  - `booking_id` is always the ServiceRequest.request_id (e.g. "HM0001"),
    not the numeric pk, since that is what the receiver looks up first.
"""
import logging
import threading
import time
import uuid

import requests
from django.conf import settings

logger = logging.getLogger("workforce_api.customer_webhook")

_WEBHOOK_TIMEOUT_SECONDS = 4


def _post_webhook(event_type, booking_id, payload, sequence):
    url = f"{settings.CUSTOMER_APP_BASE_URL}/api/workforce-integration/webhook/"
    body = {
        "event": event_type,
        "event_id": f"evt_{uuid.uuid4().hex}",
        "sequence": sequence,
        "payload": {"booking_id": booking_id, **payload},
    }
    try:
        response = requests.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Workforce-Webhook-Secret": settings.WORKFORCE_WEBHOOK_SECRET,
            },
            timeout=_WEBHOOK_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            logger.warning(
                "Customer webhook '%s' for booking %s rejected: %s %s",
                event_type, booking_id, response.status_code, response.text[:300],
            )
        else:
            logger.info("Customer webhook '%s' for booking %s delivered.", event_type, booking_id)
    except Exception as exc:
        # Never let a delivery failure surface to the caller -- this always
        # runs on a background thread already, but stay defensive in case
        # someone calls _post_webhook directly.
        logger.info("Customer webhook '%s' for booking %s failed to deliver: %s", event_type, booking_id, exc)


def notify_customer_app(event_type, service_request, **extra_payload):
    """
    Fire a webhook event to the Customer app for `service_request`.
    Safe to call from anywhere -- never raises, never blocks the caller
    beyond starting a thread.

    `event_type` must be one of the strings workforce_integration/views.py
    recognizes (see the event_type-dispatch table there), e.g.
    "employee_accepted", "employee_on_the_way", "employee_arrived",
    "service_started", "service_completed", "technician.location_updated",
    "payment.collected", "technician.assigned".
    """
    try:
        booking_id = getattr(service_request, "request_id", None) or str(getattr(service_request, "id", ""))
        if not booking_id:
            return

        sequence = int(time.time() * 1000) % 2_147_483_647  # monotonic-enough, fits a 32-bit int column

        payload = dict(extra_payload)
        payload.setdefault("workforce_job_id", str(getattr(service_request, "id", "")))
        payload.setdefault("company_id", str(getattr(service_request, "company_id", "") or ""))

        thread = threading.Thread(
            target=_post_webhook,
            args=(event_type, booking_id, payload, sequence),
            daemon=True,
        )
        thread.start()
    except Exception as exc:
        logger.info("Could not start customer webhook thread for event '%s': %s", event_type, exc)
