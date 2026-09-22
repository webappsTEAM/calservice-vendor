import os
import sys
import time
import json
import difflib

sys.path.insert(0, 'vendor/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')

import django
django.setup()

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from workforce_api._head_views_tmp import AdminSellerHubCategoryListView as HeadCatListView
from workforce_api.views_seller_hub import AdminSellerHubCategoryListView as WorkingCatListView

User = get_user_model()
factory = APIRequestFactory()

def run():
    print('=' * 80)
    print('READ-ONLY LIVE CHECK: GET seller-hub/categories/ ON SHARED POSTGRESQL')
    print('=' * 80)
    print(f'DB Engine: {connection.settings_dict["ENGINE"]}')
    print(f'DB Vendor: {connection.vendor}')
    assert connection.vendor == 'postgresql', 'Expected postgresql for live check'

    head_view = HeadCatListView.as_view()
    working_view = WorkingCatListView.as_view()

    user_admin = User.objects.get(id=5)
    print(f'Platform Admin User (User ID: {user_admin.id})')

    # Working Tree
    req_w = factory.get('/api/workforce/seller-hub/categories/')
    force_authenticate(req_w, user=user_admin)
    t0 = time.perf_counter()
    with CaptureQueriesContext(connection) as ctx_w:
        res_w = working_view(req_w)
    t_w = time.perf_counter() - t0
    q_w = len(ctx_w.captured_queries)

    # HEAD
    req_h = factory.get('/api/workforce/seller-hub/categories/')
    force_authenticate(req_h, user=user_admin)
    t0 = time.perf_counter()
    with CaptureQueriesContext(connection) as ctx_h:
        res_h = head_view(req_h)
    t_h = time.perf_counter() - t0
    q_h = len(ctx_h.captured_queries)

    h_json = json.dumps(res_h.data, indent=2, sort_keys=True)
    w_json = json.dumps(res_w.data, indent=2, sort_keys=True)
    identical = (h_json == w_json)
    print(f'Result: {"IDENTICAL" if identical else "NOT IDENTICAL"}')
    if not identical:
        diff = list(difflib.unified_diff(h_json.splitlines(keepends=True), w_json.splitlines(keepends=True), fromfile="HEAD", tofile="WORKING"))
        print("".join(diff[:50]))
    print(f'HEAD View:        {q_h} queries | {t_h*1000:.2f} ms')
    print(f'WORKING View:     {q_w} queries | {t_w*1000:.2f} ms')
    print(f'Total categories returned: {len(res_w.data)}')

if __name__ == '__main__':
    run()
