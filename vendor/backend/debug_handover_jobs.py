import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from workforce_api.views import WorkforceJobListView

User = get_user_model()
factory = APIRequestFactory()
view = WorkforceJobListView.as_view()

u = User.objects.filter(username="handover_tech_01").first()
req = factory.get("/api/workforce/jobs/?status=all")
req.user = u
resp = view(req)

print("Status Code:", resp.status_code)
jobs_data = resp.data
print("Jobs Count:", len(jobs_data))
for j in jobs_data:
    print("\n--- JOB ---")
    print("ID:", j.get("id"))
    print("Request ID:", j.get("request_id"))
    print("Status:", j.get("status"))
    print("Job Type:", j.get("job_type"))
    print("Preferred Date:", j.get("preferred_date"))
    print("Created At:", j.get("created_at"))
    print("Is Offer:", j.get("is_offer"))
    print("Offer Status:", j.get("offer_status"))
    print("Active Offer:", j.get("active_offer"))
    print("Is Assigned:", j.get("is_assigned_to_current_employee"))
    print("Is Accepted:", j.get("is_accepted_by_current_employee"))
