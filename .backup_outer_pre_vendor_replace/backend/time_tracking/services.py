"""
time_tracking/services.py

Authoritative Service Layer for Shift Attendance & Time Tracking Lifecycle.
Provides idempotent auto clock-out and concurrency-safe TimeLog operations.
"""
import logging
from typing import Optional, Tuple
from django.db import transaction
from django.utils import timezone
from time_tracking.models import TimeLog

logger = logging.getLogger("workforce.time_tracking")


def close_employee_active_timelog(
    employee,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    address: str = "",
    notes: str = "Auto clock-out upon job completion",
) -> Tuple[Optional[TimeLog], bool]:
    """
    Authoritatively and idempotently closes any open TimeLog for the employee.
    
    Guarantees:
    - Atomicity & row locking via select_for_update().
    - Closes any in-progress Break records.
    - Sets clock_out, submitted_at, and status='submitted'.
    - Idempotent: If already clocked out, returns (last_log, False) without error.
    - Prevents duplicate TimeLog records.
    
    Returns:
        (timelog: Optional[TimeLog], was_closed: bool)
    """
    if not employee:
        return None, False

    emp_id = employee.pk if hasattr(employee, "pk") else employee
    now = timezone.now()

    with transaction.atomic():
        open_log = (
            TimeLog.objects
            .select_for_update()
            .filter(employee_id=emp_id, clock_out__isnull=True)
            .first()
        )
        if not open_log:
            last_log = (
                TimeLog.objects
                .filter(employee_id=emp_id)
                .order_by("-clock_out", "-created_at")
                .first()
            )
            return last_log, False

        # Close all active open breaks
        open_breaks = open_log.breaks.filter(break_end__isnull=True)
        for b in open_breaks:
            b.break_end = now
            b.save(update_fields=["break_end"])

        # Populate clock-out fields
        open_log.clock_out = now
        if lat is not None:
            try:
                open_log.clock_out_lat = float(lat)
            except (ValueError, TypeError):
                pass
        if lon is not None:
            try:
                open_log.clock_out_lon = float(lon)
            except (ValueError, TypeError):
                pass
        if address:
            open_log.clock_out_address = address
        if notes and not open_log.clock_out_notes:
            open_log.clock_out_notes = notes

        open_log.status = "submitted"
        open_log.submitted_at = now
        open_log.save(update_fields=[
            "clock_out",
            "clock_out_lat",
            "clock_out_lon",
            "clock_out_address",
            "clock_out_notes",
            "status",
            "submitted_at",
        ])

        logger.info(
            f"[AUTO_CLOCK_OUT_SUCCESS] employee_id={emp_id} timelog_id={open_log.id} clock_out={now.isoformat()}"
        )
        return open_log, True
