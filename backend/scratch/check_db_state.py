import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from accounts.models import User
from employees.models import Employee
from companies.models import Company
from service_requests.models import ServiceRequest, Estimation, EstimationQuotation

print("=== USERS ===")
for u in User.objects.filter(is_active=True)[:10]:
    print(f"User: {u.id}, username: {u.username}, role: {getattr(u, 'role', None)}, company_id: {getattr(u, 'company_id', None)}")

print("\n=== EMPLOYEES ===")
for e in Employee.objects.filter(is_active=True)[:10]:
    print(f"Employee: {e.id}, user: {e.user.username}, company: {e.company_id}, status: {getattr(e, 'status', None)}")

print("\n=== ESTIMATIONS ===")
for est in Estimation.objects.all().order_by("-id")[:5]:
    sr = est.service_request
    print(f"Est ID: {est.id}, status: {est.status}, SR: {sr.id} ({sr.request_id}), status: {sr.status}, tech: {sr.technician_name} (id: {sr.technician_id}), assigned_emp: {sr.assigned_employee_id}")

print("\n=== QUOTATIONS ===")
for q in EstimationQuotation.objects.all().order_by("-id")[:5]:
    print(f"Quote ID: {q.id}, ref: {q.quote_ref}, status: {q.status}, total: {q.total_amount}, est_id: {q.estimation_id}")
