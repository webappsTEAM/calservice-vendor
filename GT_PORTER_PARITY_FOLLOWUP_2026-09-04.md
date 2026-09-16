# Goods & Transport — Follow-up Implementation Report

**Date:** 2026-09-04 · **Branch:** `stage0-platform-hardening` (both repos)
**Nothing pushed. Nothing applied to any database.**

---

## What was implemented

**1. Driver → Customer logistics events.** The vendor side now emits the four
events the Customer app was already able to receive:
`logistics.leg_changed`, `trip.stop_arrived`, `trip.stop_completed`, and a
`job.completion_proof_submitted` that carries real evidence instead of only
free text. New `workforce_api/services/logistics_events.py` owns the rules;
views stay thin. Leg progression is forward-only (skips allowed, backwards
refused) and idempotent on retry. The trip starts itself: accepting a
transport job sets `EN_ROUTE_PICKUP`, and submitting proof sets `DELIVERED`.
Only those two are inferred — `LOADING` / `EN_ROUTE_DROP` / `UNLOADING` are
genuine driver signals and are never guessed from a status change.

**2. Server-authoritative fare quote.** `POST /api/logistics/quote/` returns
the itemised fare *before* the customer commits. Mini Truck and Two-Wheeler
call it and render the result; neither computes a fare any more. Packers &
Movers is refused explicitly (`CATEGORY_NOT_QUOTABLE`) because its pricing is
survey/volume/crew-driven.

**3. Dispatch concurrency.** Three layers, with the database constraint
deliberately kept as the last: live-offer exclusion during candidate
generation, an `Employee` row lock plus re-check before creating the offer,
and the existing unique constraint — which now surfaces as a clean
`DispatchRaceLost` result instead of an `IntegrityError` escaping dispatch.
Dispatch also walks the ranked candidates now rather than failing the whole
run when the top one is taken.

**4. Location coordinates.** `resolveLocationCoords()` resolves real
coordinates for the 62 database entries that carry none, using the same
geocoding providers the online search already uses. **Every hardcoded
fallback coordinate is gone** — a booking whose pickup cannot be pinned is
refused rather than placed at a made-up point.

**5. Three live 500s and an N+1**, found by investigating the failing suite —
see *Test results* below.

**6. A full end-to-end test** covering the entire journey through real
endpoints and the real webhook receiver.

---

## What was already present and reused

The booking flow and zone gate; the `logistics` catalog (`ServiceTier` /
`Lane` / `ServiceArea`); the 9-gate dispatch engine with ranking, exclusive
offers and radius widening; live tracking with GPS, WebSocket broadcast and
tracking tokens; the idempotent webhook receiver and its replay guard; the
`notify_customer_app` sender; `BookingAssignment`, `TechnicianLocation`,
`WorkExtension`, `CashSettlement` + `compute_outstanding_cash`; the Django
cache framework; and — from the first pass — the routing service, fare
engine, proof-of-delivery models and fare reconciliation. `TripStop` and
`WorkforceJobLogisticsLegView` already existed and were extended, not
replaced.

---

## Customer changes

- `logistics/views.py`, `logistics/urls.py` — the quote endpoint.
- `quicktims/settings.py` — its own throttle scope (each cache miss is a
  billed Maps call; it must not be a free proxy to a metered API).
- `service_requests/models.py` — forward-only, out-of-order-tolerant
  `set_logistics_leg()`.
- `service_requests/technician_views.py` — repaired onto the current model.
- `service_requests/serializers.py` — batched the payment-OTP lookup.
- `service_requests/notifications.py` — `notify_painting_quote_sent()`.
- `service_requests/views.py` — `_humanised_technician_name()`, quote-
  notification wiring.
- Frontend: `logisticsService.fetchLogisticsQuote()`,
  `hosurLocations.resolveLocationCoords()`, and all three booking pages.

## Vendor / Driver changes

- `workforce_api/services/logistics_events.py` (new) — leg rules and all
  four emissions.
- `workforce_api/views.py` — leg endpoint now ordered/idempotent/emitting;
  new `WorkforceJobTripStopsView`; proof endpoint emits the rich payload.
- `workforce_api/services/automatic_dispatch.py` — the concurrency guard.
- `service_requests/models.py` — unmanaged `TripStop` / `DeliveryProof`
  mirrors (the established pattern for shared tables).
- `service_requests/state_machine.py` — first leg on acceptance.

## API changes

| Endpoint | Change |
|---|---|
| `POST /api/logistics/quote/` | **New.** Authoritative fare. Public, throttled. |
| `GET/POST /workforce/jobs/<pk>/stops/` | **New.** Driver sees and advances stops. |
| `POST /workforce/jobs/<pk>/logistics-leg/` | Forward-only, idempotent, emits an event; returns `changed`. |
| `POST /workforce/jobs/<pk>/proof/` | Accepts recipient/stop/location; emits the rich proof event. |
| Webhook receiver | Consumes the three new events + the enriched proof payload. |
| Tracking payload | Gains a `logistics` block (leg, history, stops, proofs). Non-logistics bookings get the same empty shape. |

No breaking changes: every addition is additive, and existing consumers see
the same keys.

---

## Database / migration status

**Nothing has been applied.** This environment has no route to the live
Postgres host; that is stated rather than worked around. Migrations from both
sessions: Customer `0063`–`0068`, vendor `0001`×2 and `0022`. All of session
2's model additions are unmanaged mirrors — **no new migration was needed**.

**One item genuinely needs you.** The `Addon.package` AlterField has been
excluded five times. Verified against Django directly:

- model today: `null=False, on_delete=CASCADE`
- database today (migration 0058): `null=True, on_delete=SET_NULL`

Run this before it can ever be applied:

```sql
SELECT count(*) FROM service_requests_addon WHERE package_id IS NULL;
```

It must be `0`; otherwise backfill first, or the migration fails on contact.
Separately, confirm the `SET_NULL → CASCADE` change is intended — after it,
deleting a Package deletes its Add-ons instead of orphaning them.

---

## Complete booking flow status

Working end to end and covered by the new test: quote → booking → driver
matched → accepted → en route to pickup → arrived → loading → in transit →
arrived at drop → unloading → proof of delivery → delivered → reconciliation
→ payment → invoice → rating.

## Fare status

Server-authoritative throughout. The quote the customer sees and the fare the
booking records come from the same computation — the end-to-end test submits
`total_amount: 1.00` and asserts `530.00` is stored. Distance variance at
completion is re-priced at the rate **locked into the original quote**, not
the tier's live rate, so changing a rate cannot move an agreed fare.

## Dispatch status

Ten gates including the cash float ceiling; a Porter-style 20/25/30s offer
ladder for transport only; and the concurrency guard above. Existing
protection was strengthened, not weakened — two tests assert the database
constraint is still created and still not removed.

## Tracking status

Leg-aware destination verified end to end: once past pickup the tracking
destination becomes the drop point. The `logistics` block exposes leg,
history, per-stop timestamps and proofs. Out-of-order webhook delivery cannot
drag the view backwards.

## Proof-of-delivery status

Photo, signature, recipient identity, OTP and notes, each a separate record,
linked to a stop when one is named. `recipient_phone` is never exposed —
asserted by test.

---

## Test results

| Suite | Before | After |
|---|---|---|
| Customer `service_requests` | 29 failures + 17 errors (46) | **9 failures + 4 errors (13)**, 5 skipped, 234 tests |
| Goods & Transport suites | — | **122 tests, all passing** |
| Vendor dispatch + events | — | **49 tests, all passing** |
| Frontend eslint | — | **0 errors** |

**Genuine bugs fixed** (not assertions edited):

1. **Every `/api/technician/bookings/*` endpoint returned 500.** Live, routed
   endpoints still used the removed `technician` FK and ~10 sibling columns.
   Rewritten onto `BookingAssignment` + `TechnicianLocation` + status. This
   also corrects migration 0064's header, which claimed those fields were
   unreferenced — they were not.
2. **Quotation submission returned 500** — `send_quote_notification()` was
   called but never existed anywhere.
3. **A service slug could be shown as the technician's name.**
4. **N+1 across four customer list endpoints** — a raw per-row query against
   the vendor's notification table, now one query per page.

**Stale tests updated**, each because behaviour changed deliberately and the
intent is documented in the code: a removed webhook skeleton key, an
anonymous OTP bypass that is now admin-only, a superseded tracking-payload
contract, tests that booked for *today* against a 6 PM cut-off (they passed
every morning and failed every evening), and a removed client-amount fallback.

**Skipped, not deleted:** four tests covering server-side saved-address
resolution, a capability that no longer exists. One of them encodes a
tenant-isolation requirement worth keeping on record.

**Still failing (13), diagnosed:** `test_painting_module` (9 — masonry
validation wording and a 403, an unrelated module), `test_standalone_workforce_integration`
(3 — SQLite "table is locked" from the booking-creation background thread, an
environment artifact PostgreSQL does not have; plus one stale GPS assertion),
`test_bridge_verification` (1).

---

## Remaining blockers / manual actions

1. **Run the `Addon.package` query above.** The only thing genuinely blocked.
2. **The driver mobile app must call the new endpoints** — `logistics-leg/`,
   `stops/`, and the richer proof payload. Both backends are ready; the
   Flutter client is not. This is now the last gap between "works" and
   "works in production".
3. **Nothing is pushed**, and Customer `0064` / vendor `0022` are destructive
   — read their headers first.
4. **Vendor migrations cannot be replayed on SQLite** (`vendor_wallet` 0002
   removes a field 0001 indexed; a later migration has a raw `DO $$` block).
   Production is unaffected, but local/CI testing on SQLite is impossible for
   that app until they are made backend-agnostic.
5. **Backfill lat/lng onto the 62 `HOSUR_LOCATIONS_DATABASE` entries** from a
   real geocoding pass — deliberately not hand-typed, because invented
   coordinates would look authoritative while being wrong.
6. **Product decision:** restore server-side saved-address location
   resolution, or leave it to the frontend?
7. **A successful Google Maps response has still never been observed here** —
   the proxy refuses `maps.googleapis.com`. The fallback is proven against
   real refusals; confirm Distance Matrix is enabled on the key at deploy.
8. **Manual deletes** (this sandbox cannot delete files):
   `backend/service_requests/tests/test_zz_diag.py` (emptied),
   `backend/service_requests/migrations/0068_alter_addon_package_farereconciliation.py.superseded`
   (inert), `.git/_stale_locks/`, `.git/objects/**/tmp_obj_*`.

**Untouched throughout:** the ~1083-file pre-existing CRLF conversion, the
vendor AC-estimation work (~427 lines), the one-line `WorkforceJobListView`
fix, and the pre-existing git stash. Where a file mixed my change with that
state, only my hunks were staged, via git blob isolation.

---

## Commit hashes

**Customer** (`stage0-platform-hardening`)

| Hash | |
|---|---|
| `6bfe1f32` | tolerate out-of-order logistics leg events |
| `5405790b` | server-authoritative fare quote + booking pages use it |
| `d60d4d33` | resolve real coordinates; drop the hardcoded fallback |
| `e9408822` | three live 500s + an N+1 |
| `1c0d856d` | full end-to-end journey test |

*Earlier in this engagement:* `57a912c7`, `7766993b`, `c2d6c4d4`, `76b59e92`,
`5371c4f4`, `b817262b`, `8749b487`, `aec9bc42`, `e899cb1f`, `6dbeb978`.

**Vendor** (`stage0-platform-hardening`)

| Hash | |
|---|---|
| `3a00715` | driver-side logistics lifecycle events |
| `d0142a4` | dispatch concurrency guard |

*Earlier:* `b84d557`, `203eac7`, `dad1f87`, `3b42a59`.
