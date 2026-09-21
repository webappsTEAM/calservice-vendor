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

pending_rows = list(
    SellerOrderStatusOutbox.objects.filter(status=SellerOrderStatusOutbox.DeliveryStatus.PENDING)
    .select_related("order__company")
    .order_by("id")
)

print(f"Total PENDING Outbox Rows: {len(pending_rows)}")
for idx, row in enumerate(pending_rows, 1):
    comp_slug = row.order.company.slug if (row.order and row.order.company) else "N/A"
    print(
        f"[{idx:2d}] ID: {row.id} | event_id: '{row.event_id}' | source_order_id: '{row.source_order_id}' | "
        f"company_slug: '{comp_slug}' | seq: {row.sequence} | new_status: '{row.new_status}' | "
        f"retries: {row.retry_count} | next_retry: {row.next_retry_at} | created: {row.created_at}"
    )
