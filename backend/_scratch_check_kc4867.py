from service_requests.models import ServiceRequest
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n--- KC4867 booking ---")
sr = ServiceRequest.objects.filter(request_id__icontains="KC4867").first()
if not sr:
    sr = ServiceRequest.objects.order_by("-created_at").first()
    print("(couldn't find KC4867 by request_id, showing most recent booking instead)")
if sr:
    print(f"id={sr.id} request_id={getattr(sr, 'request_id', None)} status={sr.status} "
          f"company_id={sr.company_id} assigned_employee_id={sr.assigned_employee_id} "
          f"service_category={getattr(sr, 'service_category', None)}")
else:
    print("No ServiceRequest rows found at all!")

print("\n--- Ramesh Kumar (technician) ---")
for u in User.objects.filter(employee_profile__isnull=False):
    emp = getattr(u, "employee_profile", None)
    if emp and "ramesh" in (getattr(emp, "full_name", "") or u.get_full_name() or u.username or "").lower():
        print(f"user={u.username} emp_id={emp.id} company_id={emp.company_id} "
              f"is_active={emp.is_active} is_online={getattr(emp, 'is_online', None)} "
              f"current_availability={getattr(emp, 'current_availability', None)}")

print("\n--- Caldim Admin user ---")
for u in User.objects.filter(username__icontains="admin") | User.objects.filter(email__icontains="admin"):
    emp = getattr(u, "employee_profile", None)
    print(f"user={u.username} is_staff={u.is_staff} is_superuser={u.is_superuser} "
          f"user.company_id={getattr(u, 'company_id', 'N/A')} "
          f"emp.company_id={getattr(emp, 'company_id', None) if emp else 'no emp profile'}")

print("\n--- Companies referenced by recent bookings ---")
from companies.models import Company
ids_in_use = set(ServiceRequest.objects.order_by("-created_at")[:5].values_list("company_id", flat=True))
for c in Company.objects.filter(id__in=ids_in_use):
    print(f"id={c.id} name={c.company_name} slug={c.slug}")
