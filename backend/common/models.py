"""
workforce-app/backend/common/models.py
Reusable row-level company isolation manager and querysets.
"""
from django.db import models


class CompanyScopedQuerySet(models.QuerySet):
    company_field = "company"

    def for_company(self, company):
        if company is None:
            return self.none()
        return self.filter(**{self.company_field: company})

    def visible_to(self, user):
        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        # SUPERADMIN: global access across all providers and independent records
        if getattr(user, "is_superuser", False) or str(getattr(user, "role", "")).lower() in ["superadmin", "super_admin"]:
            return self
        # SERVICE_PROVIDER_ADMIN: scoped strictly to user's provider
        company = getattr(user, "company", None)
        if company is None:
            return self.none()
        return self.for_company(company)

    def active(self):
        if any(f.name == "is_active" for f in self.model._meta.get_fields()):
            return self.filter(is_active=True)
        return self


def CompanyScopedManager(company_field: str = "company"):
    queryset_cls = type(
        f"CompanyScopedQuerySet_{company_field}",
        (CompanyScopedQuerySet,),
        {"company_field": company_field},
    )
    return models.Manager.from_queryset(queryset_cls)()
