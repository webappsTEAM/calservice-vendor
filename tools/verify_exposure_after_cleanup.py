#!/usr/bin/env python3
"""
tools/verify_exposure_after_cleanup.py

Read-only verification tool that evaluates the Marketplace Category Feed and
Sellable Products Queryset from the perspective of the Customer marketplace integration.
Reads the integration secret securely from Django settings without printing secrets.
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

from django.conf import settings
from django.db import connection
from rest_framework.test import APIRequestFactory
from workforce_api.models import SellerHubCategory, SellerProduct
from workforce_api.views_marketplace_integration import (
    MarketplaceCategoryFeedView,
    get_active_seller_category_ids,
    get_sellable_products_queryset,
)


def main():
    settings_dict = connection.settings_dict
    db_host = settings_dict.get("HOST") or "localhost"
    db_name = settings_dict.get("NAME") or "unknown"
    db_engine = settings_dict.get("ENGINE", "").split(".")[-1]

    print("=" * 80)
    print(f"CUSTOMER EXPOSURE AUDIT: {db_engine.upper()} @ {db_host} | DATABASE: {db_name}")
    print("=" * 80)

    # 1. Evaluate MarketplaceCategoryFeedView
    secret = getattr(settings, "WORKFORCE_WEBHOOK_SECRET", None) or getattr(settings, "WORKFORCE_API_KEY", None)
    if not secret:
        print("[-] ERROR: No WORKFORCE_WEBHOOK_SECRET configured in settings.")
        sys.exit(1)

    factory = APIRequestFactory()
    view = MarketplaceCategoryFeedView.as_view()
    request = factory.get(
        "/api/workforce/marketplace/categories/?tree=false&hide_empty=false",
        HTTP_AUTHORIZATION=f"Bearer {secret}",
    )
    response = view(request)

    if response.status_code != 200:
        print(f"[-] ERROR: Category Feed returned status {response.status_code}: {response.data}")
        sys.exit(1)

    feed_cats = response.data if isinstance(response.data, list) else response.data.get("categories", [])
    total_feed_cats = len(feed_cats)
    test_feed_cats = [c for c in feed_cats if any(c.get("slug", "").startswith(p) for p in ["groceries-", "oils-"])]
    real_feed_cats = [c for c in feed_cats if not any(c.get("slug", "").startswith(p) for p in ["groceries-", "oils-"])]

    # 2. Evaluate Sellable Products Queryset
    active_cat_ids = get_active_seller_category_ids()
    sellable_qs = get_sellable_products_queryset(active_cat_ids)
    total_sellable = sellable_qs.count()
    test_sellable = sellable_qs.filter(sku__regex=r"^(COC-OIL-1L|GND-OIL-1L|SUN-OIL-1L)-").count()
    real_sellable = total_sellable - test_sellable

    print(f"[+] Marketplace Category Feed (HTTP {response.status_code} OK):")
    print(f"    - Total Categories Returned: {total_feed_cats}")
    print(f"    - Test Categories:           {len(test_feed_cats)}")
    print(f"    - Real / Market Categories:  {len(real_feed_cats)}")
    if real_feed_cats:
        print(f"    - Real Category Slugs:       {[c.get('slug') for c in real_feed_cats]}")

    print(f"\n[+] Sellable Products Queryset (get_sellable_products_queryset):")
    print(f"    - Total Sellable Products:   {total_sellable}")
    print(f"    - Test Products:             {test_sellable}")
    print(f"    - Real / Market Products:    {real_sellable}")

    print("=" * 80)


if __name__ == "__main__":
    main()
