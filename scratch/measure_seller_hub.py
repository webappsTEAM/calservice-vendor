import os
import sys
import time
import re
import statistics
from collections import Counter

# Flush stdout immediately
sys.stdout.reconfigure(line_buffering=True)

# Add vendor/backend to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vendor", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ["*"]

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

# Ensure safe client that ONLY permits GET
class SafeReadOnlyClient:
    def __init__(self, client):
        self._client = client

    def get(self, path, data=None, **extra):
        return self._client.get(path, data=data, **extra)

    def post(self, *args, **kwargs):
        raise RuntimeError("POST is strictly forbidden in read-only measurement")

    def put(self, *args, **kwargs):
        raise RuntimeError("PUT is strictly forbidden in read-only measurement")

    def patch(self, *args, **kwargs):
        raise RuntimeError("PATCH is strictly forbidden in read-only measurement")

    def delete(self, *args, **kwargs):
        raise RuntimeError("DELETE is strictly forbidden in read-only measurement")


def normalize_sql(sql_text):
    # Strip literal numbers and strings to detect query templates
    s = re.sub(r"'[^']*'", "'?'", sql_text)
    s = re.sub(r'\b\d+\b', '?', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def measure_db_baseline():
    latencies = []
    with connection.cursor() as cursor:
        for _ in range(30):
            t0 = time.perf_counter()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)
    
    return {
        "min_ms": min(latencies),
        "median_ms": statistics.median(latencies),
        "max_ms": max(latencies),
        "all_ms": latencies
    }


def run_measurement():
    print("=" * 80, flush=True)
    print("SELLER HUB ENDPOINTS PERFORMANCE & LATENCY MEASUREMENT", flush=True)
    print("=" * 80, flush=True)

    # 1. Baseline DB Latency
    db_base = measure_db_baseline()
    print(f"PostgreSQL Baseline Roundtrip Latency (30 x 'SELECT 1'):", flush=True)
    print(f"  Min:    {db_base['min_ms']:.2f} ms", flush=True)
    print(f"  Median: {db_base['median_ms']:.2f} ms", flush=True)
    print(f"  Max:    {db_base['max_ms']:.2f} ms", flush=True)
    print("=" * 80, flush=True)

    # 2. Resolve User
    user = User.objects.filter(email="vignesh@caldim.in").first()
    if not user:
        user = User.objects.filter(username="vignesh@caldim.in").first()
    if not user:
        user = User.objects.filter(company_id=3).first()
    if not user:
        raise RuntimeError("User vignesh@caldim.in (company 3) not found in database!")

    print(f"Authenticated as user: id={user.id}, email={user.email}, username={user.username}, company_id={getattr(user, 'company_id', None)}", flush=True)
    print("=" * 80, flush=True)

    raw_client = APIClient()
    raw_client.force_authenticate(user=user)
    client = SafeReadOnlyClient(raw_client)

    endpoints = [
        "/api/workforce/seller-hub/metrics/",
        "/api/workforce/seller-hub/products/",
        "/api/workforce/seller-hub/products/batches/",
        "/api/workforce/seller-hub/categories/active/",
        "/api/workforce/seller-hub/catalog/categories/",
        "/api/workforce/seller-hub/categories/",
        "/api/workforce/seller-hub/categories/tree/",
        "/api/workforce/seller-hub/coupons/",
        "/api/workforce/seller-hub/inventory/",
        "/api/workforce/seller-hub/orders/",
        "/api/workforce/seller-hub/returns/",
        "/api/workforce/seller-hub/claims/",
        "/api/workforce/seller-hub/reports/summary/",
        "/api/workforce/seller-hub/reports/performance/",
        "/api/workforce/seller-hub/reports/quality-audit/",
        "/api/workforce/admin/seller-hub/approval/sellers/",
    ]

    results = []

    for ep in endpoints:
        print(f"Measuring endpoint: {ep} ...", flush=True)
        ep_runs = []
        for run_idx in (1, 2):
            try:
                with CaptureQueriesContext(connection) as ctx:
                    t0 = time.perf_counter()
                    res = client.get(ep)
                    t1 = time.perf_counter()

                wall_ms = (t1 - t0) * 1000.0
                query_count = len(ctx.captured_queries)
                sql_time_ms = sum(float(q.get("time", 0)) for q in ctx.captured_queries) * 1000.0
                content_len = len(res.content) if hasattr(res, "content") else 0
                status_code = res.status_code

                # Analyze repeated queries
                templates = [normalize_sql(q["sql"]) for q in ctx.captured_queries]
                counter = Counter(templates)
                if counter:
                    most_common_tpl, most_common_cnt = counter.most_common(1)[0]
                else:
                    most_common_tpl, most_common_cnt = "None", 0

                ep_runs.append({
                    "run": run_idx,
                    "status": status_code,
                    "bytes": content_len,
                    "wall_ms": wall_ms,
                    "queries": query_count,
                    "sql_ms": sql_time_ms,
                    "worst_query": most_common_tpl[:200],
                    "worst_count": most_common_cnt
                })
            except Exception as exc:
                t1 = time.perf_counter()
                wall_ms = (t1 - t0) * 1000.0
                query_count = len(ctx.captured_queries) if 'ctx' in locals() else 0
                sql_time_ms = sum(float(q.get("time", 0)) for q in ctx.captured_queries) * 1000.0 if 'ctx' in locals() else 0
                
                templates = [normalize_sql(q["sql"]) for q in ctx.captured_queries] if 'ctx' in locals() else []
                counter = Counter(templates)
                most_common_tpl, most_common_cnt = counter.most_common(1)[0] if counter else ("None", 0)

                err_name = exc.__class__.__name__
                ep_runs.append({
                    "run": run_idx,
                    "status": f"ERR:{err_name}",
                    "bytes": 0,
                    "wall_ms": wall_ms,
                    "queries": query_count,
                    "sql_ms": sql_time_ms,
                    "worst_query": f"{err_name}: {str(exc)[:100]} | SQL: {most_common_tpl[:100]}",
                    "worst_count": most_common_cnt
                })
                # Reopen connection after error
                try:
                    connection.close()
                except Exception:
                    pass

        results.append({
            "endpoint": ep,
            "runs": ep_runs
        })

    # Print Detailed Output
    print("\nRAW MEASUREMENT RESULTS:", flush=True)
    for r in results:
        ep = r["endpoint"]
        run1 = r["runs"][0]
        run2 = r["runs"][1]
        print(f"\nEndpoint: {ep}", flush=True)
        print(f"  Run 1 (Cold): status={run1['status']}, size={run1['bytes']}B, wall={run1['wall_ms']:.2f}ms, queries={run1['queries']}, db_time={run1['sql_ms']:.2f}ms", flush=True)
        print(f"  Run 2 (Warm): status={run2['status']}, size={run2['bytes']}B, wall={run2['wall_ms']:.2f}ms, queries={run2['queries']}, db_time={run2['sql_ms']:.2f}ms", flush=True)
        if run2["worst_count"] > 1:
            print(f"  Repeated SQL ({run2['worst_count']}x): {run2['worst_query']}", flush=True)

    # Print Table
    print("\n" + "=" * 120, flush=True)
    print("SUMMARY TABLE (Sorted by Run 2 Warm Wall Time):", flush=True)
    print("=" * 120, flush=True)
    print(f"{'Endpoint':<45} | {'Status':<6} | {'Queries':<7} | {'Run 1 (ms)':<10} | {'Run 2 (ms)':<10} | {'Worst Repeated Query x Count'}", flush=True)
    print("-" * 120, flush=True)

    # Sort results by run 2 wall time descending
    sorted_results = sorted(results, key=lambda x: x["runs"][1]["wall_ms"], reverse=True)

    for r in sorted_results:
        ep = r["endpoint"]
        run1 = r["runs"][0]
        run2 = r["runs"][1]
        worst_str = f"{run2['worst_count']}x: {run2['worst_query'][:60]}..." if run2['worst_count'] > 1 else "-"
        print(f"{ep:<45} | {str(run2['status']):<6} | {run2['queries']:<7} | {run1['wall_ms']:<10.2f} | {run2['wall_ms']:<10.2f} | {worst_str}", flush=True)
    print("=" * 120, flush=True)


if __name__ == "__main__":
    run_measurement()
