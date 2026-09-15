"""
backend/workforce_api/services/redis_dispatch.py

Authoritative Redis Dispatch Coordination & Candidate Discovery Layer.
Maintains PostgreSQL/Supabase as the single source of truth for all business rules,
eligibility gates, wave progressions, offer state machines, and job assignments.

Redis Responsibilities:
1. Candidate Discovery: Fast geospatial indexing of online available technicians (workforce:technicians:geo).
2. Reliable Queue: Durable Redis Streams (workforce:dispatch:jobs) with consumer groups (workforce:dispatch:workers).
3. Stale Location Pruning: Enforces DISPATCH_LOCATION_MAX_AGE_SECONDS (default 120s) via last-seen timestamps.
4. Graceful Degradation: If Redis is down, returns None to allow bounded single-job PostgreSQL fallback without dropping jobs.
"""
import logging
import os
import time
from typing import Optional, List, Dict, Any, Tuple

from django.conf import settings
from django.utils import timezone

from workforce_api.services.realtime import get_redis_client

logger = logging.getLogger("workforce.dispatch.redis")

# Configuration with safe defaults
REDIS_GEO_KEY = getattr(settings, "REDIS_GEO_KEY", "workforce:technicians:geo")
REDIS_TECH_LAST_SEEN_KEY = getattr(settings, "REDIS_TECH_LAST_SEEN_KEY", "workforce:technicians:last_seen")
REDIS_DISPATCH_STREAM = getattr(settings, "REDIS_DISPATCH_STREAM", "workforce:dispatch:jobs")
REDIS_DISPATCH_GROUP = getattr(settings, "REDIS_DISPATCH_GROUP", "workforce:dispatch:workers")

DISPATCH_LOCATION_MAX_AGE_SECONDS = int(
    getattr(settings, "DISPATCH_LOCATION_MAX_AGE_SECONDS", 120)
)
DISPATCH_CANDIDATE_RADIUS_KM = float(
    getattr(settings, "DISPATCH_CANDIDATE_RADIUS_KM", 20.0)
)


def update_technician_dispatch_geo(
    employee_id: int,
    latitude: float,
    longitude: float,
    is_eligible: bool = True
) -> bool:
    """
    Updates a technician's coordinates in the Redis GEO candidate index.
    If is_eligible is True (active, online, available, and no active job),
    adds the technician to the GEO index and updates their last-seen timestamp.
    If is_eligible is False, removes the technician from the GEO index.
    """
    if not employee_id:
        return False

    client = get_redis_client()
    if not client:
        return False

    member = f"employee:{employee_id}"
    try:
        if is_eligible:
            # Redis GEO coordinates: (longitude, latitude, member)
            client.geoadd(REDIS_GEO_KEY, (float(longitude), float(latitude), member))
            client.hset(REDIS_TECH_LAST_SEEN_KEY, str(employee_id), str(int(time.time())))
            logger.debug(f"[REDIS_GEO_ADD] Employee #{employee_id} added to GEO index ({latitude}, {longitude}).")
        else:
            client.zrem(REDIS_GEO_KEY, member)
            client.hdel(REDIS_TECH_LAST_SEEN_KEY, str(employee_id))
            logger.debug(f"[REDIS_GEO_REM] Ineligible Employee #{employee_id} removed from GEO index.")
        return True
    except Exception as err:
        logger.warning(f"[REDIS_GEO_UPDATE_FAIL] Failed updating GEO for Employee #{employee_id}: {err}")
        return False


def remove_technician_from_dispatch_geo(employee_id: int) -> bool:
    """
    Explicitly removes a technician from the Redis GEO candidate index and last-seen table.
    Called when a technician goes offline, clocks out, or accepts an active job (busy).
    """
    if not employee_id:
        return False

    client = get_redis_client()
    if not client:
        return False

    try:
        member = f"employee:{employee_id}"
        client.zrem(REDIS_GEO_KEY, member)
        client.hdel(REDIS_TECH_LAST_SEEN_KEY, str(employee_id))
        logger.debug(f"[REDIS_GEO_REMOVE] Employee #{employee_id} removed from dispatch GEO index.")
        return True
    except Exception as err:
        logger.warning(f"[REDIS_GEO_REMOVE_FAIL] Failed removing Employee #{employee_id}: {err}")
        return False


def find_nearby_technician_candidates(
    latitude: float,
    longitude: float,
    radius_km: Optional[float] = None,
    max_age_seconds: Optional[int] = None
) -> Optional[List[int]]:
    """
    Queries Redis GEO for technicians within radius_km sorted by distance.
    Filters out and prunes any candidate whose last_seen timestamp is older
    than max_age_seconds.
    
    Returns:
      List of integer employee IDs sorted by proximity (ascending), or
      None if Redis is unavailable or fails (signaling the caller to use PostgreSQL fallback).
    """
    client = get_redis_client()
    if not client:
        return None

    if radius_km is None:
        from workforce_api.services.geo_spatial import get_global_dispatch_radius_km
        radius_km = get_global_dispatch_radius_km()

    if max_age_seconds is None:
        max_age_seconds = DISPATCH_LOCATION_MAX_AGE_SECONDS

    now_ts = int(time.time())

    try:
        # 1. Geospatial radius query
        try:
            # Modern Redis 6.2+ command
            raw_results = client.geosearch(
                name=REDIS_GEO_KEY,
                longitude=float(longitude),
                latitude=float(latitude),
                radius=float(radius_km),
                unit="km",
                sort="ASC",
                withdist=True,
            )
        except Exception:
            # Fallback for Redis < 6.2
            raw_results = client.georadius(
                name=REDIS_GEO_KEY,
                longitude=float(longitude),
                latitude=float(latitude),
                radius=float(radius_km),
                unit="km",
                sort="ASC",
                withdist=True,
            )

        if not raw_results:
            return []

        # 2. Extract employee IDs
        extracted_pairs = []
        emp_ids_str = []
        for item in raw_results:
            if isinstance(item, (list, tuple)) and len(item) >= 1:
                member_raw = item[0]
                dist_val = float(item[1]) if len(item) > 1 else 0.0
            else:
                member_raw = item
                dist_val = 0.0

            if isinstance(member_raw, bytes):
                member_str = member_raw.decode("utf-8")
            else:
                member_str = str(member_raw)

            if member_str.startswith("employee:"):
                try:
                    e_id = int(member_str.split(":", 1)[1])
                    extracted_pairs.append((e_id, dist_val, member_str))
                    emp_ids_str.append(str(e_id))
                except ValueError:
                    continue

        if not extracted_pairs:
            return []

        # 3. Check freshness against workforce:technicians:last_seen
        last_seens = client.hmget(REDIS_TECH_LAST_SEEN_KEY, emp_ids_str)
        fresh_candidate_ids = []
        stale_members = []

        for (e_id, dist_val, member_str), ls_raw in zip(extracted_pairs, last_seens):
            is_fresh = False
            if ls_raw is not None:
                try:
                    ls_val = int(ls_raw)
                    age_s = now_ts - ls_val
                    if age_s <= max_age_seconds:
                        is_fresh = True
                except (ValueError, TypeError):
                    is_fresh = False

            if is_fresh:
                fresh_candidate_ids.append(e_id)
            else:
                stale_members.append(member_str)
                stale_members.append(str(e_id))

        # 4. Prune stale members asynchronously from GEO & hash
        if stale_members:
            try:
                pipe = client.pipeline()
                for i in range(0, len(stale_members), 2):
                    pipe.zrem(REDIS_GEO_KEY, stale_members[i])
                    pipe.hdel(REDIS_TECH_LAST_SEEN_KEY, stale_members[i + 1])
                pipe.execute()
                logger.debug(f"[REDIS_GEO_PRUNE] Pruned {len(stale_members)//2} stale technician(s) from GEO index.")
            except Exception as prune_err:
                logger.debug(f"[REDIS_GEO_PRUNE_ERR] {prune_err}")

        logger.info(
            f"[REDIS_GEO_CANDIDATES] Discovered {len(fresh_candidate_ids)} fresh candidate technician(s) "
            f"within {radius_km}km of ({latitude}, {longitude})."
        )
        return fresh_candidate_ids

    except Exception as geo_err:
        logger.warning(f"[REDIS_GEO_SEARCH_FAIL] Failed querying nearby candidates: {geo_err}")
        return None


def ensure_consumer_group() -> bool:
    """
    Ensures that the Redis Stream and Consumer Group exist.
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.xgroup_create(
            REDIS_DISPATCH_STREAM,
            REDIS_DISPATCH_GROUP,
            id="0",
            mkstream=True
        )
        logger.info(f"[REDIS_STREAM] Created consumer group '{REDIS_DISPATCH_GROUP}' on stream '{REDIS_DISPATCH_STREAM}'.")
        return True
    except Exception as err:
        if "BUSYGROUP" in str(err):
            return True
        logger.warning(f"[REDIS_STREAM_GROUP_ERR] Failed creating consumer group: {err}")
        return False


def enqueue_dispatch_job(
    job_id: int,
    event_type: str = "NEW_JOB",
    company_id: Optional[int] = None
) -> Optional[str]:
    """
    Reliably enqueues a dispatch event to Redis Stream (workforce:dispatch:jobs).
    Returns message ID on success, or None if Redis is unavailable.
    """
    if not job_id:
        return None

    client = get_redis_client()
    if not client:
        return None

    ensure_consumer_group()

    payload = {
        "job_id": str(job_id),
        "event_type": str(event_type),
        "company_id": str(company_id or ""),
        "enqueued_at": timezone.now().isoformat(),
    }

    try:
        msg_id = client.xadd(REDIS_DISPATCH_STREAM, payload)
        if isinstance(msg_id, bytes):
            msg_id = msg_id.decode("utf-8")
        logger.info(f"[REDIS_DISPATCH_ENQUEUE] Enqueued Job #{job_id} ({event_type}) -> msg_id: {msg_id}")
        return msg_id
    except Exception as err:
        logger.warning(f"[REDIS_DISPATCH_ENQUEUE_FAIL] Failed enqueueing Job #{job_id}: {err}")
        return None


def acknowledge_dispatch_job(msg_id: str) -> bool:
    """
    Acknowledges (XACK) a processed message in the consumer group.
    Must ONLY be called after successful PostgreSQL transaction commit.
    """
    if not msg_id:
        return False

    client = get_redis_client()
    if not client:
        return False

    try:
        res = client.xack(REDIS_DISPATCH_STREAM, REDIS_DISPATCH_GROUP, msg_id)
        logger.debug(f"[REDIS_DISPATCH_ACK] Acknowledged message {msg_id} (result: {res}).")
        return bool(res)
    except Exception as err:
        logger.warning(f"[REDIS_DISPATCH_ACK_FAIL] Failed acknowledging {msg_id}: {err}")
        return False


def recover_pending_dispatch_messages(
    worker_id: str,
    min_idle_ms: int = 60000,
    count: int = 10
) -> List[Tuple[str, Dict[str, str]]]:
    """
    Recovers unacknowledged messages that have been idle for > min_idle_ms
    (e.g., from worker crashes or network interruptions).
    Uses XPENDING and XCLAIM to safely transfer ownership to this worker.
    """
    client = get_redis_client()
    if not client:
        return []

    recovered_items = []
    try:
        # Check pending messages for the group
        pending_info = client.xpending(REDIS_DISPATCH_STREAM, REDIS_DISPATCH_GROUP)
        total_pending = pending_info.get("pending", 0) if isinstance(pending_info, dict) else 0
        if not total_pending:
            return []

        pending_range = client.xpending_range(
            REDIS_DISPATCH_STREAM,
            REDIS_DISPATCH_GROUP,
            min="-",
            max="+",
            count=count
        )

        claim_msg_ids = []
        for p in pending_range:
            p_msg_id = p.get("message_id") if isinstance(p, dict) else (p[0] if isinstance(p, (list, tuple)) else None)
            p_idle = p.get("time_since_delivered", p.get("idle", 0)) if isinstance(p, dict) else (p[2] if isinstance(p, (list, tuple)) and len(p) > 2 else 0)
            if p_msg_id and p_idle >= min_idle_ms:
                if isinstance(p_msg_id, bytes):
                    p_msg_id = p_msg_id.decode("utf-8")
                claim_msg_ids.append(p_msg_id)

        if claim_msg_ids:
            claimed_msgs = client.xclaim(
                REDIS_DISPATCH_STREAM,
                REDIS_DISPATCH_GROUP,
                worker_id,
                min_idle_time=min_idle_ms,
                message_ids=claim_msg_ids
            )
            for item in claimed_msgs:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    m_id = item[0].decode("utf-8") if isinstance(item[0], bytes) else str(item[0])
                    m_data = {
                        (k.decode("utf-8") if isinstance(k, bytes) else str(k)):
                        (v.decode("utf-8") if isinstance(v, bytes) else str(v))
                        for k, v in item[1].items()
                    }
                    recovered_items.append((m_id, m_data))
            logger.info(f"[REDIS_DISPATCH_RECOVER] Worker '{worker_id}' claimed {len(recovered_items)} pending message(s).")

    except Exception as err:
        logger.debug(f"[REDIS_DISPATCH_RECOVER_ERR] Failed recovering pending messages: {err}")

    return recovered_items


def process_dispatch_stream_events(
    worker_id: str,
    count: int = 10,
    block_ms: int = 500,
    reconcile_fn=None
) -> int:
    """
    Consumes and processes a batch of dispatch events from Redis Stream:
    1. Reclaims any abandoned pending messages.
    2. Reads new messages using XREADGROUP.
    3. Executes bounded, single-job dispatch for each event.
    4. Calls XACK only after successful processing.
    
    Returns the count of messages processed.
    """
    client = get_redis_client()
    if not client:
        return 0

    ensure_consumer_group()

    if reconcile_fn is None:
        from workforce_api.services.automatic_dispatch import reconcile_booking_for_dispatch
        reconcile_fn = reconcile_booking_for_dispatch

    # Bounded block_ms to prevent socket timeouts (client socket_timeout is 1.0s)
    if block_ms is not None and block_ms >= 800:
        block_ms = 500

    messages_to_process = []

    # 1. Recover pending messages
    recovered = recover_pending_dispatch_messages(worker_id, min_idle_ms=60000, count=count)
    messages_to_process.extend(recovered)

    # 2. Read new messages
    try:
        read_res = client.xreadgroup(
            groupname=REDIS_DISPATCH_GROUP,
            consumername=worker_id,
            streams={REDIS_DISPATCH_STREAM: ">"},
            count=count,
            block=block_ms,
        )
        if read_res:
            for stream_name, msg_list in read_res:
                for msg_id, raw_fields in msg_list:
                    m_id_str = msg_id.decode("utf-8") if isinstance(msg_id, bytes) else str(msg_id)
                    fields_dict = {
                        (k.decode("utf-8") if isinstance(k, bytes) else str(k)):
                        (v.decode("utf-8") if isinstance(v, bytes) else str(v))
                        for k, v in raw_fields.items()
                    }
                    messages_to_process.append((m_id_str, fields_dict))
    except Exception as read_err:
        logger.warning(f"[REDIS_STREAM_READ_FAIL] {read_err}")
        return 0

    if not messages_to_process:
        return 0

    processed_count = 0
    for msg_id, data in messages_to_process:
        raw_job_id = data.get("job_id")
        if not raw_job_id:
            acknowledge_dispatch_job(msg_id)
            continue

        try:
            job_id = int(raw_job_id)
        except ValueError:
            acknowledge_dispatch_job(msg_id)
            continue

        event_type = data.get("event_type", "NEW_JOB")
        logger.info(f"[DISPATCH_WORKER] Processing Job #{job_id} ({event_type}) from message {msg_id}...")

        try:
            # Execute single-job targeted dispatch with Redis GEO candidate discovery
            success, msg = reconcile_fn(job_id, use_redis_geo=True)
            logger.info(f"[DISPATCH_WORKER_RESULT] Job #{job_id} result: success={success}, msg='{msg}'")
            # Acknowledge message in Redis Stream only after successful execution
            acknowledge_dispatch_job(msg_id)
            processed_count += 1
        except Exception as proc_err:
            logger.error(f"[DISPATCH_WORKER_ERR] Error processing Job #{job_id}: {proc_err}", exc_info=True)
            # Message remains unacknowledged in Redis Stream for retry/recovery

    return processed_count
