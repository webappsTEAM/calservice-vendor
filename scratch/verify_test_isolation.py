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

from companies.models import Company
from django.contrib.auth import get_user_model
from workforce_api.models import SellerHubCategory

User = get_user_model()

def get_counts():
    return {
        "Company": Company.objects.count(),
        "User": User.objects.count(),
        "SellerHubCategory": SellerHubCategory.objects.count(),
    }

print("BEFORE TEST RUN (PostgreSQL):", get_counts())

# Now run test_phase10b_category_feed.py and test_seller_hub_category_separation.py
import subprocess

py_exe = os.path.abspath(os.path.join(backend_dir, ".venv", "Scripts", "python.exe"))

print("\n--- Running test_phase10b_category_feed.py ---")
res10b = subprocess.run([py_exe, "test_phase10b_category_feed.py"], cwd=backend_dir, capture_output=True, text=True)
lines10b = res10b.stdout.strip().split("\n")
for l in lines10b[-5:]:
    print(" ", l)

print("\n--- Running test_seller_hub_category_separation.py ---")
res_sep = subprocess.run([py_exe, "test_seller_hub_category_separation.py"], cwd=backend_dir, capture_output=True, text=True)
lines_sep = res_sep.stdout.strip().split("\n")
for l in lines_sep[-5:]:
    print(" ", l)

print("\nAFTER TEST RUN (PostgreSQL):", get_counts())
