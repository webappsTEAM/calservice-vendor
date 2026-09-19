import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.contrib.auth import get_user_model
from employees.models import Employee
from workforce_api.models import WorkforceJobOffer
from service_requests.models import ServiceRequest

User = get_user_model()
for uname in ["technician01", "technician02", "handover_tech_01", "vendor01"]:
    u = User.objects.filter(username=uname).first()
    if not u: continue
    emp = Employee.objects.filter(user=u).first()
    if not emp:
        print(uname, "NO EMP")
        continue
    offers = list(WorkforceJobOffer.objects.filter(employee=emp).values("job_id", "status", "expires_at"))
    assigned_jobs = list(ServiceRequest.objects.filter(assigned_employee=emp).values("id", "status"))
    print(f"{uname} (emp #{emp.id}): online={emp.is_online}, avail={emp.current_availability}, co={emp.company_id}")
    print("   Services:", (emp.bank_details or {}).get("onboarding", {}).get("services", []))
    print("   Offers:", offers)
    print("   Assigned jobs:", assigned_jobs)
