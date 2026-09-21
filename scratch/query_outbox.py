import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vendor", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if "SEVO_E2E_SQLITE_PATH" in os.environ:
    del os.environ["SEVO_E2E_SQLITE_PATH"]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from workforce_api.models import SellerOrderStatusOutbox
from django.db.models import Count

status_counts = list(SellerOrderStatusOutbox.objects.values("status").annotate(cnt=Count("id")))
print("SellerOrderStatusOutbox counts by status:")
if not status_counts:
    print("  (Table is empty / 0 records)")
for s in status_counts:
    print(f"  {s['status']}: {s['cnt']}")

recent_errors = list(
    SellerOrderStatusOutbox.objects.exclude(last_error__isnull=True)
    .exclude(last_error="")
    .order_by("-id")
    .values_list("last_error", flat=True)[:5]
)
print("\n5 most recent last_error strings:")
if not recent_errors:
    print("  (No error entries recorded)")
for idx, err in enumerate(recent_errors, 1):
    print(f"  {idx}. {err}")
