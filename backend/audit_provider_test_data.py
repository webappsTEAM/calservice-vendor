"""
workforce-app/backend/audit_provider_test_data.py
Audit and safe cleanup script for test/demo Service Provider data.
Safely identifies test companies created during development and testing suites.
Preserves all legitimate production companies and foreign keys.
"""
import os
import sys
import argparse

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import transaction
from companies.models import Company
from accounts.models import User
from employees.models import Employee
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceProviderJoinRequest

# Known legitimate companies that MUST NEVER be touched
PROTECTED_COMPANY_IDS = {1, 3, 4, 7, 8, 276}

TEST_PATTERNS = [
    "9gate",
    "phase2 enterprise",
    "phase 1 vendor",
    "scenario",
    "testa_co",
    "testb_",
    "testc_",
    "testd_",
    "teste_",
    "services test comp",
    "packers movers test",
    "concurrency test",
    "rival co",
    "rival field",
    "apex field",
    "rival corp",
    "acme services",
    "solar pros alpha",
    "apex solutions alpha",
    "inactive omega",
    "provider beta",
    "audit dispatch",
    "handover test",
    "independent_",
    "rival services",
    "competitor",
    "acme-",
    "state machine audit",
    "workload isolation",
    "integrity test",
    "load benchmark",
    "rapido transit",
    "other transit",
    "certcomp",
    "_debug",
    "vendor x ",
]



def audit_companies(dry_run=True):
    from django.db.models import Count

    print("Fetching company records and aggregated metrics in bulk...")
    user_counts = dict(User.objects.exclude(company_id=None).values_list("company_id").annotate(c=Count("id")).values_list("company_id", "c"))
    emp_counts = dict(Employee.objects.exclude(company_id=None).values_list("company_id").annotate(c=Count("id")).values_list("company_id", "c"))
    sr_counts = dict(ServiceRequest.objects.exclude(company_id=None).values_list("company_id").annotate(c=Count("id")).values_list("company_id", "c"))
    jr_counts = dict(WorkforceProviderJoinRequest.objects.values_list("provider_id").annotate(c=Count("id")).values_list("provider_id", "c"))

    all_companies = list(Company.objects.all().order_by("id"))
    legit_list = []
    test_list = []

    for comp in all_companies:
        name_lower = (comp.company_name or "").lower()
        is_protected = comp.id in PROTECTED_COMPANY_IDS
        is_test_match = any(p in name_lower for p in TEST_PATTERNS)

        users_count = user_counts.get(comp.id, 0)
        employees_count = emp_counts.get(comp.id, 0)
        sr_count = sr_counts.get(comp.id, 0)
        jr_count = jr_counts.get(comp.id, 0)

        data = {
            "id": comp.id,
            "name": comp.company_name,
            "display_id": comp.display_id,
            "is_active": comp.is_active,
            "created_at": comp.created_at,
            "users": users_count,
            "employees": employees_count,
            "service_requests": sr_count,
            "join_requests": jr_count,
        }


        # STRICT SAFETY: If a company has actual ServiceRequests or is protected or id < 50, preserve it!
        if is_protected or sr_count > 0 or comp.id < 50:
            legit_list.append(data)
        elif is_test_match:
            test_list.append(data)
        else:
            # Ambiguous: treat as legitimate by default
            legit_list.append(data)

    print("=" * 80)
    print(f"AUDIT SUMMARY: {len(all_companies)} Total Companies in Database")
    print(f"  -> Legitimate / Protected Companies Preserved: {len(legit_list)}")
    print(f"  -> Test / Demo Artifacts Identified: {len(test_list)}")
    print("=" * 80)

    print("\n[PRESERVED LEGITIMATE COMPANIES]")
    for item in legit_list:
        print(f"  ID={item['id']:<4} | {item['name']:<35} | DisplayID={str(item['display_id']):<12} | Users={item['users']} | Emps={item['employees']} | SRs={item['service_requests']}")

    print(f"\n[IDENTIFIED TEST / DEMO COMPANIES ({len(test_list)})]")
    for item in test_list[:25]:
        print(f"  ID={item['id']:<4} | {item['name']:<35} | DisplayID={str(item['display_id']):<12} | Users={item['users']} | Emps={item['employees']} | SRs={item['service_requests']}")
    if len(test_list) > 25:
        print(f"  ... and {len(test_list) - 25} more test companies.")

    if dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN ONLY. No data modified. Run with --execute to perform safe cleanup.")
        print("=" * 80)
        return

    print("\n" + "=" * 80)
    print("EXECUTING SAFE CLEANUP OF CONFIRMED TEST ARTIFACTS...")
    print("=" * 80)

    test_company_ids = [t["id"] for t in test_list]

    with transaction.atomic():
        # 1. Clean up join requests pointing to test companies
        deleted_jrs, _ = WorkforceProviderJoinRequest.objects.filter(provider_id__in=test_company_ids).delete()
        print(f"Deleted {deleted_jrs} test join requests.")

        # 2. Deactivate all test companies (is_active=False) so public APIs exclude them
        deactivated = Company.objects.filter(id__in=test_company_ids).update(is_active=False)
        print(f"Deactivated {deactivated} test companies (is_active=False).")

    print("\n" + "=" * 80)
    print("CLEANUP COMPLETED! Verifying remaining database records...")
    rem_comps = Company.objects.all().count()
    rem_active = Company.objects.filter(is_active=True).count()
    print(f"Remaining Total Companies: {rem_comps} (Active: {rem_active})")
    print("=" * 80)




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit and cleanup test provider data.")
    parser.add_argument("--execute", action="store_true", help="Execute cleanup")
    args = parser.parse_args()

    audit_companies(dry_run=not args.execute)
