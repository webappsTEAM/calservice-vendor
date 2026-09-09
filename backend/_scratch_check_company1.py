from companies.models import Company
from django.contrib.auth import get_user_model
from service_requests.models import ServiceRequest

User = get_user_model()

print("--- Company id=1 ---")
c1 = Company.objects.filter(id=1).first()
if c1:
    print(f"id={c1.id} name={c1.company_name} slug={c1.slug} display_id={c1.display_id} primary_country={c1.primary_country}")
else:
    print("No company with id=1 exists!")

print("\n--- Company id=918 ---")
c918 = Company.objects.filter(id=918).first()
print(f"id={c918.id} name={c918.company_name} slug={c918.slug} display_id={c918.display_id} primary_country={c918.primary_country}")

print("\n--- How many employees per company (top 10) ---")
from employees.models import Employee
from django.db.models import Count
for row in Employee.objects.values("company_id").annotate(n=Count("id")).order_by("-n")[:10]:
    comp = Company.objects.filter(id=row["company_id"]).first()
    print(f"company_id={row['company_id']} name={comp.company_name if comp else '???'} employees={row['n']}")

print("\n--- How many ServiceRequests per company (top 10, all time) ---")
for row in ServiceRequest.objects.values("company_id").annotate(n=Count("id")).order_by("-n")[:10]:
    comp = Company.objects.filter(id=row["company_id"]).first()
    print(f"company_id={row['company_id']} name={comp.company_name if comp else '???'} bookings={row['n']}")

print("\n--- All employees under company_id=1 ---")
for e in Employee.objects.filter(company_id=1)[:20]:
    print(f"emp_id={e.id} name={getattr(e,'full_name',None)} is_active={e.is_active}")
