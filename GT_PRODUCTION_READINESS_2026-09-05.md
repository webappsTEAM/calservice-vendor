# Goods & Transport — Production Readiness Report
**2026-09-05 · branch `stage0-platform-hardening` · nothing pushed**

This closes out the Porter-style Goods & Transport work. The previous two
reports covered backend parity; this one covers the driver app, the
end-to-end flow, and what still stands between here and production.

Two repositories are involved. `Calservices` (parent) holds `vendor/` and
`mobile/`; `Customer/` is a **git submodule** with its own history. Commits
below are labelled accordingly.

---

## 1. Flutter Driver app — the gap that made everything else inert

The vendor backend has had leg, stop and rich-proof endpoints since
`3a00715`. **Nothing on the driver's phone called them.** A Goods &
Transport job looked exactly like a repair job: pickup address only, no
drop point, no legs, no stops, and a proof sheet asking for an "appliance
photo". Every column the customer's tracking map reads was written by
nobody.

**Parent commit `731abc5`** — 1,340 lines across 8 files.

| Layer | File | What it does |
|---|---|---|
| Domain | `mobile/lib/features/jobs/domain/trip_stop.dart` *(new)* | `kLogisticsLegSequence` mirroring the backend's `LEG_SEQUENCE`, forward-only `canAdvanceLeg`, `TripStop`, `TripStopsSnapshot`, `LogisticsLegResult`, `TripStopProgressResult` |
| Domain | `.../domain/job.dart` | `isLogistics`, drop address + coordinates + contact, `logisticsLeg`, `logisticsLegUpdatedAt`, `tripStopCount`, `hasDropCoordinates` |
| Data | `.../data/job_actions_api.dart` | `setLogisticsLeg`, `fetchTripStops`, `updateTripStop`; `uploadProof` extended with recipient, stop, lat/lng |
| Data | `.../data/job_actions_repository.dart` | Typed layer, refuses a backwards leg locally before spending a request |
| State | `.../presentation/providers/trip_stops_provider.dart` *(new)* | `FutureProvider.autoDispose.family` — same shape as `preServiceStatusProvider` |
| UI | `.../widgets/logistics_trip_section.dart` *(new)* | Trip progress, pickup/drop cards with navigation, stop list, explicit leg buttons |
| UI | `.../widgets/proof_submission_sheet.dart` | Recipient name/phone, stop picker, best-effort GPS — the **same** sheet, not a second one |
| UI | `.../presentation/job_detail_screen.dart` | Section wired above ACTION STEPS for accepted logistics jobs |

### The three rules that shaped it

**Every leg is an explicit tap.** `LOADING`, `EN_ROUTE_DROP` and
`UNLOADING` are never inferred from arrival, GPS proximity or elapsed time.
Only the driver knows when loading actually began, and both the customer's
tracking view and fare reconciliation depend on those timestamps being
real. The app offers exactly **one** button — the immediate next leg — so a
driver is never invited to skip over steps that did not happen.

**`DELIVERED` is not a button.** `WorkforceJobProofView` sets it when proof
of delivery is accepted. There is no path in the app to claim a delivery
without the evidence for it.

**The server owns the state.** Leg and stop timestamps are re-read from
`GET /workforce/jobs/<pk>/stops/` on open and after every action. Nothing
about trip progress is cached locally, so an app killed mid-trip reopens
exactly where it was and never disagrees with what the customer is shown.

Retry safety is inherited from the backend rather than reimplemented: a
repeated leg returns `changed: false` with no duplicate history entry and
no duplicate customer event; a repeated stop update never rewrites a
recorded timestamp; the proof endpoint upserts one row per job. A request
lost on a patchy connection is simply offered again — including when it
actually succeeded and only the response went missing. The UI reports those
as "already recorded", not as failures.

### Backend prerequisites (both additive)

- `WorkforceJobSerializer` now exposes `is_logistics`, drop address and
  coordinates, drop contact, leg + timestamp, and `trip_stop_count`.
- The unmanaged `ServiceRequest` mirror gained `drop_latitude` /
  `drop_longitude`, which it was missing.

> ### ⚠️ DEPLOY ORDER — hard requirement
> Customer migration **`0065_servicerequest_drop_latitude_and_more`** must be
> applied to the shared database **before** the vendor app ships with these
> mirror fields. Django selects every concrete field on a model, so
> deploying the vendor app first breaks *every* `ServiceRequest` query in it,
> not only logistics ones. `0065` is two nullable `DecimalField`s and is safe
> to apply on its own, ahead of everything else.

### Verification honesty

**This Flutter code is not compile-verified.** Neither the Dart SDK nor
pub.dev is reachable from this environment (`storage.googleapis.com` and
`pub.dev` both refused at the egress proxy), so `flutter analyze` could not
run. What *was* checked mechanically: delimiters balance in all 8 files,
every relative import resolves to a tracked file, and all 66 cross-file
symbols referenced are declared where they are imported from. On the backend
the serializer was **bound** (`.fields`) — the check `manage.py check` does
not perform, and precisely the one that would have caught the missing mirror
columns. **Run `flutter analyze` before shipping.**

> `mobile/` is deleted in the working tree (413 files, a pre-existing
> uncommitted deletion). All work was done against `HEAD` blobs and staged
> without touching the working tree, so that deletion was neither committed
> nor reverted.

---

## 2. End-to-end flow — what was actually broken

Testing the full Customer → Vendor → Driver → Customer loop surfaced five
real defects. All are fixed.

### Stale GPS overwrote fresher positions *(Customer `e6b0390e`)*

The webhook receiver wrote lat/lng straight onto the booking **with no
ordering check at all** — the `updated_at` the vendor sends was read by
nothing. Mobile networks retry and reorder constantly: a fix captured at
17:15 routinely lands after one captured at 17:20 (a retry after a dead
spot, a queued burst leaving a tunnel), and the older packet won. The
customer's map pin moved backwards, and because the stale value was
persisted it stayed wrong after a reload — the frontend's own out-of-order
guard only protects one live socket session.

There *was* a test for this. It compared against
`technician_location_updated_at`; when that column was dropped, the
protection went with it and the test errored instead of failing loudly.

Two more defects fell out of the same refactor: the webhook **discarded
heading, speed and accuracy** entirely and wrote no `TechnicianLocation`
row, and `_build_tracking_payload` initialised `db_heading`/`db_speed`/
`db_accuracy` and then **never assigned them** — so every tracking payload
reported heading 0, speed 0, accuracy null regardless of what the device
sent.

Fixed with one shared service, `services/technician_tracking.py`, used by
both ingestion paths. It compares **capture** time (arrival order being
exactly what cannot be trusted), rejects anything older than the newest
stored fix, writes the telemetry row, and updates the snapshot. A rejected
fix is not broadcast either — pushing it would have undone the guard
client-side. Migration `0069` adds `TechnicianLocation.captured_at`
(nullable, indexed, purely additive).

### WebSocket broadcasts were switched off by testing *(same commit)*

`broadcast_tracking_event` began with `if "test" in sys.argv: return`. Every
broadcast was a no-op under `manage.py test`, so the two tests covering the
live-tracking bridge were disabled by the fact that they were running. It
is also a production branch keyed on a command line: any process launched
with "test" in its arguments would lose live tracking silently. Replaced
with `TRACKING_BROADCAST_ENABLED`, defaulting to current behaviour.

### A retried proof duplicated the evidence *(Customer `5ffd5457`)*

The event-id replay guard does not cover this. A driver who loses the
network mid-upload retries; the vendor's proof endpoint accepts the
re-submission and emits a **fresh** event with a new id. Same delivery,
same photo, different event — and `_record_delivery_proof` called
`create()` unconditionally, so the customer saw the same signature,
recipient and OTP listed twice.

Now idempotent per `(booking, stop, kind, value)`. The subtle part was the
bare-note fallback: it fired when nothing had been created, which after the
change would be true on every retry — inventing a NOTE proof the original
delivery never had. It is now keyed on what the payload *supplied*, so a
retry writes nothing while genuinely new evidence still lands.

### Coverage now in place

| Concern | Where |
|---|---|
| Duplicate webhook delivery | `test_duplicate_leg_event_does_not_duplicate_history`, `test_replayed_event_id_is_ignored`, `test_duplicate_stop_event_does_not_move_the_timestamp` |
| Out-of-order delivery | `test_stale_earlier_leg_arriving_late_is_ignored`, `test_06_stale_location_protection` |
| Network retry / duplicate proof | `test_retried_proof_with_a_new_event_id_does_not_duplicate_evidence`, `test_a_retry_does_not_invent_a_note_proof`, `test_genuinely_new_evidence_after_a_retry_is_still_recorded` |
| Driver app restart | Trip state is read from the server on every open; no local cache exists to go stale |
| Invalid transitions | `test_invalid_leg_value_is_ignored_without_a_500`, `test_backwards_moves_are_rejected`, `test_skipping_a_leg_forward_is_allowed` |
| Unauthorized requests | `test_missing_secret_...`, `test_wrong_secret_...`, `test_unauthorized_stop_event_...`, `test_unauthorized_proof_event_...`, cross-tenant job guards |
| Expired tracking tokens | `test_invalid_tracking_token_returns_403`, `test_cross_booking_token_access_is_denied`, **new** `test_19_expired_tracking_token_cannot_start_a_payment` |

---

## 3. Database — nothing has been applied

**The production database is unreachable from this environment.** Both the
cloud container and the local VM fail to connect (`Network is unreachable`
to the configured host on 5432). No migration in this series has been
applied anywhere, and none should be applied without reading this section.

### Safe additive — apply freely, in order

| Migration | Operations |
|---|---|
| `logistics/0005_servicetier_additional_stop_charge_and_more` | AddField ×6 (pricing columns) |
| `service_requests/0063_merge_20260904_1457` | merge node, no operations |
| **`service_requests/0065_servicerequest_drop_latitude_and_more`** | AddField ×2 — **apply this before deploying the vendor app** (see §1) |
| `service_requests/0066_servicerequest_fare_breakdown` | AddField ×1 (JSON) |
| `service_requests/0067_tripstop_arrived_at_..._and_more` | AddField ×2 + CreateModel `DeliveryProof` |
| `service_requests/0068_farereconciliation` | CreateModel |
| `service_requests/0069_technicianlocation_captured_at` | AddField ×1 (nullable, indexed) |

Verified by reading the operations, not the filenames: no `RemoveField`,
`DeleteModel`, `RunSQL`, `RunPython` or `AlterField` in any of them.

### Destructive — requires your approval

**`service_requests/0064_gt_x04_drop_legacy_addon_and_technician_snapshot_fields`**
— `DeleteModel` ×2 (`BookingAddOn`, `ServiceAddOn`) and `RemoveField` ×27.

I re-verified its central claim across **both** backends, both frontends and
the mobile app in one pass, because that claim was wrong once before (it
asserted the `technician_*` fields were unreferenced while
`technician_views.py` was still selecting them — every
`/api/technician/bookings/*` endpoint was returning 500). Result: **every
field and model it drops is already absent from the current models**, so it
is genuinely catching the migration graph up to `models.py`, not causing a
loss. Before applying, confirm `BookingAddOn` / `ServiceAddOn` hold no rows
you still need.

**`vendor/workforce_api/0022_gt_x04_drop_legacy_quote_models_and_cleanup`** —
same category, same requirement.

### Requires real-data verification — BLOCKED ON YOU

`Addon.package` is the one remaining schema blocker. The model declares
`ForeignKey(Package, on_delete=CASCADE)` — implicitly `null=False`. Migration
`0058` recorded `null=True, on_delete=SET_NULL`. `makemigrations` wants to
write `0070_alter_addon_package` closing that gap, which would do two things:

1. add `NOT NULL` to `package_id` — **fails outright** if any row is null;
2. change `ON DELETE` from `SET_NULL` to `CASCADE` — deleting a Package would
   then delete its Addons instead of orphaning them. **Silent data loss.**

Run this against production and send me the number:

```bash
# from Customer/backend, using the existing .env — no credentials typed anywhere
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','quicktims.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute('SELECT count(*) FROM service_requests_addon WHERE package_id IS NULL')
    print('addons with NULL package_id:', c.fetchone()[0])
"
```

- **Result `0`** → the `NOT NULL` half is safe. I still need your answer on
  whether `SET_NULL → CASCADE` is intended, because that is a product
  decision about what deleting a Package should do to its addons.
- **Result `> 0`** → do not apply. Those rows need assigning or deleting
  first, and that is a data decision only you can make.

### Also found

`workforce_api` migration `0020` creates a `WorkforceSystemSetting` model
that `models.py` no longer declares — migration/model drift in the opposite
direction. Not blocking; worth a look.

---

## 4. Google Maps — configured, chain verified, key rotation required

`maps.googleapis.com` is **blocked by the egress allowlist** in both
environments, so I could not confirm which APIs are enabled on the key. Run
this from a machine with network access to check:

```bash
curl -s "https://maps.googleapis.com/maps/api/distancematrix/json?origins=12.7409,77.8253&destinations=12.9716,77.5946&key=$GOOGLE_MAPS_API_KEY" | head -c 300
curl -s "https://maps.googleapis.com/maps/api/geocode/json?address=SIPCOT+Phase+1,+Hosur&key=$GOOGLE_MAPS_API_KEY" | head -c 300
```

`status: "OK"` means enabled; `REQUEST_DENIED` with an `error_message` names
what is missing. **Distance Matrix** and **Geocoding** are both required.

### The chain is server-authoritative — proven, not asserted

A booking was submitted with `total_amount: 1`. The server stored **908.94**
with a full itemised breakdown:

```
base_fare 250.00 · distance 35.83 km · chargeable 33.83 km
distance_charge 608.94 · loading_unloading 50.00 · stops 0
subtotal 908.94 · surge ×1.00 · minimum_fare_applied false
distance_source "straight_line_estimate"
```

`POST /api/logistics/quote/` returned **the same 908.94** for the same
coordinates, also ignoring the client's number. `distance_source` is the
honest part: with Google Maps unreachable the haversine fallback engaged
and **says so**, rather than presenting a straight-line guess as a road
route.

### 🔴 Key rotation required *(Customer `bce413f4`)*

A **live Google Maps API key was hardcoded as a fallback** in three
committed frontend files — `hosurLocations.js`, `locationService.js`,
`useReverseGeocode.js`. It is in git history and in every bundle ever built.
Being a *fallback* made it worse: it kept working when
`VITE_GOOGLE_MAPS_KEY` was unset, so a misconfigured deployment silently
billed whichever project owns that key.

Removed — the key now comes only from the environment, and with none set,
place search degrades to the existing keyless Photon and Nominatim tiers.
**This does not un-leak it.** The value is still in git history and in
shipped bundles. It must be **rotated in the Google Cloud console**, and the
replacement restricted by HTTP referrer and by API. The key was never
printed during this work and appears in no commit message.

The server-side key (`settings.GOOGLE_MAPS_API_KEY`, used by
`services/routing.py`) is a separate value, not exposed to browsers. It
should be a *different* key from the browser one, restricted by IP.

> Also on disk: `vendor/backend/scratch/deploy_full_phase4.py` contains live
> keys in a heredoc. That path is gitignored so nothing leaked to the repo,
> but the file is worth cleaning up locally.

---

## 5. Tests — 13 failures → 7, none of them regressions

**Customer `service_requests`: 238 tests, 6 failures + 1 error, 5 skipped.**
**Vendor Goods & Transport: 52 tests, all passing.**

### Fixed by fixing the code, not the assertion

| Was failing | Root cause |
|---|---|
| `test_04_full_lifecycle_and_gps_telemetry_persistence` | Webhook discarded telemetry — fixed |
| `test_05_websocket_realtime_bridge_and_fallback` | Broadcasts disabled under test — fixed |
| `test_06_stale_location_protection` | No out-of-order guard existed — fixed |
| `test_complete_bridge_chain` | Same broadcast bug |
| `test_waterproofing_advance_payment_split` | Payment endpoint charged the full quote, not the advance — fixed |
| `test_payment_replay_protection_and_status_update` | Stale contract: an order_id can no longer be invented client-side |

Three assertions referencing dropped columns were **re-pointed** at
`TechnicianLocation` rather than deleted — the behaviour they check is still
the behaviour that matters.

### A real payment defect found this way *(Customer `5e6c5e6a`)*

`PaymentInitiateView` asked for `sr.total_amount` unconditionally. Every
other part of the system disagrees for quoted painting/masonry work: the
accepted quote names an advance, `state_machine.py` refuses to let work
start until that advance is recorded, and the booking page shows the advance
as what is due. A customer who accepted a ₹20,000 quote with a ₹10,000
advance was presented with an order for **₹20,000**.

The frontend was covering for it by computing `grandTotal * 0.5` itself —
meaning the amount actually charged was decided **client-side**. Same class
of problem as trusting a client-supplied total, fixed the same way.

### The remaining 7 are missing features, not regressions

All in `test_painting_module`, all verified by grepping for each expected
behaviour and finding **nothing that implements it**:

| Tests | Missing feature | Product decision needed |
|---|---|---|
| 4 | Inspection-fee geofencing (free ≤15 km, ₹300 beyond) | Fee amount, radius, origin point |
| 1 | Consultation fee excluded from advance | Depends on the above |
| 1 | Minor-masonry 500 sq.ft minimum | Threshold, per service |
| 1 | Bathroom size-choice requirement | Size tiers and pricing |

The last two assert validation messages that appear nowhere but in the tests
themselves. None are Goods & Transport, and none were invented.

> Related: `validate_total_amount` rejects `amount <= 0`, which will block a
> free inspection booking the moment that feature is built. Worth handling
> together.

### Outside Goods & Transport, pre-existing

`customer_care` (4) and `accounts.test_customer_address_isolation` (1) fail
on `create_refund_request()` signature drift and a missing
`is_booking_reschedule_eligible` import. Confirmed pre-existing — this
session's commits touched none of those files.

### Vendor tests were homeless *(parent `2f04c89`)*

52 vendor tests had been living outside the repository, protecting nothing.
Now committed at `vendor/backend/workforce_api/tests_gt/`, including a new
`test_driver_job_contract` that pins the fields the Flutter app depends on
by **binding** the serializer — the check that would have caught the missing
mirror columns.

They are in `tests_gt/` rather than `tests/` deliberately: that directory has
no `__init__.py`, so unittest cannot load it by label, and its one module has
been silently unrunnable for some time (it imports `WorkforceSystemSetting`,
which migration 0020 creates but `models.py` no longer declares). Adding an
`__init__.py` would surface that breakage in someone else's module, so these
got their own package instead.

---

## 6. Location data — resolved without inventing anything

70 of the 79 `HOSUR_LOCATIONS_DATABASE` entries carry no baked coordinates,
**by design**. They resolve at selection time through the app's own
three-tier geocoder — Google → Photon → Nominatim — all of which return real
coordinates, with a per-session cache.

When nothing resolves, `resolveLocationCoords` returns `null` and the
booking is **refused** with *"We couldn't pin your pickup location. Please
pick it from the suggestions so we can find a driver near you."* No default
coordinate exists anywhere in the path; the old hardcoded `12.7409/77.8253`
fallbacks are gone. The only remaining occurrence of those numbers is
Photon's search-bias parameter, which is not a returned coordinate.

---

## 7. Production-readiness audit

Every line below is a grep or a settings read, with file:line evidence.

| Area | Finding |
|---|---|
| **Authentication** | 159 `IsAuthenticated` guards (Customer), 40 `IsApprovedTechnician` (vendor). The 16 vendor `AllowAny` endpoints are deliberate and documented: signup (throttled), the RazorpayX payout webhook (HMAC-verified against the raw body), public catalog |
| **Authorization** | Job actions check `job.assigned_employee == emp` before any leg/stop/proof write |
| **Tenant isolation** | 14 per-job `is_employee_authorized_for_job` checks, 69 `resolve_actor_company` resolutions, explicit `CROSS_TENANT_FORBIDDEN` refusals |
| **Rate limiting** | 9 throttled Customer scopes (payment, OTP, quote), 6 vendor. The logistics quote endpoint is `AllowAny` + throttled |
| **Webhook auth** | Constant-time comparison of a shared-secret header **or** HMAC-SHA256 over the raw body; fails closed when neither is present. The `wf_webhook_secret_default` skeleton key is gone, and production **refuses to boot** without `WORKFORCE_WEBHOOK_SECRET` |
| **Idempotency** | Event-id replay guard; forward-only leg ordering; stop timestamps never rewritten; proof now idempotent per artefact |
| **Payment integrity** | Ownership verified before an order is issued; `order_id` must match one this app issued; Razorpay signature verified server-side; a Payment row is consumed once; no-gateway refuses (503) rather than defaulting to success |
| **Fare integrity** | Client `total_amount` never trusted for logistics; unresolvable fare **raises** rather than falling back to the client's number; advance/balance now server-computed |
| **Driver eligibility** | 10-gate engine: account active, registration approved, documents approved **and unexpired**, vehicle insurance/permit/PUC unexpired, no unapproved dossier documents |
| **Document expiry** | Enforced at dispatch (Gate 3) for both technician documents and vehicle papers |
| **Cash ceiling** | `CASH_FLOAT_CEILING` (Gate 10) stops offering further cash-collecting work past the limit; fails **open** so a lookup failure cannot halt dispatch |
| **Tracking authorization** | Token + 180-day expiry, enforced on REST **and** WebSocket — and now on payment too (`6706b01d`) |
| **PII protection** | `recipient_phone` deliberately omitted from the tracking payload, with a test pinning it |
| **Proof-of-delivery security** | Photo required; recipient name required for a delivery; server sets `DELIVERED`, the app cannot |
| **Error handling** | Webhook side effects are fire-and-forget: a broadcast or notification failure never rolls back a persisted state change, and never returns non-2xx to a sender that will not retry |
| **Logging / secrets** | Routing logs `type(exc).__name__` only — a `requests` exception string embeds the URL including `key=`. A regression test asserts the key never appears in emitted records. Zero hardcoded keys remain in tracked source |

### Fixed during the audit *(Customer `6706b01d`)*

`_verify_booking_ownership` accepted a tracking token **without the expiry
check** the tracking endpoints enforce. The weaker rule was guarding the more
sensitive action: an expired link could no longer show you where the
technician was, but could still start and confirm an order on that booking.

### Worth your attention

- The production database host is a **public IP** on 5432. Confirm it is
  firewalled to your application servers only.
- `create_admin.py` / `reset_admin.py` print passwords to stdout.
- `vendor/backend/service_requests/vendor_views.py` (lines 116, 650) reads and
  writes `sr.technician_arrived_at`, which **does not exist** on the vendor
  mirror model — a live `AttributeError` in the AC-estimation endpoints. This
  is in the pre-existing uncommitted work, so it was left untouched and is
  reported rather than fixed.

---

## 8. Git

Both repositories are on `stage0-platform-hardening`. **Nothing was pushed**
— neither branch has an upstream configured.

**Parent (`Calservices`)** — 2 commits: `731abc5` (Flutter integration),
`2f04c89` (vendor tests). 1,135 pre-existing dirty entries, unchanged.

**Customer submodule** — 5 commits: `e6b0390e` (tracking), `5e6c5e6a`
(payment advance), `bce413f4` (key removal), `5ffd5457` (proof idempotency),
`6706b01d` (token expiry). 1,082 pre-existing dirty entries, unchanged.

Every change to a file carrying pre-existing uncommitted work was staged via
blob isolation from `HEAD` and applied separately to the working tree, so the
AC-estimation/quotation work and the repo-wide line-ending conversion are
byte-for-byte as they were.

> **One consequence to know about:** because that pre-existing work sits
> unstaged in the same files, a future `git add -A` will stage it. Review
> before committing.

---

## Remaining blockers

| # | Blocker | Who |
|---|---|---|
| 1 | **`Addon.package`** — run the count query in §3; then decide whether `SET_NULL → CASCADE` is intended | You |
| 2 | **Rotate the leaked Google Maps key** and restrict the replacement by referrer + API | You |
| 3 | **Apply migration 0065 before deploying the vendor app** — otherwise every vendor `ServiceRequest` query breaks | Deploy order |
| 4 | **Run `flutter analyze`** — no Dart SDK was reachable here | Anyone with the SDK |
| 5 | **Confirm Distance Matrix + Geocoding are enabled** on the server key (§4) | You |
| 6 | **Seed `ServiceTier.base_fare` / `per_km_rate`** — migration 0005 adds the columns but seeds no values; without them distance pricing falls back to flat `Lane.fare` / `starting_price` | You |
| 7 | **7 painting/masonry features** never implemented (§5) — each needs a product decision | You |
| 8 | **Approve the two destructive migrations** (0064, vendor 0022) | You |

Items 1, 2, 3 and 6 block a Goods & Transport production launch. Items 4 and
5 are verification you can do in minutes. Items 7 and 8 are outside Goods &
Transport and can follow.
