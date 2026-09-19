import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from service_requests.models import ServiceRequest
from django.db.models import Count

print("Total ServiceRequests:", ServiceRequest.objects.count())
print("\nBreakdown by status:")
for item in ServiceRequest.objects.values("status").annotate(c=Count("id")).order_by("-c"):
    print(f"  {item['status']}: {item['c']}")

print("\nRecent 15 ServiceRequests:")
for sr in ServiceRequest.objects.order_by("-created_at")[:15]:
    print(f"  ID: {sr.id}, req_id: {sr.request_id}, status: {sr.status}, scheduled: {sr.scheduled_date}, created: {sr.created_at}, company: {sr.company_id}, assigned: {sr.assigned_employee_id}")
