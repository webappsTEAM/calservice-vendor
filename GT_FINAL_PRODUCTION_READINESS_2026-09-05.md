# Goods & Transport — Final Production Readiness

**2026-09-05 · branch `stage0-platform-hardening` · nothing pushed**
Supersedes `GT_PRODUCTION_READINESS_2026-09-05.md`. Flutter/mobile and
painting/masonry were out of scope for this pass.

---

## A. Completion

**Code: ~95%. Deployable today: no.**

The gap is not code. Every remaining blocker is a value only you can supply
(pricing rates, environment variables, a key rotation, one data decision) or
a migration only you can apply. Nothing below is waiting on more engineering.

| Area | State |
|---|---|
| Fare engine, quote, booking | Complete and proven server-authoritative |
| Final fare reconciliation | Now actually runs — it never did before |
| Dispatch, eligibility, cash ceiling | Complete |
| Live tracking / GPS | Complete, with ordering guarantees proven |
| Proof of delivery | Complete and idempotent |
| Authorization / tenant isolation | Complete after this pass |
| Webhook transport | Complete after this pass |
| **Pricing catalogue data** | **Empty of rates — distance pricing is inert** |
| **Environment configuration** | **Missing values that stop both apps booting** |
| **Database** | **Nothing applied; the apps cannot run against it as-is** |

---

## B. Finished

**Fare chain, end to end.** `ServiceTier.base_fare` / `per_km_rate` are read
in exactly one place — `quote_logistics_fare()` in
`services/logistics_pricing.py` — which both the quote endpoint and the
booking path call through `resolve_logistics_fare_v2()`. Proven with a real
request: a booking submitted with `total_amount: 1` stored **908.94**, and
the quote endpoint returned the identical 908.94 for the same coordinates.
Minimum fare, free km, distance charge, loading/unloading, additional stops
and surge are all applied in that one function; a zero or negative surge is
treated as no surge rather than zeroing the fare. `distance_source` records
whether the distance was a real road route or a straight-line estimate, so
an estimate can never be mistaken for a measurement.

**A client-supplied total can never win.** For logistics categories the
submitted amount is not consulted at all, and an unresolvable fare raises
rather than falling back to it. Pinned by
`test_gt_fare_integrity.BookingFareAuthorityTests`.

**Two fare holes closed this pass:**

*Tier substitution.* `ServiceTier.category` uses the catalogue vocabulary
(`truck`) while bookings use `service_category` (`goods_transport_truck`),
and nothing reconciled them. A caller could book a truck while naming a
two-wheeler tier and be charged the scooter fare — at both the quote and the
booking, which agreed with each other and were wrong together. Now gated in
the shared pricing service, for lanes as well as tiers, including inactive
records.

*The final fare never happened.* `reconcile_booking_fare()` was wired to the
`service_completed` event — which the vendor app **never emits**. Its
complete emission set is `technician.assigned`, `booking.dispatch_delayed`,
`technician.delayed`, `technician.location_updated`, `payment.collected`,
`logistics.leg_changed`, `trip.stop_arrived`/`trip.stop_completed`,
`job.completion_proof_submitted`. So a trip that ran 40 km on a 20 km quote
was charged the 20 km price, extra stops completed were charged for at all,
and approved extra work never reached the amount collected. Reconciliation
now also runs on `DELIVERED`, which the vendor does emit.

**Live tracking, proven rather than asserted** — 15 tests walking the path
from driver GPS to customer map: capture time preserved and distinguished
from receive time; heading, speed and accuracy surviving ingestion; an older
packet arriving late leaving both the snapshot and the telemetry log
untouched; a genuinely newer packet still accepted; equal timestamps not
dropped; a stale packet not broadcast; a malformed coordinate refused
without a 500; telemetry reaching the customer payload; the destination
switching to the drop on `EN_ROUTE_DROP`; expired and wrong tracking tokens
refused.

**Security fixed this pass:** the webhook rate limit (below), cross-tenant
checks on the leg and stop endpoints, and server-side geocoding no longer
preferring the browser key.

---

## C. Blocking production

### 1. The webhook receiver was rate-limited at 60/minute — FIXED, verify the new value

`AllowAny` meant it inherited the blanket **anonymous** rate. The vendor
POSTs one request per event, and GPS alone is ~6/minute **per active
driver** — ten drivers saturate it, twenty lose half their events. Delivery
is fire-and-forget with no retry, so a throttled event is gone: the map
freezes, proof never arrives, the fare is never reconciled, and nothing
errors anywhere. Now `1200/minute`, configurable. Confirm that suits your
expected fleet size.

### 2. Distance pricing is inert — NEEDS YOUR RATES

`seed_logistics_hosur` sets `starting_price` only. Every tier has
`per_km_rate = NULL`, so `quote_logistics_fare()` returns `None` and the
fare falls back to the flat starting price. **Porter-style distance pricing
is not live until you supply rates.** This is correct behaviour — nothing
was invented — but it is not what the product promises. See §G.

### 3. Environment values missing — BOTH APPS WILL NOT BOOT

`WORKFORCE_WEBHOOK_SECRET` is unset in both `.env` files, and both apps now
raise at import when `DEBUG=False`. `CUSTOMER_APP_BASE_URL` is unset in the
vendor `.env` and defaults to localhost — previously a **silent** failure
that would have delivered every customer event nowhere while the vendor
looked healthy. It now fails closed too.

### 4. Database not migrated — the apps cannot run against it

Seven pending migrations, **all** with live runtime references. See §F.

### 5. Leaked Google Maps key — NEEDS ROTATION

Removed from source, but still in git history and in shipped bundles.

### 6. `Addon.package` — NEEDS ONE COUNT AND ONE DECISION

See §E and §D.

---

## D. What you must do by hand

1. **Rotate the Google Maps browser key** in the Google Cloud console.
   Restrict the replacement by HTTP referrer and to Geocoding + Maps
   JavaScript. Set it as `VITE_GOOGLE_MAPS_KEY`.
2. **Use a separate server key** for `GOOGLE_MAPS_API_KEY`, restricted by
   **IP** (not referrer) and to Distance Matrix + Geocoding. The two must
   not be the same key: a referrer-restricted key rejects server calls, and
   a key loose enough for both is loose enough for anyone.
3. **Set `WORKFORCE_WEBHOOK_SECRET`** to the same strong random value in
   *both* apps' `.env`.
4. **Set `CUSTOMER_APP_BASE_URL`** in the vendor `.env` to the Customer
   app's real base URL, no trailing slash.
5. **Supply per-km pricing** (§G) — or accept flat pricing for launch.
6. **Run the `Addon.package` count** (§E) and decide on `SET_NULL → CASCADE`:
   today deleting a Package orphans its addons; the model wants it to delete
   them. That is a product decision about what deleting a Package means.
7. **Approve the two destructive migrations** (`0064`, vendor `0022`).
8. **Confirm the fare-reconciliation policy.** It now runs for the first
   time, and it can change what a customer is charged after they booked. The
   thresholds in `services/fare_reconciliation.py` are not new, but they have
   never actually executed — they deserve one review pass.

---

## E. Commands

```bash
# 1. The Addon.package blocker — from Customer/backend, uses the existing .env
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','quicktims.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute('SELECT count(*) FROM service_requests_addon WHERE package_id IS NULL')
    print('addons with NULL package_id:', c.fetchone()[0])
"
# 0  -> the NOT NULL half is safe; still decide SET_NULL -> CASCADE
# >0 -> do NOT apply; those rows need assigning or deleting first

# 2. Google Maps APIs (from a machine with network access)
curl -s "https://maps.googleapis.com/maps/api/distancematrix/json?origins=12.7409,77.8253&destinations=12.9716,77.5946&key=$GOOGLE_MAPS_API_KEY" | head -c 200
curl -s "https://maps.googleapis.com/maps/api/geocode/json?address=SIPCOT+Phase+1,+Hosur&key=$GOOGLE_MAPS_API_KEY" | head -c 200
# "OK" = enabled. REQUEST_DENIED names what is missing.

# 3. Confirm no drift remains before deploying
python manage.py makemigrations --check --dry-run     # expect only 0070_alter_addon_package

# 4. Seed the logistics catalogue (safe to re-run; will not wipe rates you entered)
python manage.py seed_logistics_hosur

# 5. Goods & Transport test suites
python manage.py test service_requests.tests.test_gt_fare_integrity \
  service_requests.tests.test_gt_end_to_end \
  service_requests.tests.test_gt_logistics_webhook_events \
  service_requests.tests.test_gt_live_tracking_path \
  service_requests.tests.test_gt_d01_proof_of_delivery \
  service_requests.tests.test_gt_d02_leg_aware_tracking \
  service_requests.tests.test_gt_b01_fare_engine \
  service_requests.tests.test_gt_c01_fare_reconciliation \
  service_requests.tests.test_logistics_pricing \
  service_requests.tests.test_x10_routing_eta \
  service_requests.tests.test_live_tracking_security
# vendor:
python manage.py test workforce_api.tests_gt
```

---

## F. Migration order

**Every one of these has live runtime references, and every added column
appears in a plain `SELECT` on its model — so a missing column is a total
outage of every query on that model, not a partial degradation.** Verified
by inspecting the generated SQL.

### Apply in this order — all safe additive

| # | Migration | Adds | If missing |
|---|---|---|---|
| 1 | `logistics/0005_servicetier_additional_stop_charge_and_more` | 7 pricing columns | Every tier/quote query fails |
| 2 | `service_requests/0063_merge_20260904_1457` | merge node, no operations | — |
| 3 | `service_requests/0065_servicerequest_drop_latitude_and_more` | `drop_latitude`, `drop_longitude` | **Every ServiceRequest query in BOTH apps fails** |
| 4 | `service_requests/0066_servicerequest_fare_breakdown` | `fare_breakdown` | Every ServiceRequest query fails |
| 5 | `service_requests/0067_tripstop_arrived_at_..._and_more` | `TripStop.arrived_at`/`completed_at`, `DeliveryProof` | Every TripStop query fails; no proof storage |
| 6 | `service_requests/0068_farereconciliation` | `FareReconciliation` | Reconciliation logs a warning and continues |
| 7 | `service_requests/0069_technicianlocation_captured_at` | `captured_at` | All live tracking fails |

> **`0065` is not merely "before the vendor deploys" — it is before
> *anything* deploys.** `drop_latitude`/`drop_longitude` are concrete fields
> on the Customer `ServiceRequest` model and on the vendor's mirror, so both
> apps select them on every query. The current code cannot run against a
> database without them.

### Destructive — your approval required

- `service_requests/0064_gt_x04_drop_legacy_addon_and_technician_snapshot_fields`
  — `DeleteModel` ×2 (`BookingAddOn`, `ServiceAddOn`), `RemoveField` ×27.
  Re-verified across both backends, both frontends and the mobile app: every
  field and model it drops is already absent from the current models, so it
  is catching the migration graph up to `models.py`, not causing a loss.
  Confirm those two tables hold no rows you need.
- `vendor/workforce_api/0022_gt_x04_drop_legacy_quote_models_and_cleanup`
  — same category.

### Data-dependent — blocked

- `service_requests/0070_alter_addon_package` — §E.

### Not required

The vendor's pending `service_requests/0002_deliveryproof_tripstop` is
state-only: those mirror models are `managed=False`, so it emits no DDL.
Table names match the Customer app's real tables exactly.

---

## G. Pricing seed data required

`seed_logistics_hosur` already creates 9 tiers, the lanes and 30 service
areas, and re-running it will **not** overwrite rates you enter (its
`update_or_create` defaults carry no pricing-formula keys — pinned by a
test). What it does not set is the distance formula. Fill in these five
columns per tier and distance pricing turns on for that tier alone:

```
fare = base_fare
     + (distance_km - free_km) x per_km_rate
     + loading_unloading_charge
     + additional_stop_charge x (stops - 2)
     , x surge_multiplier, floored at minimum_fare
```

| Tier (`slug`) | Category | `starting_price` today | Needs |
|---|---|---|---|
| `3-wheeler` | truck | 160.00 | base_fare, per_km_rate, free_km, minimum_fare, loading_unloading_charge, additional_stop_charge |
| `tata-ace` | truck | 205.00 | same |
| `pickup-8ft` | truck | 300.00 | same |
| `1-7-ton` | truck | 380.00 | same |
| `2-wheeler` | two_wheeler | 48.00 | same (description already says "inclusive of 1.0 km" → `free_km = 1.00`) |
| `2-wheeler-electric-express` | two_wheeler | 55.00 | same |
| `1rk-1bhk-shifting` | packers_movers | 1499.00 | **none** — survey-priced by design, excluded from distance pricing |
| `2bhk-3bhk-shifting` | packers_movers | 2999.00 | none |
| `villa-office-relocation` | packers_movers | 4499.00 | none |

Leaving `per_km_rate` NULL keeps a tier on flat `starting_price` — a safe,
supported state. `base_fare` falls back to `starting_price` when unset, so
the minimum to switch a tier on is **`per_km_rate`**.

**I did not invent any of these numbers.** Send me the rate card and I will
write the seed.

---

## H. Google Maps deployment checks

1. **Two keys, never one.** Browser key: referrer-restricted, Geocoding +
   Maps JavaScript. Server key: IP-restricted, Distance Matrix + Geocoding.
2. **Zero hardcoded keys remain in tracked source** — verified across 825
   tracked files in both repos. The only live keys on disk are in
   `vendor/backend/scratch/deploy_full_phase4.py`, which is gitignored;
   clean it up locally.
3. **Browser key comes only from the environment** — the fallback literal is
   gone; unset means place search degrades to Photon then Nominatim, both
   keyless.
4. **Server key is separate and never sent to the frontend** — and server
   paths now read it *first* (they previously preferred the browser key,
   which a referrer-restricted key would reject).
5. **Run the two curl checks in §E** to confirm both APIs are enabled.
6. **Verify the fallback** by temporarily unsetting the server key: quotes
   must still return, with `distance_source: "straight_line_estimate"`.
   Covered by `test_x10_routing_eta`.
7. **Confirm no key leaks into logs** — routing logs only the exception
   type, because a `requests` exception string embeds the URL including the
   key. There is a regression test for this.

---

## I. Recommended code fixes (not blocking)

1. **Have the vendor send `actual_distance_km` on `DELIVERED`.** Without it
   the reconciliation applies stops, approved extra work and the minimum
   fare — all exact recorded facts — but not distance variance, the largest
   term. Deriving it from the GPS trail was considered and rejected: a
   haversine sum over jittery fixes overstates distance and would quietly
   overcharge.
2. **Charge additional stops at booking time.** Stops are added after the
   booking via a separate endpoint, so the stored fare always says
   `additional_stops: 0` and the customer only learns the real price at
   reconciliation. Not a revenue loss — reconciliation catches it — but poor
   transparency.
3. **Emit `service_completed`**, or retire its handler. Five handlers in the
   Customer receiver (`employee_accepted`, `employee_on_the_way`,
   `employee_arrived`, `service_started`, `service_completed`) are wired to
   events nobody sends. Status still updates through the shared database
   row, but their side effects — notifications, reconciliation — never fire.
4. **`workforce_api/tests/` has no `__init__.py`**, so its one module has
   been silently unrunnable; it imports `WorkforceSystemSetting`, which
   migration 0020 creates but `models.py` no longer declares.
5. **Out of scope, but worth knowing:** the painting/masonry inspection fee
   (`distanceKm > 15 ? 300 : 0`) is computed **client-side** in
   `BookingPage.jsx` and sent as `total_amount`. The backend has no such
   rule, which is why those tests fail. It is client-authoritative pricing
   in the same family as the fare issues fixed here.

---

## J. Tests

| Suite | Result |
|---|---|
| Customer — Goods & Transport (11 modules) | **171 passed, 0 failed** |
| Customer — `service_requests` (all) | 278 run, 271 passed, 5 skipped |
| Vendor — `workforce_api.tests_gt` | **70 passed, 0 failed** |

**+61 tests this pass**, all passing: fare integrity and tier substitution
(19), the live-tracking GPS path (15), final-fare reconciliation (6),
webhook config guards (5), estimation/logistics separation (6), GT endpoint
authorization (8), plus the retried-proof cases.

The 7 remaining failures are all `test_painting_module` and all **missing
features**, verified by grepping for each expected behaviour and finding
nothing implementing it: inspection-fee geofencing (4), the consultation fee
that depends on it (1), the minor-masonry 500 sq.ft minimum (1), the
bathroom size-choice requirement (1). Explicitly out of scope; no assertion
was weakened or deleted.

> The rate-limit defect was found **by** the suite, not by reading code:
> adding 40 tests pushed the run past 60 webhook POSTs and 23 unrelated
> tests began failing with 429. That is the evidence the old limit sat below
> realistic event volume.

---

## K. Security

| Control | Status |
|---|---|
| Authentication | `IsApprovedTechnician` on every driver endpoint; 159 `IsAuthenticated` guards customer-side |
| Authorization | Assignment checked on all three trip endpoints |
| Tenant isolation | **Fixed** — leg and stop endpoints let assignment stand in for tenancy; both now verify `is_employee_authorized_for_job` |
| Payment ownership | Verified before an order is issued; `order_id` must match one this app issued; Razorpay signature verified server-side; a Payment row is consumed once |
| Tracking token expiry | 180 days, enforced on REST, WebSocket **and** payment |
| Webhook authentication | Constant-time shared secret **or** HMAC-SHA256 over the raw body; fails closed; skeleton-key default gone; **both apps refuse to boot without the secret** |
| Rate limits | **Fixed** — the webhook receiver was on the anonymous 60/minute rate |
| PII | `recipient_phone` deliberately absent from the tracking payload, with a test |
| Secret leakage | Zero hardcoded keys in tracked source; routing logs exception types only |
| Logging | Webhook side effects are fire-and-forget: a broadcast or notification failure never rolls back a persisted state change |
| Hardcoded credentials | None in tracked source |
| `AllowAny` endpoints | 16 vendor, all deliberate: signup (throttled), the RazorpayX webhook (HMAC-verified), public catalog |

**Still worth your attention:** the production database host is a public IP
on 5432 — confirm it is firewalled to your application servers only. And
`create_admin.py` / `reset_admin.py` print passwords to stdout.

---

## L. Recommendation

# NO-GO — but only on configuration and data

The Goods & Transport code is production-ready. Nothing on the list below is
waiting on engineering; every item is a value you supply or an action you
take, and each is short.

**Not ready because:**

1. The database is unmigrated, and the current code **cannot run against
   it** — this is an outage, not a degradation.
2. Both apps refuse to boot: two environment variables are unset.
3. Distance pricing has no rates. You would launch a Porter-style product
   charging flat fares.
4. A leaked API key is unrotated.
5. One schema decision (`Addon.package`) is unanswered.

**Becomes GO when:** migrations 1–7 are applied in order · the four
environment values are set · per-km rates are entered (or flat pricing is a
deliberate launch choice) · the Maps keys are rotated and split · the
`Addon.package` count comes back 0 and you have decided on CASCADE.

I would not launch on the strength of a green test suite. Three of the
defects fixed this pass — reconciliation never running, the webhook rate
limit, and every Packers & Movers booking 500ing the estimation dashboard —
were invisible to the suite before this pass, and two of them fail
**silently** in production. What makes me comfortable recommending GO once
the list above is done is that the paths that would fail silently now have
tests that fail loudly.


---

## Addendum — second verification pass (2026-09-05, later)

A second adversarial pass over the areas the first report covered most
thinly found two more Goods & Transport defects. Both are fixed; both were
invisible to the test suite beforehand.

### 1. A reconciled fare never reached the amount the driver collects

The first report traced the fare chain as far as `total_amount` and called
the chain complete. It was not. `JobPayment` rows are created with
`get_or_create`, whose `defaults` apply **only on creation**, and nothing
anywhere updates `amount_due` afterwards -- there is not one `amount_due =`
assignment outside those defaults.

The row is created the first time anyone looks at payment: the driver
opening the payment screen (the Flutter app calls it from the job detail
screen), the customer viewing payment, or cash collection. All of those
routinely happen mid-trip, before `DELIVERED`. So a trip that ran longer,
visited an extra stop or picked up approved extra work has its
`total_amount` raised by reconciliation -- and the collection screen still
shows the pre-trip number. The customer pays the old amount and the books
say the new one. A reconciliation that lowers the fare overcharges instead.

Fixed with `sync_payment_amount_due()` at all three creation sites. It
refreshes only a `PENDING` row: `PAID` is history, `CASH_PENDING` means the
driver has already taken the cash (an OTP is issued for the customer to
confirm it), and `AUTHORIZED` is held by the gateway for a specific amount.
A fare change after any of those is a refund or a follow-up charge, not an
edit. Nine tests, including one that counts creation sites against sync
calls so a fourth site cannot be added without the refresh.

### 2. The bare `goods_transport` slug bypassed server-side pricing

There are four logistics category sets across the two apps. Three contained
the bare `goods_transport` slug; `LOGISTICS_CATEGORIES` in
`logistics_pricing.py` did not -- and that is the set that decides whether a
client-supplied total is trusted. So the vendor treated those bookings as
logistics for dispatch, legs and stops, while the Customer app priced them
at **whatever the client sent**.

Not a legacy slug: it has its own `"GT"` request-id prefix and the generic
booking page emits it. It is now covered by the pricing gate, and
deliberately **not** distance-priced -- the bare slug does not say truck or
two-wheeler, so there is no tier category to validate a quote against. It
resolves through the flat lane/tier lookup or returns a clean 400.

A test now walks the request-id prefix map -- the closest thing this
codebase has to a registry of live category slugs -- and asserts every slug
labelled GT or PM is covered by the pricing gate.

### Also verified this pass

* **Category vocabularies** across both apps now agree (four sets compared
  programmatically). `truck` and `logistics` appear in the prefix map but in
  no category set and are emitted by nothing; reported, not changed.
* **Payment status semantics** checked against the real `PaymentStatus`
  choices rather than assumed.

### Revised test totals

| Suite | Result |
|---|---|
| Customer — Goods & Transport (13 modules) | **176 passed, 0 failed** |
| Customer — `service_requests` (all) | 283 run, 276 passed, 5 skipped |
| Vendor — `workforce_api.tests_gt` | **79 passed, 0 failed** |

The 7 remaining failures are unchanged and all out-of-scope painting/masonry.

### Effect on the recommendation

**Unchanged: NO-GO on configuration and data.** No new blocker was
introduced, and both defects above were code-level and are now fixed. But
they sharpen the reason for the recommendation: this is the second pass in a
row where the most damaging Goods & Transport defects were ones that fail
**silently** in production and were invisible to a green test suite. The
list in section D has not grown -- and it is still the only thing standing
between here and GO.
