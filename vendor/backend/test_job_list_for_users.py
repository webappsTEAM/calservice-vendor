import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from workforce_api.views import WorkforceJobListView
from employees.models import Employee

User = get_user_model()
factory = APIRequestFactory()
view = WorkforceJobListView.as_view()

print("=== TESTING WorkforceJobListView FOR USERS ===")
for u in User.objects.filter(is_active=True).order_by("id")[:20]:
    req = factory.get("/api/workforce/jobs/?status=all")
    req.user = u
    try:
        resp = view(req)
        data = resp.data if hasattr(resp, "data") else []
        print(f"User #{u.id} ({u.username}), role={getattr(u, 'role', None)}, is_super={u.is_superuser} -> Status {resp.status_code}, Jobs count: {len(data) if isinstance(data, list) else data}")
    except Exception as e:
        print(f"User #{u.id} ({u.username}) -> EXCEPTION: {e}")
