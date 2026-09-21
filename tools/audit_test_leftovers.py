import os
import sys
from datetime import datetime

# Add vendor/backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vendor", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure SEVO_E2E_SQLITE_PATH is removed so we connect directly to PostgreSQL
if "SEVO_E2E_SQLITE_PATH" in os.environ:
    del os.environ["SEVO_E2E_SQLITE_PATH"]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from django.db import connection, ProgrammingError, OperationalError
from django.db.models import Min, Max
from django.db.models.deletion import Collector, ProtectedError
from django.contrib.auth import get_user_model
from companies.models import Company
from employees.models import Employee
from workforce_api.models import (
    SellerHubCategory,
    SellerProduct,
    SellerInventory,
    SellerInventoryBatch,
    SellerInventoryMovement,
    SellerOrder,
    SellerOrderItem,
    SellerOrderAuditLog,
    SellerOrderStatusOutbox,
    SellerReturn,
    SellerReturnItem,
    SellerReturnAuditLog,
    SellerClaim,
    SellerClaimAuditLog,
)

User = get_user_model()

# STRICT TIGHT REGEX PATTERNS
COMPANY_TIGHT_REGEX = r"^(organic-farms|daily-fresh)-[0-9a-f]{6}$"
USER_TIGHT_REGEX = r"^(seller_orders_a_|seller_orders_b_|orders_superadmin_)[0-9a-f]{6}$"
CATEGORY_TIGHT_REGEX = r"^(groceries|oils)-[0-9a-f]{6}$"
SKU_TIGHT_REGEX = r"^(COC-OIL-1L|GND-OIL-1L|SUN-OIL-1L)-[0-9a-f]{6}$"

# LOOSE REGEX PATTERNS (FOR COMPARISON & ANOMALY DETECTION)
COMPANY_LOOSE_REGEX = r"^(organic-farms|daily-fresh)-"
USER_LOOSE_REGEX = r"^(seller_orders_a_|seller_orders_b_|orders_superadmin_)"
CATEGORY_LOOSE_REGEX = r"^(groceries|oils)-"
SKU_LOOSE_REGEX = r"^(COC-OIL-1L|GND-OIL-1L|SUN-OIL-1L)-"

# ALLOW-LIST OF MODEL NAMES ALLOWED IN CASCADE
ALLOW_LIST_MODEL_NAMES = {
    "SellerInventory",
    "SellerInventoryMovement",
    "SellerInventoryBatch",
    "SellerOrder",
    "SellerOrderItem",
    "SellerOrderStatusOutbox",
    "SellerOrderAuditLog",
    "SellerProduct",
    "SellerHubCategory",
    "User",
    "Company",
}

class SafeCollector(Collector):
    """
    Subclass of Django's Collector that checks table existence in DB before evaluating reverse relations.
    """
    _existing_tables = None

    def _get_existing_tables(self):
        if SafeCollector._existing_tables is None:
            with connection.cursor() as cursor:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                SafeCollector._existing_tables = {row[0] for row in cursor.fetchall()}
        return SafeCollector._existing_tables

    def related_objects(self, related_model, related_fields, objs):
        table_name = related_model._meta.db_table
        if table_name not in self._get_existing_tables():
            return related_model._default_manager.none()
        return super().related_objects(related_model, related_fields, objs)

def run_audit():
    db_settings = connection.settings_dict
    host = db_settings.get("HOST", "unknown")
    name = db_settings.get("NAME", "unknown")
    engine = db_settings.get("ENGINE", "unknown")

    print("=" * 80)
    print("REFINED CLEANUP DRY-RUN & CASCADE AUDIT (READ-ONLY)")
    print("=" * 80)
    print(f"DATABASE HOST: {host}")
    print(f"DATABASE NAME: {name}")
    print(f"DATABASE ENGINE: {engine}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # D1. TIGHT PATTERN MATCHES
    # -------------------------------------------------------------------------
    tight_companies = Company.objects.filter(slug__regex=COMPANY_TIGHT_REGEX)
    tight_users = User.objects.filter(username__regex=USER_TIGHT_REGEX)
    tight_categories = SellerHubCategory.objects.filter(slug__regex=CATEGORY_TIGHT_REGEX)
    tight_products = SellerProduct.objects.filter(sku__regex=SKU_TIGHT_REGEX)
    tight_orders = SellerOrder.objects.filter(company__in=tight_companies)

    print("\nD1. TIGHT-PATTERN MATCH COUNTS:")
    print(f"   - Tight Companies ({COMPANY_TIGHT_REGEX}): {tight_companies.count()}")
    print(f"   - Tight Users ({USER_TIGHT_REGEX}): {tight_users.count()}")
    print(f"   - Tight Categories ({CATEGORY_TIGHT_REGEX}): {tight_categories.count()}")
    print(f"   - Tight Products ({SKU_TIGHT_REGEX}): {tight_products.count()}")
    print(f"   - Tight Orders (company in tight companies): {tight_orders.count()}")

    # -------------------------------------------------------------------------
    # D2. ROWS CAUGHT BY LOOSE PATTERN BUT NOT TIGHT PATTERN [REVIEW: DO NOT DELETE]
    # -------------------------------------------------------------------------
    loose_not_tight_companies = Company.objects.filter(slug__regex=COMPANY_LOOSE_REGEX).exclude(slug__regex=COMPANY_TIGHT_REGEX)
    loose_not_tight_users = User.objects.filter(username__regex=USER_LOOSE_REGEX).exclude(username__regex=USER_TIGHT_REGEX)
    loose_not_tight_cats = SellerHubCategory.objects.filter(slug__regex=CATEGORY_LOOSE_REGEX).exclude(slug__regex=CATEGORY_TIGHT_REGEX)
    loose_not_tight_prods = SellerProduct.objects.filter(sku__regex=SKU_LOOSE_REGEX).exclude(sku__regex=SKU_TIGHT_REGEX)

    print("\nD2. ROWS CAUGHT BY LOOSE PATTERN BUT NOT TIGHT PATTERN [REVIEW: DO NOT DELETE]:")
    print(f"   - Non-tight Companies count: {loose_not_tight_companies.count()}")
    for comp in loose_not_tight_companies:
        comp_users = User.objects.filter(company=comp)
        comp_prods_count = SellerProduct.objects.filter(company=comp).count()
        comp_orders_count = SellerOrder.objects.filter(company=comp).count()
        user_details = [
            {
                "username": u.username,
                "last_login": u.last_login,
                "is_active": u.is_active,
                "fails_test_pattern": not bool(u.username.startswith(("seller_orders_a_", "seller_orders_b_", "orders_superadmin_")))
            }
            for u in comp_users
        ]
        print(f"     * Company ID={comp.id}, Slug='{comp.slug}', Name='{comp.company_name}', Created={comp.created_at}")
        print(f"       Products: {comp_prods_count}, Orders: {comp_orders_count}")
        print(f"       Users ({len(user_details)}): {user_details}")

    if loose_not_tight_users.count() > 0:
        print(f"   - Non-tight Users count: {loose_not_tight_users.count()}")
        for u in loose_not_tight_users:
            print(f"     * User ID={u.id}, Username='{u.username}', Joined={u.date_joined}, Company ID={u.company_id}")

    if loose_not_tight_cats.count() > 0:
        print(f"   - Non-tight Categories count: {loose_not_tight_cats.count()}")
        for c in loose_not_tight_cats:
            print(f"     * Category ID={c.id}, Slug='{c.slug}', Name='{c.name}'")

    if loose_not_tight_prods.count() > 0:
        print(f"   - Non-tight Products count: {loose_not_tight_prods.count()}")
        for p in loose_not_tight_prods:
            print(f"     * Product ID={p.id}, SKU='{p.sku}', Title='{p.title}', Company ID={p.company_id}")

    # -------------------------------------------------------------------------
    # D3. OVERLAP ANALYSIS: TIGHT-MATCHED COMPANIES VS TIGHT USERS
    # -------------------------------------------------------------------------
    users_in_tight_companies = User.objects.filter(company__in=tight_companies)
    count_users_in_tight_companies = users_in_tight_companies.count()
    count_tight_users = tight_users.count()

    users_in_comp_not_tight_user = users_in_tight_companies.exclude(username__regex=USER_TIGHT_REGEX)
    tight_users_not_in_tight_comp = tight_users.exclude(company__in=tight_companies)

    print("\nD3. USER OVERLAP ANALYSIS:")
    print(f"   - Users belonging to tight-matched companies: {count_users_in_tight_companies}")
    print(f"   - Users matching tight username pattern: {count_tight_users}")
    print(f"   - Users in tight companies but NOT matching tight username: {users_in_comp_not_tight_user.count()}")
    if users_in_comp_not_tight_user.count() > 0:
        print(f"     Samples: {list(users_in_comp_not_tight_user.values('id', 'username', 'company_id')[:5])}")
    print(f"   - Tight username users NOT in tight companies (e.g. orders_superadmin without company): {tight_users_not_in_tight_comp.count()}")
    if tight_users_not_in_tight_comp.count() > 0:
        print(f"     Samples: {list(tight_users_not_in_tight_comp.values('id', 'username', 'company_id')[:5])}")

    # -------------------------------------------------------------------------
    # D4. CASCADE COLLECTION (COLLECTOR DRY RUN - NO DELETE CALLED)
    # -------------------------------------------------------------------------
    print("\nD4. DJANGO CASCADE COLLECTOR DRY RUN (READ-ONLY):")
    collector = SafeCollector(using=connection.alias)
    all_protected = set()

    # Collect bottom-up to capture entire cascading hierarchy
    for qs in [tight_orders, tight_products, tight_categories, tight_users, tight_companies]:
        if qs.exists():
            try:
                collector.collect(list(qs))
            except ProtectedError as pe:
                all_protected.update(pe.protected_objects)

    print("   Cascaded deletion collection results per db_table:")
    outside_allow_list = []
    for model, instances in collector.data.items():
        table_name = model._meta.db_table
        model_name = model.__name__
        count = len(instances)
        is_allowed = model_name in ALLOW_LIST_MODEL_NAMES
        flag = "" if is_allowed else " [FLAGGED: OUTSIDE ALLOW-LIST!]"
        if not is_allowed:
            outside_allow_list.append((model_name, table_name, count))
        print(f"     - {table_name} ({model_name}): {count} instance(s){flag}")

    # Protected relations check
    print(f"\n   Protected Objects Encountered: {len(all_protected)}")
    if all_protected:
        print("   [PROTECTED RELATION WARNING]: The following instances are protected by on_delete=PROTECT:")
        protected_by_type = {}
        for obj in all_protected:
            protected_by_type.setdefault(obj.__class__.__name__, []).append(str(obj))
        for cls_name, items in protected_by_type.items():
            print(f"     * {cls_name} ({len(items)} instances): sample: {items[:3]}")

    # Allow-list validation summary
    if outside_allow_list:
        print(f"\n   [FLAGGED WARNING] Models outside allow-list ({len(outside_allow_list)}):")
        for m_name, t_name, cnt in outside_allow_list:
            print(f"     * {m_name} ({t_name}): {cnt} rows")
    else:
        print("\n   Allow-List Check: 100% of collected cascading models are inside the safe allow-list.")

    print("=" * 80)

if __name__ == "__main__":
    run_audit()
