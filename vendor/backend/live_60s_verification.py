import os
import sys
import time
import requests
import json
import threading
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from workforce_api.models import WorkforceEventLog, WorkforceDispatchState
from employees.models import Employee
from companies.models import Company
from service_requests.models import ServiceRequest

User = get_user_model()

def run_live_test():
    print("==================================================================")
    print("           CALTRACK — 60-SECOND LIVE IDLE & ENDPOINT TEST         ")
    print("==================================================================")

    # Find or create a test technician
    # Find an approved active test technician
    emp = None
    for candidate in Employee.objects.filter(is_active=True):
        ob = (candidate.bank_details or {}).get("onboarding", {})
        if isinstance(ob, dict) and ob.get("status") == "approved":
            emp = candidate
            break

    if not emp:
        co = Company.objects.first()
        user = User.objects.create_user(
            username="live_test_tech_appr", password="TestPass@123", email="live_test_tech_appr@example.com",
            role="employee", company=co
        )
        emp = Employee.objects.create(
            user=user, company=co, is_active=True, is_online=True, current_availability="available",
            bank_details={"onboarding": {"status": "approved"}}
        )
    else:
        user = emp.user

    token = str(RefreshToken.for_user(user).access_token)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = "http://localhost:8001"

    # Baseline DB event count
    t_start = timezone.now()
    initial_event_count = WorkforceEventLog.objects.count()
    print(f"\n[START] Baseline WorkforceEventLog count: {initial_event_count}")
    print(f"[START] Testing with approved employee #{emp.id} ({user.username})")
    print(f"[START] Beginning 60-second observation window at {t_start.isoformat()}...")

    # SSE listener thread
    sse_events = []
    sse_heartbeats = 0
    sse_reconnects = 0
    stop_event = threading.Event()

    def sse_worker():
        nonlocal sse_reconnects, sse_heartbeats
        sse_url = f"{base_url}/api/workforce/realtime/stream/"
        while not stop_event.is_set():
            try:
                resp = requests.get(sse_url, headers={"Authorization": f"Bearer {token}"}, stream=True, timeout=30)
                for line in resp.iter_lines():
                    if stop_event.is_set():
                        break
                    if line:
                        decoded = line.decode("utf-8", errors="replace")
                        if decoded.startswith("data:"):
                            sse_events.append(decoded)
                        elif "heartbeat" in decoded or decoded.startswith(":"):
                            sse_heartbeats += 1
            except Exception as e:
                if not stop_event.is_set():
                    sse_reconnects += 1
                    time.sleep(1)

    t_sse = threading.Thread(target=sse_worker, daemon=True)
    t_sse.start()

    # Simulate user activity over the 60s window:
    # At T+10s: GET jobs
    # At T+20s: GET presence status
    # At T+30s: POST location update (GPS)
    # At T+40s: POST presence toggle-online
    # At T+50s: GET jobs again
    time_elapsed = 0
    while time_elapsed < 60:
        time.sleep(10)
        time_elapsed += 10
        print(f"  [T+{time_elapsed}s] Active inspection point...")

        if time_elapsed == 10:
            r = requests.get(f"{base_url}/api/workforce/jobs/?status=active", headers=headers)
            print(f"    GET /jobs -> HTTP {r.status_code}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        elif time_elapsed == 20:
            r = requests.get(f"{base_url}/api/workforce/presence/status/", headers=headers)
            print(f"    GET /presence/status/ -> HTTP {r.status_code}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        elif time_elapsed == 30:
            r = requests.post(f"{base_url}/api/workforce/presence/location/", headers=headers, json={
                "latitude": 12.9716, "longitude": 77.5946, "accuracy": 10.0, "captured_at": timezone.now().isoformat()
            })
            print(f"    POST /presence/location/ (GPS update) -> HTTP {r.status_code}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        elif time_elapsed == 40:
            r = requests.post(f"{base_url}/api/workforce/presence/toggle-online/", headers=headers, json={"is_online": True})
            print(f"    POST /presence/toggle-online/ -> HTTP {r.status_code}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        elif time_elapsed == 50:
            r = requests.get(f"{base_url}/api/workforce/jobs/?status=active", headers=headers)
            print(f"    GET /jobs (refresh) -> HTTP {r.status_code}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    stop_event.set()
    t_end = timezone.now()

    final_event_count = WorkforceEventLog.objects.count()
    events_created = final_event_count - initial_event_count

    events_in_window = WorkforceEventLog.objects.filter(created_at__gte=t_start, created_at__lte=t_end)
    dispatch_started = events_in_window.filter(event_type="DISPATCH_STARTED").count()
    candidates_eval = events_in_window.filter(event_type="CANDIDATES_EVALUATED").count()
    dispatch_unassigned = events_in_window.filter(event_type="DISPATCH_UNASSIGNED_REASON").count()

    print("\n==================================================================")
    print("                    60-SECOND TEST RESULTS                        ")
    print("==================================================================")
    print(f"Observation window duration:         60.0 seconds")
    print(f"Total WorkforceEventLog rows created: {events_created}")
    print(f"DISPATCH_STARTED count:              {dispatch_started}")
    print(f"CANDIDATES_EVALUATED count:          {candidates_eval}")
    print(f"DISPATCH_UNASSIGNED_REASON count:    {dispatch_unassigned}")
    print(f"SSE reconnect count:                 {sse_reconnects}")
    print(f"SSE events captured:                 {len(sse_events)}")
    print("------------------------------------------------------------------")

    # Invariants verification
    assert events_created < 10, f"Event count exceeded threshold! ({events_created} rows)"
    assert dispatch_started <= 2, f"Dispatch storm detected! DISPATCH_STARTED={dispatch_started}"
    assert sse_reconnects <= 1, f"Unstable SSE connection: {sse_reconnects} reconnects"

    print("[SUCCESS] ZERO EVENT STORM! System is completely stable and controlled.")
    print("==================================================================")

if __name__ == "__main__":
    run_live_test()
