"""
workforce-app/backend/workforce_api/services/provider_service.py
Reusable business logic for creating Service Providers and Primary Provider Admins.
Shared between Superadmin creation and self-service registration.
"""
import uuid
from django.db import transaction
from django.utils.text import slugify
from companies.models import Company
from accounts.models import User


def create_service_provider_with_admin(data):
    """
    Atomically creates a Company and its primary Service Provider Admin user.
    Enforces all invariants:
    - Unique display_id (e.g. PROV-XXXXXX)
    - Unique slug
    - is_active = True
    - User role = 'service_provider_admin'
    - User company = created_company
    - User is_staff = True
    - User is_superuser = False
    - No Employee record is created
    """
    with transaction.atomic():
        # 1. Prepare unique display_id and slug
        display_id = data.get("display_id")
        if not display_id:
            display_id = f"PROV-{uuid.uuid4().hex[:6].upper()}"
            while Company.objects.filter(display_id=display_id).exists():
                display_id = f"PROV-{uuid.uuid4().hex[:6].upper()}"

        slug_base = slugify(data["company_name"]) or "provider"
        slug = slug_base
        counter = 1
        while Company.objects.filter(slug=slug).exists():
            slug = f"{slug_base}-{uuid.uuid4().hex[:4]}"
            counter += 1
            if counter > 10:
                slug = f"{slug_base}-{uuid.uuid4().hex[:8]}"
                break

        # Format address with city/state if provided
        address_parts = [data.get("address", "").strip()]
        city_state = ", ".join(filter(None, [data.get("city", "").strip(), data.get("state", "").strip()]))
        if city_state:
            address_parts.append(city_state)
        country = data.get("country") or data.get("primary_country") or "US"
        if country and country != "US":
            address_parts.append(country)
        full_address = "\n".join(filter(None, address_parts))

        # 2. Create the Company record
        company = Company.objects.create(
            company_name=data["company_name"].strip(),
            display_id=display_id,
            slug=slug,
            address=full_address,
            industry=data.get("industry", "").strip(),
            website=data.get("website", "").strip(),
            primary_country=country[:2].upper() if country else "US",
            is_active=True,
        )

        # 3. Create the primary Service Provider Admin user
        admin_username = data.get("username") or data.get("admin_username")
        admin_email = data.get("admin_email") or data.get("email")
        admin_password = data.get("password") or data.get("admin_password")
        admin_first_name = data.get("first_name") or data.get("admin_first_name") or ""
        admin_last_name = data.get("last_name") or data.get("admin_last_name") or ""
        admin_phone = data.get("admin_phone") or data.get("phone") or None

        admin_user = User.objects.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            first_name=admin_first_name,
            last_name=admin_last_name,
            phone=admin_phone,
            mobile_number=admin_phone or "",
            role="service_provider_admin",
            company=company,
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )

        return company, admin_user
