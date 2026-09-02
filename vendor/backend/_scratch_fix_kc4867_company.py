from service_requests.models import ServiceRequest

sr = ServiceRequest.objects.filter(request_id__icontains="KC4867").first()
if not sr:
    print("KC4867 not found -- nothing to fix.")
else:
    print(f"Before: id={sr.id} company_id={sr.company_id} status={sr.status} "
          f"assigned_employee_id={sr.assigned_employee_id} "
          f"lat={getattr(sr,'latitude',None)} lng={getattr(sr,'longitude',None)}")
    sr.company_id = 1
    sr.save(update_fields=["company_id"])
    sr.refresh_from_db()
    print(f"After:  id={sr.id} company_id={sr.company_id}")
