"""
accounts/platform.py

Shared platform admin identity resolution.
Used identically across accounts login/me responses and workforce API authorization checks.
"""


def is_platform_admin_user(user) -> bool:
    """
    Evaluates whether an authenticated user is a platform administrator.
    A user is considered a platform administrator if:
      - is_superuser is True
      - OR (is_staff is True and company_id == 1)
      - OR role in ('superadmin', 'platform_admin')
      - OR (role in ('admin', 'manager') and company_id == 1)
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    company_id = getattr(user, "company_id", None)
    if company_id is None and hasattr(user, "company") and user.company is not None:
        company_id = getattr(user.company, "id", None)

    role = str(getattr(user, "role", "") or "").strip().lower()
    is_super = bool(getattr(user, "is_superuser", False))
    is_staff = bool(getattr(user, "is_staff", False))

    return bool(
        is_super
        or (is_staff and company_id == 1)
        or role in ("superadmin", "platform_admin")
        or (role in ("admin", "manager") and company_id == 1)
    )
