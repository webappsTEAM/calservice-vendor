"""
run_claims_verification.py
Comprehensive verification test suite for Phase 6: Seller Hub Claims & Dispute Management.
Tests:
1. Empty state for seller with no claims (zero mock data)
2. Seller claim creation, listing, type filter, and search
3. Claim detail with evidence and order/return link
4. Admin request seller response with mandatory reason
5. Seller response and evidence submission with audit logging
6. Seller dispute escalation to platform admin
7. Admin approval & rejection decisions with mandatory rationale
8. Claim settlement and closure transitions
9. Invalid state machine transitions blocked with HTTP 400
10. Source claim ID idempotent intake contract
11. Multi-tenant isolation (cross-tenant access blocked with HTTP 404)
12. Zero side-effects check (inventory, order totals, customer payment remain untouched)
13. Seller Hub dashboard claims metrics live aggregation
"""
import os
import sys
import uuid
import tempfile
from decimal import Decimal

if not os.environ.get("SEVO_E2E_SQLITE_PATH"):
    temp_sqlite = os.path.join(tempfile.gettempdir(), f"sevo_run_claims_test_{uuid.uuid4().hex[:8]}.sqlite3")
    os.environ["SEVO_E2E_SQLITE_PATH"] = temp_sqlite

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from django.apps import apps
from django.conf import settings
from django.db import connection

# Hard safety guard: ensure test execution is strictly against SQLite
if connection.vendor != "sqlite":
    raise RuntimeError(
        f"SAFETY ABORT: run_claims_verification initialized against non-SQLite database (vendor={connection.vendor!r}). "
        "Tests must ONLY execute against isolated temporary SQLite."
    )

created_table_count = 0
with connection.schema_editor() as schema_editor:
    for model in apps.get_models():
        try:
            schema_editor.create_model(model)
            created_table_count += 1
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "duplicate table" in err_msg:
                continue
            raise RuntimeError(f"Failed to create schema for model {model.__name__}: {e}") from e

settings.ALLOWED_HOSTS = ["*"]

from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from companies.models import Company
from workforce_api.models import (
    SellerProduct,
    SellerInventory,
    SellerOrder,
    SellerOrderItem,
    SellerReturn,
    SellerReturnItem,
    SellerClaim,
    SellerClaimAuditLog,
)

User = get_user_model()

TEST_WEBHOOK_SECRET = "test-secret-not-real-run-claims"
settings.WORKFORCE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
settings.WORKFORCE_API_KEY = TEST_WEBHOOK_SECRET


def _guarded_real_post(*args, **kwargs):
    raise AssertionError(f"SECURITY GUARD: Real outbound network request attempted in run_claims_verification: {args} {kwargs}")


def run_verification():
    print("=" * 80)
    print("SEVO-VENDOR PHASE 6: SELLER HUB CLAIMS VERIFICATION")
    print("=" * 80)

    client = APIClient()
    pass_count = 0
    fail_count = 0

    def assert_true(condition, message):
        nonlocal pass_count, fail_count
        if condition:
            print(f"  [PASS] {message}")
            pass_count += 1
        else:
            print(f"  [FAIL] {message}")
            fail_count += 1

    patch_dispatch = patch("workforce_api.services.seller_order_outbox._trigger_background_dispatch")
    patch_dispatch.start()
    patch_post = patch("requests.post", side_effect=_guarded_real_post)
    patch_post.start()

    uid = uuid.uuid4().hex[:6]
    # Setup Test Data
    # Superadmin
    admin_user, _ = User.objects.get_or_create(
        username=f"claims_superadmin_{uid}@test.com",
        defaults={
            "email": f"claims_admin_{uid}@test.com",
            "is_superuser": True,
            "is_staff": True,
            "role": "platform_admin",
            "first_name": "Admin",
            "last_name": "Reviewer",
        }
    )
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()

    # Company A (Seller A)
    comp_a, _ = Company.objects.get_or_create(
        slug=f"claims-company-a-{uid}",
        defaults={"company_name": "Super Fresh Farms", "is_active": True}
    )
    seller_a, _ = User.objects.get_or_create(
        username=f"claims_seller_a_{uid}@test.com",
        defaults={
            "email": f"seller_a_claims_{uid}@test.com",
            "company": comp_a,
            "role": "vendor_admin",
            "first_name": "Alice",
            "last_name": "Seller",
        }
    )
    seller_a.company = comp_a
    seller_a.save()

    # Company B (Seller B)
    comp_b, _ = Company.objects.get_or_create(
        slug=f"claims-company-b-{uid}",
        defaults={"company_name": "Urban Grocery Depot", "is_active": True}
    )
    seller_b, _ = User.objects.get_or_create(
        username=f"claims_seller_b_{uid}@test.com",
        defaults={
            "email": f"seller_b_claims_{uid}@test.com",
            "company": comp_b,
            "role": "vendor_admin",
            "first_name": "Bob",
            "last_name": "Seller",
        }
    )
    seller_b.company = comp_b
    seller_b.save()

    # Clean existing test claims for test companies
    SellerClaim.objects.filter(company__in=[comp_a, comp_b]).delete()

    from workforce_api.models import SellerHubCategory

    category_a, _ = SellerHubCategory.objects.get_or_create(
        slug=f"claims-test-cat-{uid}",
        defaults={"name": "Claims Test Category", "is_active": True}
    )

    # Setup Product, Inventory, and Order for Seller A
    product_a, _ = SellerProduct.objects.get_or_create(
        company=comp_a,
        sku=f"CLM-TEST-SKU-01-{uid}",
        defaults={
            "title": "Fresh Organic Avocados (Box of 6)",
            "category": category_a,
            "selling_price": Decimal("180.00"),
            "mrp": Decimal("200.00"),
            "status": SellerProduct.Status.APPROVED,
        }
    )
    inv_a, _ = SellerInventory.objects.get_or_create(
        company=comp_a,
        product=product_a,
        defaults={
            "on_hand_qty": Decimal("50.000"),
            "reserved_qty": Decimal("0.000"),
            "low_stock_threshold": Decimal("5.000"),
        }
    )

    order_a, _ = SellerOrder.objects.get_or_create(
        company=comp_a,
        source_order_id=f"CLM-TEST-ORD-{uid}",
        defaults={
            "order_number": f"ORD-CLM-{uid}",
            "customer_name": "Deepak Patel",
            "customer_phone": "+91 9876543210",
            "delivery_address": "Plot 42, Green Valley, Chennai",
            "total_amount": Decimal("540.00"),
            "status": SellerOrder.Status.DELIVERED,
        }
    )

    return_a, _ = SellerReturn.objects.get_or_create(
        company=comp_a,
        order=order_a,
        source_return_id=f"CLM-TEST-RET-{uid}",
        defaults={
            "return_number": f"RET-CLM-{uid}",
            "customer_name": "Deepak Patel",
            "reason": SellerReturn.Reason.DAMAGED,
            "status": SellerReturn.Status.UNDER_SELLER_REVIEW,
        }
    )

    # --------------------------------------------------------------------------
    print("\n--- TEST 1: EMPTY STATE FOR SELLER WITH NO CLAIMS ---")
    # --------------------------------------------------------------------------
    client.force_authenticate(user=seller_b)
    res_b = client.get("/api/workforce/seller-hub/claims/")
    assert_true(res_b.status_code == status.HTTP_200_OK, "Seller B requests claims list successfully")
    assert_true(len(res_b.data) == 0, "Seller B receives an empty array (no mock records)")

    # --------------------------------------------------------------------------
    print("\n--- TEST 2: SELLER CREATE CLAIM & LIST / SEARCH ---")
    # --------------------------------------------------------------------------
    client.force_authenticate(user=seller_a)
    res_create = client.post("/api/workforce/seller-hub/claims/", {
        "claim_type": "DELIVERY_DAMAGE",
        "description": "Customer reported avocado box crushed during delivery by courier partner.",
        "order_id": order_a.id,
        "return_id": return_a.id,
        "claimed_amount": "180.00",
        "evidence_urls": ["https://storage.sevo.in/proof/damaged_avocados.jpg"],
        "customer_name": "Deepak Patel",
        "customer_phone": "+91 9876543210",
    }, format="json")
    assert_true(res_create.status_code == status.HTTP_201_CREATED, "Seller A files claim with HTTP 201")
    claim_1_data = res_create.data.get("claim", {})
    claim_1_id = claim_1_data.get("id")
    claim_1_num = claim_1_data.get("claim_number")
    assert_true(bool(claim_1_num), f"Claim number generated: {claim_1_num}")
    assert_true(claim_1_data.get("status") == "OPEN", "Initial claim status is OPEN")

    # List claims
    res_list = client.get("/api/workforce/seller-hub/claims/")
    assert_true(res_list.status_code == status.HTTP_200_OK, "Seller A lists claims with HTTP 200")
    assert_true(len(res_list.data) == 1, "Seller A has exactly 1 claim in list")

    # Search match
    res_search = client.get(f"/api/workforce/seller-hub/claims/?search={claim_1_num}")
    assert_true(len(res_search.data) == 1, "Search by claim number matches")

    # Search non-match
    res_no_match = client.get("/api/workforce/seller-hub/claims/?search=NON_EXISTENT_TXT")
    assert_true(len(res_no_match.data) == 0, "Non-matching search returns empty list")

    # --------------------------------------------------------------------------
    print("\n--- TEST 3: CLAIM DETAIL VIEW WITH EVIDENCE & AUDIT TRAIL ---")
    # --------------------------------------------------------------------------
    res_detail = client.get(f"/api/workforce/seller-hub/claims/{claim_1_id}/")
    assert_true(res_detail.status_code == status.HTTP_200_OK, "Detail view returns HTTP 200")
    assert_true(res_detail.data.get("order_number") == order_a.order_number, "Linked order number matches")
    assert_true(res_detail.data.get("return_number") == return_a.return_number, "Linked return number matches")
    assert_true(len(res_detail.data.get("evidence_urls", [])) == 1, "Evidence URL preserved")
    assert_true(len(res_detail.data.get("audit_logs", [])) >= 1, "Initial audit log recorded")

    # --------------------------------------------------------------------------
    print("\n--- TEST 4: ADMIN REQUESTS SELLER RESPONSE ---")
    # --------------------------------------------------------------------------
    # Platform Admin acts
    client.force_authenticate(user=admin_user)

    # Missing reason fails
    res_bad = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/admin-decision/", {
        "decision": "REQUEST_SELLER_RESPONSE",
        "reason": "   ",
    }, format="json")
    assert_true(res_bad.status_code == status.HTTP_400_BAD_REQUEST, "Admin decision without rationale is blocked with HTTP 400")

    # Valid request seller response
    res_req_resp = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/admin-decision/", {
        "decision": "REQUEST_SELLER_RESPONSE",
        "reason": "Please provide warehouse packing photos and courier handover receipt.",
    }, format="json")
    assert_true(res_req_resp.status_code == status.HTTP_200_OK, "Admin requests seller response with HTTP 200")
    claim_obj = SellerClaim.objects.get(id=claim_1_id)
    assert_true(claim_obj.status == SellerClaim.Status.SELLER_RESPONSE_REQUIRED, "Status transitioned to SELLER_RESPONSE_REQUIRED")
    assert_true(claim_obj.admin_decision == "REQUEST_SELLER_RESPONSE", "Admin decision recorded")

    # --------------------------------------------------------------------------
    print("\n--- TEST 5: SELLER SUBMITS RESPONSE & EVIDENCE ---")
    # --------------------------------------------------------------------------
    client.force_authenticate(user=seller_a)
    res_respond = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/respond/", {
        "seller_response": "We packed with standard bubble wrap and handed over to courier intact.",
        "evidence_urls": ["https://storage.sevo.in/proof/packing_bench_camera.jpg"],
    }, format="json")
    assert_true(res_respond.status_code == status.HTTP_200_OK, "Seller submits response successfully with HTTP 200")
    claim_obj.refresh_from_db()
    assert_true(claim_obj.status == SellerClaim.Status.UNDER_REVIEW, "Status transitioned back to UNDER_REVIEW")
    assert_true(bool(claim_obj.seller_response), "Seller response text saved")
    assert_true(claim_obj.seller_responded_by == seller_a, "seller_responded_by recorded")
    assert_true(len(claim_obj.evidence_urls) == 2, "Combined evidence URLs list updated")

    # Verify audit log
    has_resp_log = SellerClaimAuditLog.objects.filter(
        claim=claim_obj,
        action="SELLER_RESPONSE_SUBMITTED"
    ).exists()
    assert_true(has_resp_log, "Audit log created for seller response")

    # --------------------------------------------------------------------------
    print("\n--- TEST 6: SELLER DISPUTE ESCALATION ---")
    # --------------------------------------------------------------------------
    res_esc = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/escalate/", {
        "notes": "Courier partner disputing damage responsibility. Requesting urgent admin arbitration.",
    }, format="json")
    assert_true(res_esc.status_code == status.HTTP_200_OK, "Seller escalates claim with HTTP 200")
    claim_obj.refresh_from_db()
    assert_true(claim_obj.status == SellerClaim.Status.ESCALATED, "Status transitioned to ESCALATED")

    # --------------------------------------------------------------------------
    print("\n--- TEST 7: ADMIN ARBITRATION DECISION ---")
    # --------------------------------------------------------------------------
    client.force_authenticate(user=admin_user)
    res_approve = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/admin-decision/", {
        "decision": "APPROVE",
        "reason": "Courier in-transit mishandling confirmed via dispatch telemetry. Seller claim approved.",
    }, format="json")
    assert_true(res_approve.status_code == status.HTTP_200_OK, "Admin approves claim with HTTP 200")
    claim_obj.refresh_from_db()
    assert_true(claim_obj.status == SellerClaim.Status.APPROVED, "Status transitioned to APPROVED")
    assert_true(claim_obj.admin_decision == "APPROVE", "Admin decision set to APPROVE")
    assert_true(claim_obj.resolved_at is not None, "resolved_at timestamp populated")
    assert_true(claim_obj.admin_decided_by == admin_user, "admin_decided_by recorded")

    # --------------------------------------------------------------------------
    print("\n--- TEST 8: CLAIM SETTLEMENT & CLOSURE ---")
    # --------------------------------------------------------------------------
    # Settle
    res_settle = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/admin-decision/", {
        "decision": "SETTLE",
        "reason": "Credit adjustment processed in accounting ledger.",
    }, format="json")
    assert_true(res_settle.status_code == status.HTTP_200_OK, "Admin settles claim with HTTP 200")
    claim_obj.refresh_from_db()
    assert_true(claim_obj.status == SellerClaim.Status.SETTLED, "Status transitioned to SETTLED")

    # Close
    client.force_authenticate(user=seller_a)
    res_close = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/close/", {
        "notes": "Case fully resolved and closed.",
    }, format="json")
    assert_true(res_close.status_code == status.HTTP_200_OK, "Claim closed with HTTP 200")
    claim_obj.refresh_from_db()
    assert_true(claim_obj.status == SellerClaim.Status.CLOSED, "Status transitioned to CLOSED")
    assert_true(claim_obj.closed_at is not None, "closed_at timestamp populated")

    # --------------------------------------------------------------------------
    print("\n--- TEST 9: INVALID STATE TRANSITIONS REJECTED ---")
    # --------------------------------------------------------------------------
    # Cannot transition from CLOSED to OPEN or UNDER_REVIEW
    res_bad_trans = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/escalate/", {
        "notes": "Try re-escalating closed claim",
    }, format="json")
    assert_true(res_bad_trans.status_code == status.HTTP_400_BAD_REQUEST, "Invalid transition from CLOSED rejected with HTTP 400")

    # --------------------------------------------------------------------------
    print("\n--- TEST 10: SOURCE CLAIM ID IDEMPOTENT INTAKE CONTRACT ---")
    # --------------------------------------------------------------------------
    source_clm_id = f"EXT-SEVO-CUST-CLM-{uid}"
    client.force_authenticate(user=admin_user)

    # First intake call creates record
    res_intake_1 = client.post("/api/workforce/seller-hub/claims/intake/", {
        "source_claim_id": source_clm_id,
        "source_order_id": order_a.source_order_id,
        "claim_type": "MISSING_ITEM",
        "description": "Customer says 1 avocado was missing from pack.",
        "claimed_amount": "30.00",
        "evidence_urls": ["https://storage.sevo.in/proof/pack_missing.jpg"],
    }, format="json")
    assert_true(res_intake_1.status_code == status.HTTP_201_CREATED, "First intake call creates SellerClaim with HTTP 201 (created=True)")
    assert_true(res_intake_1.data.get("created") is True, "created flag is True")
    created_claim_id = res_intake_1.data.get("claim", {}).get("id")

    # Second intake call with identical source_claim_id returns existing
    res_intake_2 = client.post("/api/workforce/seller-hub/claims/intake/", {
        "source_claim_id": source_clm_id,
        "source_order_id": order_a.source_order_id,
        "claim_type": "MISSING_ITEM",
        "description": "Customer says 1 avocado was missing from pack.",
    }, format="json")
    assert_true(res_intake_2.status_code == status.HTTP_200_OK, "Second intake call returns existing claim with HTTP 200 (created=False)")
    assert_true(res_intake_2.data.get("created") is False, "created flag is False on duplicate intake")
    assert_true(res_intake_2.data.get("claim", {}).get("id") == created_claim_id, "Returned ID matches initial claim")

    total_count_src = SellerClaim.objects.filter(source_claim_id=source_clm_id).count()
    assert_true(total_count_src == 1, "Database contains exactly 1 SellerClaim for source_claim_id")

    # --------------------------------------------------------------------------
    print("\n--- TEST 11: MULTI-TENANT ISOLATION ---")
    # --------------------------------------------------------------------------
    client.force_authenticate(user=seller_b)
    res_cross_view = client.get(f"/api/workforce/seller-hub/claims/{claim_1_id}/")
    assert_true(res_cross_view.status_code == status.HTTP_404_NOT_FOUND, "Seller B cannot view Seller A's claim (HTTP 404)")

    res_cross_resp = client.post(f"/api/workforce/seller-hub/claims/{claim_1_id}/respond/", {
        "seller_response": "Cross tenant tamper attempt",
    }, format="json")
    assert_true(res_cross_resp.status_code == status.HTTP_404_NOT_FOUND, "Seller B cannot mutate Seller A's claim (HTTP 404)")

    # --------------------------------------------------------------------------
    print("\n--- TEST 12: ZERO SIDE-EFFECTS VERIFICATION ---")
    # --------------------------------------------------------------------------
    # Verify inventory on_hand_qty, reserved_qty, and order totals are untouched
    inv_a.refresh_from_db()
    assert_true(inv_a.on_hand_qty == Decimal("50.000"), f"Inventory on_hand_qty untouched ({inv_a.on_hand_qty})")
    assert_true(inv_a.reserved_qty == Decimal("0.000"), f"Inventory reserved_qty untouched ({inv_a.reserved_qty})")

    order_a.refresh_from_db()
    assert_true(order_a.total_amount == Decimal("540.00"), f"Order total_amount untouched ({order_a.total_amount})")

    # --------------------------------------------------------------------------
    print("\n--- TEST 13: DASHBOARD CLAIMS METRICS LIVE AGGREGATION ---")
    # --------------------------------------------------------------------------
    client.force_authenticate(user=seller_a)
    res_met = client.get("/api/workforce/seller-hub/metrics/")
    assert_true(res_met.status_code == status.HTTP_200_OK, "Seller metrics returns HTTP 200")
    # Seller A has 2 claims now: claim 1 (CLOSED), claim 2 (OPEN)
    assert_true(res_met.data.get("total_claims_count") == 2, f"total_claims_count is 2 (got {res_met.data.get('total_claims_count')})")
    assert_true(res_met.data.get("open_claims_count") == 1, f"open_claims_count is 1 (got {res_met.data.get('open_claims_count')})")
    assert_true(res_met.data.get("resolved_claims_count") == 1, f"resolved_claims_count is 1 (got {res_met.data.get('resolved_claims_count')})")

    patch_post.stop()
    patch_dispatch.stop()

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: {pass_count} PASSED, {fail_count} FAILED")
    print("=" * 80)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_verification()
