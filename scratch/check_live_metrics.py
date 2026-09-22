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

from workforce_api._head_views_tmp import SellerHubMetricsView as HeadSellerHubMetricsView
from workforce_api.views_seller_hub import SellerHubMetricsView as WorkingSellerHubMetricsView

User = get_user_model()
factory = APIRequestFactory()

def run():
    print('=' * 80)
    print('READ-ONLY LIVE CHECK ON SHARED POSTGRESQL')
    print('=' * 80)
    print(f'DB Engine: {connection.settings_dict["ENGINE"]}')
    print(f'DB Vendor: {connection.vendor}')
    assert connection.vendor == 'postgresql', 'Expected postgresql for live check'

    head_view = HeadSellerHubMetricsView.as_view()
    working_view = WorkingSellerHubMetricsView.as_view()

    # 1. Seller vignesh@caldim.in (company 3)
    user_vignesh = User.objects.get(email='vignesh@caldim.in')
    print(f'\n[1] Seller: vignesh@caldim.in (User ID: {user_vignesh.id}, Company ID: {user_vignesh.company_id})')

    # Working Tree
    req_w1 = factory.get('/api/workforce/seller-hub/metrics/')
    force_authenticate(req_w1, user=user_vignesh)
    t0 = time.perf_counter()
    with CaptureQueriesContext(connection) as ctx_w1:
        res_w1 = working_view(req_w1)
    t_w1 = time.perf_counter() - t0
    q_w1 = len(ctx_w1.captured_queries)

    # HEAD
    req_h1 = factory.get('/api/workforce/seller-hub/metrics/')
    force_authenticate(req_h1, user=user_vignesh)
    t0 = time.perf_counter()
    with CaptureQueriesContext(connection) as ctx_h1:
        res_h1 = head_view(req_h1)
    t_h1 = time.perf_counter() - t0
    q_h1 = len(ctx_h1.captured_queries)

    h1_json = json.dumps(res_h1.data, indent=2, sort_keys=True)
    w1_json = json.dumps(res_w1.data, indent=2, sort_keys=True)
    identical1 = (h1_json == w1_json)
    print(f'Result: {"IDENTICAL" if identical1 else "NOT IDENTICAL"}')
    if not identical1:
        diff1 = list(difflib.unified_diff(h1_json.splitlines(keepends=True), w1_json.splitlines(keepends=True), fromfile="HEAD", tofile="WORKING"))
        print("".join(diff1))
    print(f'HEAD View:        {q_h1} queries | {t_h1*1000:.2f} ms')
    print(f'WORKING View:     {q_w1} queries | {t_w1*1000:.2f} ms')

    # 2. Platform Admin (non-test admin, user id 5)
    user_admin = User.objects.get(id=5)
    print(f'\n[2] Platform Admin User (User ID: {user_admin.id})')

    # Working Tree
    req_w2 = factory.get('/api/workforce/seller-hub/metrics/')
    force_authenticate(req_w2, user=user_admin)
    t0 = time.perf_counter()
    with CaptureQueriesContext(connection) as ctx_w2:
        res_w2 = working_view(req_w2)
    t_w2 = time.perf_counter() - t0
    q_w2 = len(ctx_w2.captured_queries)

    # HEAD
    req_h2 = factory.get('/api/workforce/seller-hub/metrics/')
    force_authenticate(req_h2, user=user_admin)
    t0 = time.perf_counter()
    with CaptureQueriesContext(connection) as ctx_h2:
        res_h2 = head_view(req_h2)
    t_h2 = time.perf_counter() - t0
    q_h2 = len(ctx_h2.captured_queries)

    h2_json = json.dumps(res_h2.data, indent=2, sort_keys=True)
    w2_json = json.dumps(res_w2.data, indent=2, sort_keys=True)
    identical2 = (h2_json == w2_json)
    print(f'Result: {"IDENTICAL" if identical2 else "NOT IDENTICAL"}')
    if not identical2:
        diff2 = list(difflib.unified_diff(h2_json.splitlines(keepends=True), w2_json.splitlines(keepends=True), fromfile="HEAD", tofile="WORKING"))
        print("".join(diff2))
    print(f'HEAD View:        {q_h2} queries | {t_h2*1000:.2f} ms')
    print(f'WORKING View:     {q_w2} queries | {t_w2*1000:.2f} ms')

if __name__ == '__main__':
    run()
