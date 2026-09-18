import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from service_requests.models import ServiceRequest

j = ServiceRequest.objects.filter(id=5643).values().first()
print(j)
