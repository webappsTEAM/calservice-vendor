import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from service_requests.models import ServiceRequest

for sr in ServiceRequest.objects.exclude(cart_data__isnull=True).exclude(cart_data={})[:3]:
    print(f"SR ID: {sr.id}, request_id: {sr.request_id}, invoice_id: {sr.invoice_id}")
    import json
    print(f"cart_data: {json.dumps(sr.cart_data, ensure_ascii=True)}")
