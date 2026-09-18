import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from service_requests.models import ServiceRequest

jobs = ServiceRequest.objects.filter(id__in=[5289, 5352, 5660, 5654]).values("id", "status", "preferred_date", "created_at", "company_id")
for j in jobs:
    print(j)
