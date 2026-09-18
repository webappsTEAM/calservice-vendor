import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from service_requests.models import ServiceRequest

today = timezone.localdate()
today_jobs = ServiceRequest.objects.filter(preferred_date=today)
print(f"Jobs with preferred_date={today}: {today_jobs.count()}")
for j in today_jobs:
    print(f"  Job #{j.id}: status={j.status} cat={j.service_category}")
