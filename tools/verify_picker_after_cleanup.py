#!/usr/bin/env python3
"""
tools/verify_picker_after_cleanup.py

Read-only verification tool that queries the Seller Hub Category Picker endpoint
(parent_id=null) authenticated as the real non-test seller vignesh@caldim.in.
Performs 0 writes/updates.
"""

import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vendor", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if "SEVO_E2E_SQLITE_PATH" in os.environ:
    del os.environ["SEVO_E2E_SQLITE_PATH"]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from django.db import connection
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from workforce_api.views_seller_hub import SellerCatalogCategoryListView

User = get_user_model()


def main():
    settings_dict = connection.settings_dict
    db_host = settings_dict.get("HOST") or "localhost"
    db_name = settings_dict.get("NAME") or "unknown"
    db_engine = settings_dict.get("ENGINE", "").split(".")[-1]

    print("=" * 80)
    print(f"VERIFY PICKER: {db_engine.upper()} @ {db_host} | DATABASE: {db_name}")
    print("=" * 80)

    # 1. Resolve seller user
    user = User.objects.filter(email="vignesh@caldim.in").first()
    if not user:
        user = User.objects.filter(username="vignesh@caldim.in").first()

    if not user:
        print("[-] ERROR: Seller user 'vignesh@caldim.in' not found in database.")
        sys.exit(1)

    print(f"[*] Authenticated Seller: {user.username} (ID: {user.id}, Company: {user.company})")

    # 2. Call SellerCatalogCategoryListView with parent_id=null
    factory = APIRequestFactory()
    view = SellerCatalogCategoryListView.as_view()
    request = factory.get("/api/workforce/seller-hub/categories/picker/?parent_id=null")
    force_authenticate(request, user=user)

    response = view(request)

    if response.status_code != 200:
        print(f"[-] ERROR: Picker returned status {response.status_code}: {response.data}")
        sys.exit(1)

    roots = response.data if isinstance(response.data, list) else response.data.get("results", [])

    print(f"[+] Picker Status Code: {response.status_code} OK")
    print(f"[+] Total Root Categories Returned: {len(roots)}")
    print("\nRoot Categories List:")
    for idx, r in enumerate(roots, 1):
        is_test = "-" in r.get("slug", "") and any(r.get("slug", "").startswith(p) for p in ["groceries-", "oils-"])
        tag = "[TEST]" if is_test else "[REAL/MKT]"
        print(f"  {idx:3d}. {tag:10s} ID: {r.get('id'):<5d} Name: '{r.get('name')}' (Slug: {r.get('slug')})")

    print("=" * 80)


if __name__ == "__main__":
    main()
