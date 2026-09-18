import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from workforce_api.views import WorkforceJobListView

User = get_user_model()
factory = APIRequestFactory()
view = WorkforceJobListView.as_view()

test_usernames = [
    "suryaramya111111@gmail.com", "Lokeshwari", "vignesh@caldim.in",
    "vendor01", "handover_tech_01", "tech4_suite_user", "technician01", "technician02",
    "employee", "rk.chem", "hari", "admin_baffe4"
]

print("=== TESTING apiGetWorkforceJobs FOR KEY USERS ===")
for uname in test_usernames:
    u = User.objects.filter(username=uname).first()
    if not u:
        print(f"{uname}: USER NOT FOUND")
        continue
    for st_param in ["all", "active"]:
        url = f"/api/workforce/jobs/?status={st_param}"
        req = factory.get(url)
        req.user = u
        try:
            resp = view(req)
            count = len(resp.data) if isinstance(resp.data, list) else f"ERROR: {resp.data}"
            print(f"User {u.username} (role={getattr(u, 'role', None)}, co={getattr(u, 'company_id', None)}) [status={st_param}] -> HTTP {resp.status_code}, count={count}")
        except Exception as e:
            print(f"User {u.username} [status={st_param}] -> EXCEPTION: {e}")
