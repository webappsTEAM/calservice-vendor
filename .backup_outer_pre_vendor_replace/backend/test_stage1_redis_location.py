"""
backend/test_stage1_redis_location.py

Stage 1 Verification Script:
- Redis Configuration & Django Settings Exposure
- Redis Client Ping
- Current Location SET (with 300s TTL)
- Current Location GET
- Location Replacement (A -> B)
- Key Cleanup
- Error / Edge Case Resiliency
"""

import os
import sys
import time

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from django.conf import settings
from workforce_api.services.realtime import (
    get_redis_client,
    set_job_current_location,
    get_job_current_location,
)

passed_tests = 0
failed_tests = 0


def report(test_name: str, success: bool, detail: str = ""):
    global passed_tests, failed_tests
    if success:
        passed_tests += 1
        print(f"  [PASS] {test_name}: {detail}")
    else:
        failed_tests += 1
        print(f"  [FAIL] {test_name}: {detail}")


def run_stage1_verification():
    print("\n" + "=" * 60)
    print("STAGE 1: REDIS INTEGRATION & CURRENT LOCATION VERIFICATION")
    print("=" * 60 + "\n")

    # TEST 1: Django Settings & Environment Configuration
    redis_url = getattr(settings, "REDIS_URL", None)
    report(
        "TEST 1 — Settings REDIS_URL Exposure",
        bool(redis_url),
        f"REDIS_URL = {redis_url}"
    )

    # TEST 2: Redis Client Connection & Ping
    client = get_redis_client()
    ping_ok = False
    if client:
        try:
            ping_ok = client.ping()
        except Exception as e:
            ping_ok = False
    report(
        "TEST 2 — Redis Client ping()",
        ping_ok is True,
        f"client.ping() = {ping_ok}"
    )

    if not ping_ok:
        print("\nERROR: Redis is not reachable. Ensure Docker container workforce-redis is running.")
        sys.exit(1)

    # TEST 3: set_job_current_location with TTL
    test_job_id = 999888
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload_a = {
        "latitude": 12.9715987,
        "longitude": 77.5945627,
        "accuracy": 8.5,
        "speed": 22.4,
        "heading": 120.0,
        "captured_at": now_iso,
        "updated_at": now_iso,
    }

    set_ok_a = set_job_current_location(test_job_id, payload_a, ttl=300)
    report(
        "TEST 3 — set_job_current_location(job_id, payload_a)",
        set_ok_a is True,
        f"Stored key 'job_location:{test_job_id}'"
    )

    # Verify TTL on key
    key = f"job_location:{test_job_id}"
    ttl = client.ttl(key)
    report(
        "TEST 3b — Redis Key TTL Verification",
        280 <= ttl <= 300,
        f"TTL for key '{key}' is {ttl}s (expected ~300s)"
    )

    # TEST 4: get_job_current_location
    retrieved_a = get_job_current_location(test_job_id)
    matches_a = (
        retrieved_a is not None
        and retrieved_a.get("latitude") == payload_a["latitude"]
        and retrieved_a.get("longitude") == payload_a["longitude"]
        and retrieved_a.get("accuracy") == payload_a["accuracy"]
        and retrieved_a.get("speed") == payload_a["speed"]
        and retrieved_a.get("heading") == payload_a["heading"]
    )
    report(
        "TEST 4 — get_job_current_location(job_id)",
        matches_a,
        f"Retrieved lat={retrieved_a.get('latitude') if retrieved_a else None}, lng={retrieved_a.get('longitude') if retrieved_a else None}"
    )

    # TEST 5: Replacement (Location A -> Location B)
    now_b_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload_b = {
        "latitude": 12.9730000,
        "longitude": 77.5960000,
        "accuracy": 5.0,
        "speed": 18.0,
        "heading": 90.0,
        "captured_at": now_b_iso,
        "updated_at": now_b_iso,
    }
    set_ok_b = set_job_current_location(test_job_id, payload_b, ttl=300)
    retrieved_b = get_job_current_location(test_job_id)
    matches_b = (
        set_ok_b is True
        and retrieved_b is not None
        and retrieved_b.get("latitude") == 12.9730000
        and retrieved_b.get("longitude") == 77.5960000
    )
    report(
        "TEST 5 — In-Place Replacement (Location A -> Location B)",
        matches_b,
        f"Location updated to lat={retrieved_b.get('latitude') if retrieved_b else None}, lng={retrieved_b.get('longitude') if retrieved_b else None}"
    )

    # TEST 6: Key Cleanup
    del_count = client.delete(key)
    retrieved_after_del = get_job_current_location(test_job_id)
    report(
        "TEST 6 — Cleanup & Non-Existent Key Handling",
        del_count == 1 and retrieved_after_del is None,
        f"Deleted {del_count} key(s), get() returned None"
    )

    # TEST 7: Resiliency against None / Zero job_id
    res_none = set_job_current_location(0, payload_a)
    get_none = get_job_current_location(0)
    report(
        "TEST 7 — Invalid Job ID Resiliency",
        res_none is False and get_none is None,
        "Safely returned False/None without crashing"
    )

    print("\n" + "-" * 60)
    print(f"STAGE 1 SUMMARY: {passed_tests} PASSED, {failed_tests} FAILED")
    print("-" * 60 + "\n")

    if failed_tests > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_stage1_verification()
