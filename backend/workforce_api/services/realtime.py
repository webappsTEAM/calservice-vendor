"""
workforce_api/services/realtime.py

Authoritative Realtime Abstraction Layer for CalTrack Workforce.
Maintains PostgreSQL as the durable source of truth for all events and telemetry.
Provides a Redis-ready publishing interface for location updates and lifecycle events.
If Redis is unavailable or unconfigured, all operations gracefully succeed using PostgreSQL.
"""
import json
import logging
import os
import time
from typing import Optional, Dict, Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("workforce.realtime")

_redis_client = None
_redis_last_failure: float = 0.0
_REDIS_RETRY_INTERVAL_SECONDS: float = 3.0


def get_redis_client():
    """
    Returns a configured, live Redis client if available and reachable, or None.
    Caches connection and performs quick liveness check.
    If Redis fails, throttles reconnection attempts to once every 3 seconds so
    unavailable Redis does not add latency to API requests.
    Automatically reconnects when Redis recovers.
    """
    global _redis_client, _redis_last_failure
    now = time.time()

    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception as conn_err:
            logger.warning(f"[REDIS_CONN_LOST] Redis connection lost: {conn_err}. Falling back to PostgreSQL.")
            _redis_client = None
            _redis_last_failure = now
            return None

    # Throttle connection attempts after a failure
    if now - _redis_last_failure < _REDIS_RETRY_INTERVAL_SECONDS:
        return None

    redis_url = getattr(settings, "REDIS_URL", None) or os.getenv("REDIS_URL")
    if not redis_url:
        return None

    try:
        import redis
        client = redis.from_url(
            redis_url,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
            decode_responses=False,
        )
        client.ping()
        _redis_client = client
        _redis_last_failure = 0.0
        logger.info("[REDIS_REALTIME] Connected to Redis realtime layer.")
        return _redis_client
    except Exception as e:
        _redis_last_failure = now
        logger.debug(f"[REDIS_REALTIME_UNAVAILABLE] Redis is not available, falling back to PostgreSQL durable state: {e}")
        _redis_client = None
        return None


def set_job_current_location(job_id: int, payload: Dict[str, Any], ttl: int = 300) -> bool:
    """
    Sets the fast current-location state in Redis for an active job.
    Key structure: job_location:<job_id>
    TTL defaults to 300 seconds (5 minutes).
    Returns True if stored successfully in Redis, False otherwise.
    Redis failure is logged and does not raise an exception.
    """
    if not job_id:
        return False

    client = get_redis_client()
    if not client:
        return False

    try:
        key = f"job_location:{job_id}"
        message = json.dumps(payload, default=str)
        client.set(key, message, ex=ttl)
        logger.debug(f"[REDIS_SET_LOCATION] Stored current location for Job #{job_id} (TTL={ttl}s).")
        return True
    except Exception as err:
        logger.warning(f"[REDIS_SET_LOCATION_FAIL] Failed to set current location for Job #{job_id}: {err}")
        return False


def get_job_current_location(job_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves the fast current-location snapshot from Redis for a job.
    Returns parsed dictionary or None if not found, expired, or Redis is down.
    """
    if not job_id:
        return None

    client = get_redis_client()
    if not client:
        return None

    try:
        key = f"job_location:{job_id}"
        raw_val = client.get(key)
        if raw_val is None:
            return None
        if isinstance(raw_val, bytes):
            raw_val = raw_val.decode("utf-8")
        return json.loads(raw_val)
    except Exception as err:
        logger.warning(f"[REDIS_GET_LOCATION_FAIL] Failed to get current location for Job #{job_id}: {err}")
        return None


def publish_job_location_update(
    job_id: int,
    payload: Dict[str, Any],
    user=None,
    persist_db: bool = True
) -> Optional[Any]:
    """
    Publishes live technician GPS telemetry for an active job.
    1. Updates fast Redis current location: job_location:<job_id> (TTL 300s).
    2. Broadcasts via transient Redis PubSub channel: 'job_tracking:<job_id>'.
    3. Persists durable event in PostgreSQL (WorkforceEventLog) ONLY when persist_db is True.
    """
    from workforce_api.models import WorkforceEventLog

    # 1. Fast Redis Current State & Realtime PubSub
    set_job_current_location(job_id, payload, ttl=300)

    client = get_redis_client()
    if client:
        try:
            channel = f"job_tracking:{job_id}"
            message = json.dumps(payload, default=str)
            client.publish(channel, message)
        except Exception as r_err:
            logger.debug(f"[REDIS_PUBLISH_FAIL] Failed to publish to Redis channel: {r_err}")

    # 2. PostgreSQL Durable State (Throttled)
    event_log = None
    if persist_db:
        try:
            event_log = WorkforceEventLog.objects.create(
                user=user,
                event_type="JOB_LOCATION_UPDATE",
                payload=payload,
            )
        except Exception as db_err:
            logger.error(f"[REALTIME_DB_EVENT_ERROR] Failed to persist location event for Job #{job_id}: {db_err}")

    return event_log


def publish_workforce_event(
    event_type: str,
    payload: Dict[str, Any],
    user=None,
    company=None,
    ip_address: str = ""
) -> Optional[Any]:
    """
    Publishes authoritative workforce lifecycle events:
    JOB_OFFERED, JOB_ACCEPTED, JOB_ARRIVED, JOB_IN_PROGRESS,
    JOB_PROOF_SUBMITTED, PAYMENT_COLLECTED, JOB_COMPLETED,
    EMPLOYEE_AVAILABILITY_CHANGED, etc.
    """
    from workforce_api.models import WorkforceEventLog

    event_log = None
    try:
        event_log = WorkforceEventLog.objects.create(
            user=user,
            event_type=event_type,
            payload=payload,
            ip_address=ip_address,
        )
    except Exception as db_err:
        logger.error(f"[REALTIME_EVENT_LOG_ERROR] Failed to persist event '{event_type}': {db_err}")

    client = get_redis_client()
    if client:
        try:
            channel = f"workforce_events:{event_type}"
            message = json.dumps(payload, default=str)
            client.publish(channel, message)
            if company:
                client.publish(f"company_events:{company.id if hasattr(company, 'id') else company}", message)
        except Exception as r_err:
            logger.debug(f"[REDIS_EVENT_PUBLISH_FAIL] Failed to publish workforce event: {r_err}")

    return event_log
