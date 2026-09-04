"""
workforce_api/services/logistics_events.py

The driver-side half of the Goods & Transport lifecycle contract.

The Customer app consumes four logistics events -- `logistics.leg_changed`,
`trip.stop_arrived`, `trip.stop_completed` and a rich
`job.completion_proof_submitted`. This module is where the vendor side
emits them, and where the leg-progression rules live, so the views stay
thin (CLAUDE.md: business logic never in views).

Why events at all, when both apps share one database?
Leg and stop columns live on the shared ServiceRequest/TripStop tables, so
a customer polling their tracking endpoint would eventually see a change
written here regardless. The webhook adds the two things a shared column
cannot: an immediate WebSocket broadcast to a customer watching the map
right now, and the Customer app's own side effects (proof records,
recipient notification, fare reconciliation). Emission is fire-and-forget
via notify_customer_app(), so a webhook failure never blocks or undoes the
driver's action -- the shared row is still correct either way. That makes
the webhook an enhancement over the shared table, not a single point of
failure for it.

The driver-visible trip flow this supports:

    accept -> EN_ROUTE_PICKUP -> (arrive at pickup stop) -> LOADING
           -> EN_ROUTE_DROP -> (arrive at drop stop) -> UNLOADING
           -> proof of delivery -> DELIVERED
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

# Forward-only ordering for the trip. Index position is the rule: a leg may
# be repeated (idempotent) or skipped forward (a driver who never signals
# LOADING should not be blocked from signalling EN_ROUTE_DROP), but never
# moved backwards -- a trip that has reached DELIVERED cannot claim to be
# EN_ROUTE_PICKUP again, and accepting that would corrupt both the customer's
# tracking view and the leg audit trail.
LEG_SEQUENCE = [
    "EN_ROUTE_PICKUP",
    "LOADING",
    "EN_ROUTE_DROP",
    "UNLOADING",
    "DELIVERED",
]


def leg_rank(leg):
    """Position of `leg` in the trip, or -1 for a blank/unknown value."""
    try:
        return LEG_SEQUENCE.index(leg)
    except ValueError:
        return -1


def can_advance_to(current_leg, target_leg):
    """
    (allowed, reason). Forward-only; repeats are allowed and handled as
    no-ops by the caller so a retried request stays idempotent.
    """
    if target_leg not in LEG_SEQUENCE:
        return False, f"Invalid leg '{target_leg}'. Choose one of: {', '.join(LEG_SEQUENCE)}"
    if not current_leg:
        return True, ""
    if leg_rank(target_leg) < leg_rank(current_leg):
        return False, (
            f"Cannot move the trip backwards from '{current_leg}' to '{target_leg}'."
        )
    return True, ""


def set_logistics_leg(job, leg, actor=None):
    """
    Advance a job's logistics leg on the shared ServiceRequest row and tell
    the Customer app.

    Returns (changed, error). `changed` is False for an idempotent repeat of
    the leg the job is already on -- not an error, since the driver app may
    retry. `error` is a message when the move was rejected.

    Mirrors ServiceRequest.set_logistics_leg() in the Customer app: same
    append-only history shape ({"leg", "at", "by"}), same idempotency. The
    two implementations are separate because this app's ServiceRequest is an
    unmanaged mirror model without the Customer app's methods, which is the
    established pattern for every shared table here.
    """
    leg = (leg or "").strip().upper()
    allowed, reason = can_advance_to(job.logistics_leg, leg)
    if not allowed:
        return False, reason

    if job.logistics_leg == leg:
        return False, ""

    now = timezone.now()
    history = list(job.logistics_leg_history or [])
    history.append({
        "leg": leg,
        "at": now.isoformat(),
        "by": getattr(actor, "id", None),
    })
    job.logistics_leg = leg
    job.logistics_leg_updated_at = now
    job.logistics_leg_history = history
    job.save(update_fields=[
        "logistics_leg", "logistics_leg_updated_at", "logistics_leg_history", "updated_at",
    ])

    emit_leg_changed(job, leg)
    return True, ""


def emit_leg_changed(job, leg):
    try:
        from workforce_api.services.customer_webhook import notify_customer_app
        notify_customer_app("logistics.leg_changed", job, leg=leg)
    except Exception as exc:
        logger.info("Could not emit logistics.leg_changed for job %s: %s", job.id, exc)


def emit_stop_progress(job, stop, completed):
    event = "trip.stop_completed" if completed else "trip.stop_arrived"
    try:
        from workforce_api.services.customer_webhook import notify_customer_app
        notify_customer_app(
            event, job,
            stop_id=stop.id,
            stop_sequence=stop.sequence,
            stop_type=stop.stop_type,
            completed=bool(completed),
        )
    except Exception as exc:
        logger.info("Could not emit %s for job %s: %s", event, job.id, exc)


def record_stop_progress(job, stop, completed, actor=None):
    """
    Mark a stop arrived (and optionally completed) on the shared table, then
    tell the Customer app.

    Idempotent in the way that matters: an existing timestamp is never
    rewritten, so a retried request cannot drag the trip timeline forward.
    A completion for a stop whose arrival was never reported still produces
    a coherent timeline rather than a half-filled row.
    """
    now = timezone.now()
    fields = []
    if stop.arrived_at is None:
        stop.arrived_at = now
        fields.append("arrived_at")
    if completed and stop.completed_at is None:
        stop.completed_at = now
        fields.append("completed_at")

    if fields:
        stop.save(update_fields=fields)

    # Emit even on a no-op save: the customer's app may have missed the
    # first delivery, and the receiver is itself idempotent.
    emit_stop_progress(job, stop, completed)
    return bool(fields)


def emit_completion_proof(job, *, notes="", photo_url="", signature_url="",
                          recipient_name="", recipient_phone="", stop=None,
                          otp_verified=False, technician_name="",
                          workforce_employee_id="", location=None):
    """
    The rich `job.completion_proof_submitted` payload.

    Previously this event carried only free-text remarks, and the Customer
    app could do nothing with it but append them to the booking description.
    It now carries the actual evidence, which is what the receiver turns
    into DeliveryProof rows.

    Image references are passed as URLs into this app's own media storage
    rather than re-uploading the bytes: the Customer app deliberately stores
    the reference it is given instead of pulling someone else's file into its
    media root from inside a webhook handler.
    """
    payload = {
        "notes": notes or "",
        "otp_verified": bool(otp_verified),
        "technician_name": technician_name or "",
        "workforce_employee_id": str(workforce_employee_id or ""),
    }
    if photo_url:
        payload["photo_url"] = photo_url
    if signature_url:
        payload["signature_url"] = signature_url
    if recipient_name:
        payload["recipient_name"] = recipient_name
    if recipient_phone:
        payload["recipient_phone"] = recipient_phone
    if stop is not None:
        payload["stop_id"] = stop.id
        payload["stop_sequence"] = stop.sequence
    if location:
        payload["location"] = location

    try:
        from workforce_api.services.customer_webhook import notify_customer_app
        notify_customer_app("job.completion_proof_submitted", job, **payload)
    except Exception as exc:
        logger.info("Could not emit job.completion_proof_submitted for job %s: %s", job.id, exc)


def absolute_media_url(request, file_field):
    """
    Build an absolute URL for an uploaded proof file, so the Customer app
    stores a reference it can actually resolve. Returns "" when there is no
    file -- callers omit the key entirely in that case.
    """
    try:
        if not file_field:
            return ""
        url = file_field.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    except Exception:
        return ""
