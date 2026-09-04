# SEVO Platform — Production Readiness Report

**Prepared for:** Caldim Engineering
**Date:** September 3, 2026
**Scope:** Customer app (`Customer/backend`, `Customer/frontend`) + Vendor/provider app (`vendor/backend`, `vendor/frontend`), working branch `testing`. Mobile app repo was not touched or reviewed, per standing instruction.

## Update: 12 fixes landed since this report was first sent

Everything in the "What I'm doing next" list at the bottom got done, each as its own compile-checked, diff-reviewed, individually committed change on `testing`:

- **Blockers fixed:** rescheduling no longer crashes and rolls back every request (the customer app called the vendor bridge with the wrong argument names); cancelling a job now actually reaches the vendor side and releases the technician (previously a wrong URL, wrong auth scheme, and wrong target endpoint meant this silently no-op'd every time -- I built a real internal endpoint for it, authenticated with a shared secret); the live-tracking WebSocket no longer grants anyone who guesses a booking ID full read access with no login or token required.
- **Security fixed:** the two IDOR endpoints (supplemental invoices, reschedule) now check company ownership; the same missing-company-check pattern was swept across 7 more endpoints; the webhook secret between the two apps no longer silently falls back to a well-known default string -- it now fails closed in production if unset; `ALLOWED_HOSTS` in the Customer app now actually reads its own env var instead of ignoring it and hardcoding `"*"`.
- **Map/UX fixed:** the "Live GPS" badge and fast-reconnect polling now actually reflect real connection health instead of always showing green; the three technician driving-nav screens now show a real error and a Retry button if Google Maps fails to load, instead of a permanent black screen; a related loader bug that permanently broke maps for the rest of the page session after one transient failure is fixed too.
- **Data integrity fixed:** a duplicate cancel request (double-click, retry) no longer creates a second refund request for an already-cancelled booking.

**Important, still needs your action:** the webhook-secret fix means both apps will refuse to start in production if `WORKFORCE_WEBHOOK_SECRET` isn't set to a real value in both apps' `.env` files (same value on both). This is on the `testing` branch, not yet on the deploy branch, so nothing is live yet -- but set that before merging it forward.

## How to read this

You asked me to examine the map work, find the holes standing between this app and production, and fix what I safely can myself. I ran four separate, deep investigations — map/tracking, security & tenant isolation, booking lifecycle edge cases, and infrastructure/deployment — on top of the 9 data-accuracy bugs already fixed and committed earlier this pass (wrong prices on the vendor jobs list, wallet not crediting after cash-OTP completion, fake OTP/data fallbacks on the customer decision screen, and others).

This report is the findings from those four investigations. Nothing below has been fixed yet — that's the next phase, and I've already queued it as tracked tasks so you can watch it land fix-by-fix, each one `py_compile`-verified, diff-reviewed, and committed on its own, the same way the earlier 9 bugs were handled.

Three things are true at once about this codebase: it has real, substantive engineering behind it (the RazorpayX payout integration, the refund/dispute flow, the technician reassignment logic, and Gokul's map/navigation work are all genuinely built, not stubs); it also has the kind of gaps you'd expect from fast-moving parallel development — a few security holes, a couple of cross-app integrations that were wired with the wrong function signature and have never actually worked, and no safety net (error tracking, health checks, CI gating) around any of it yet. None of that is unusual for an app at this stage. But "production-ready" means closing the gaps below first.

## Severity key

**BLOCKER** — a core feature is currently broken or silently non-functional for every user, every time. **CRITICAL** — a live security hole or data-integrity risk reachable by any authenticated (or unauthenticated) user right now. **HIGH** — a real defect or gap with a plausible, damaging trigger in normal use. **MEDIUM** — a real gap, lower likelihood or impact. **INFO** — reviewed and confirmed working correctly; listed so you know it was checked.

---

## 1. Blockers — things that don't work at all today

**Rescheduling a booking can never complete.** The customer-side reschedule code (`service_requests/services/__init__.py`) calls into the vendor bridge with the wrong argument names — it passes `booking_id=` and `new_time_slot=`, but the bridge function's real signature takes `service_request=`, `new_date=`, `new_time=`. Every single reschedule request raises a `TypeError`, and because it's inside a database transaction that has already updated the reschedule request's status, the whole transaction rolls back every time. On top of that, once the name mismatch is fixed, the constructed request URL is also missing the job's ID, so it wouldn't reach the right vendor-side route anyway — and nothing re-runs availability/dispatch logic for the new time slot even when it does go through, so a job would stay pinned to a technician regardless of whether they're free at the new time.

**Cancelling an assigned job never frees the technician.** When a customer cancels, the customer app calls the vendor app to release the assignment, using a hardcoded `Authorization: Bearer wf_integration_key_default` header — a scheme the vendor app's authentication doesn't recognize at all, so the call always fails with 401/403. The bug that makes this dangerous rather than just broken: both the exception path and the failed-response path in that bridge call are caught and turned into `{"success": True, "fallback": True}` — a silent, hardcoded success. So the customer app has no idea it failed, the technician's job is never actually cancelled on the vendor side, `Employee.current_availability` stays "busy" forever, and that technician is silently excluded from all future dispatch until they happen to manually toggle their status off and back on. There's no background sweep that would ever catch this on its own.

**Any live-tracking WebSocket connection is unauthenticated.** `TrackingConsumer._is_authorized()` in the Customer backend has four authorization branches; the fourth one is `if self.sr: return True` — meaning if the client supplies a valid `request_id` or numeric ID for *any* booking, it gets full read access to that booking's live GPS position, technician name and photo, ETA, and customer address, no login required. This directly contradicts the properly-secured REST endpoint that serves the same data (`CustomerBookingLiveLocationView`), and a code comment sitting right next to it acknowledges the gap exists while only fixing a different, adjacent issue. This is exploitable today by anyone who can guess or enumerate a booking ID.

## 2. Critical — live security and data-integrity risk

**Real credentials are committed to git.** `Customer/backend/.env.pre-cutover` and `.env.production` are tracked at HEAD (the `.gitignore` in the Customer repo is missing the wildcard the vendor repo already has). Based on their format — not their content, which I did not print or copy anywhere — they contain what look like a real database password, a Gmail App Password, Google Maps/OAuth keys, and a Google OAuth client secret. The database host in these files doesn't match the vendor app's current `.env`, so that credential may already be stale, but the email, Maps, and OAuth secrets are independent of that and are very likely still live.

**Two endpoints let any authenticated account act on any other company's jobs (IDOR).** `WorkforceCreateSupplementalInvoiceView` and `WorkforceJobRescheduleView` only check that the requester is logged in — there's no check that the job actually belongs to their company. Anyone with any account on the platform can create a billing invoice against, or reschedule, a job that isn't theirs, just by guessing or incrementing an ID. The correct pattern already exists elsewhere in the same file (`WorkforceJobExtensionView`, `WorkforceJobProofView`) — it just wasn't applied consistently.

## 3. High — real defects, plausible triggers

- **`is_admin_role` checked without a company-ownership check**, the same class of bug as the IDOR above, recurring across six more endpoints: purchase requests and their admin decision, customer extension detail/decision, the customer-facing supplemental invoice list, the reschedule-response view, and the auto-dispatch trigger. Any company's admin account can act on another company's data through these.
- **The webhook secret between the two apps is set to its own hardcoded default.** Both apps fall back to the literal string `wf_webhook_secret_default` when the `WORKFORCE_WEBHOOK_SECRET` env var is unset — and it's confirmed unset in both live `.env` files today. The signature check itself (`hmac.compare_digest`) is implemented correctly; it's just checking against a secret anyone could look up in the source.
- **`ALLOWED_HOSTS` is hardcoded to `["*"]`** in the Customer backend's settings, silently ignoring the `DJANGO_ALLOWED_HOSTS` variable that's already set correctly in the `.env` files — host-header validation is fully disabled in the app that's actually running.
- **Both apps fail open if `DEBUG` is ever left unset on a future deploy** — vendor's settings default to `DEBUG=True`, `ALLOWED_HOSTS=["*"]`, and `CORS_ALLOW_ALL_ORIGINS=True` simultaneously in that case, unlike `SECRET_KEY`, which correctly refuses to start.
- **No file-type or size validation on uploaded proof/inspection photos**, combined with a missing `X-Content-Type-Options: nosniff` header on the media-serving nginx location block — together these allow a disguised HTML/SVG "photo" upload to be served from the app's own origin and executed as a script (stored XSS).
- **The connection-health badge on the customer tracking map is fake.** The code treats the WebSocket connection-state callback as a true/false value, but the real callback always sends one of four strings (`"connecting"`, `"connected"`, `"reconnecting"`, `"disconnected"`) — all of which are truthy in JavaScript. So the "🟢 Live" badge is always green, the "Offline" state never shows, and the fast-polling fallback that's supposed to kick in when the socket drops never activates. The underlying data still updates via REST polling underneath, so tracking isn't literally frozen — but the health indicator lies.
- **No fallback UI if Google Maps fails to load** in the vendor app's three core navigation screens (standby, first-person nav, arrival) — a bad API key, network block, or ad-blocker produces a permanent black screen with dead buttons. Three sibling map components elsewhere in the same codebase already handle this correctly, so the pattern exists, it just wasn't used here. Compounding it, a failed load is never retried for the rest of that browser session.
- **No customer notification exists for cancellation at all** — the notification system has functions for assignment, reschedule, refund, and complaints, but none for "your booking was cancelled."
- **Refund and wallet clawback are disconnected.** The refund flow genuinely calls Razorpay and processes real money back to the customer; the wallet clawback function is genuinely correct on its own. But nothing calls clawback when a refund is approved, so a technician can keep a wallet credit for a job whose payment was fully refunded, with no flag anywhere recording that money is owed back.
- **No duplicate-request guards on refunds** — a customer can submit more than one refund request for the same booking, and the refund executor doesn't check whether that payment was already refunded by an earlier approved request.
- **No-show / arrival-timeout handling doesn't exist anywhere in the code**, despite a design document describing it as already built.

## 4. Medium

- Auto-refund-request creation on cancel is wrapped in a bare `except: log and swallow` — a paid, cancelled booking can end up with no refund process at all if that step fails.
- `GPS permission denied` on the technician side is captured correctly but never surfaced in the technician UI — they just lose dispatch/map functionality with no explanation.
- `JobLocationPoint` and the location-update event log grow forever — no retention policy or cleanup job.
- Cancelling a job twice (double-click, retry) is allowed to re-run the entire cancel handler, including refund-request creation — because `apply_transition` treats `CANCELLED → CANCELLED` as always-allowed and the view has no "already cancelled" guard.
- OTP endpoints use adequate hand-rolled rate limits, but they're backed by Django's in-memory cache — the moment either app is scaled to more than one worker process, those limits silently fragment across processes with no warning.
- The `.env.example` template in the Customer frontend has values in real-looking API-key format rather than obvious placeholders — worth cleaning up so nobody mistakes it for a real config.

## 5. Confirmed clean

Worth knowing what's *not* broken: Razorpay checkout signature verification and the RazorpayX payout webhook verification are both still correctly implemented. Technician reassignment/redispatch after a cancelled assignment is thorough and correct, including cache invalidation and re-broadcasting. The wallet clawback function itself handles both held and released balances correctly. No SQL injection was found anywhere reachable from the web. Several other `AllowAny` endpoints were spot-checked and are intentionally public. Gokul's map and navigation system is a real, substantial, mostly-complete build — not a placeholder — split across two independent stacks (Google Maps for the vendor/technician side, Leaflet + OpenStreetMap/OSRM for the customer side), which is an architectural choice worth eventually consolidating but isn't itself a defect.

## 6. Infrastructure — what's missing before this can run unattended

No error tracking (Sentry or equivalent) exists in either app. Neither app has a generic health-check endpoint suitable for a load balancer. The vendor repo currently has two competing, unreconciled migration "leaf" merges sitting in its history at once — an active fork in the migration graph. The vendor app has no task queue at all (no Celery) — dispatch relies on a polling command that needs an external supervisor to stay alive, and cross-app webhook notifications are explicitly fire-and-forget on daemon threads, so a process restart mid-flight loses them permanently with no retry or alert. The Customer app does have a real Celery setup. Both apps have substantive backend test suites (dozens of real assertions), but neither is wired into CI — the vendor repo's CI only runs `manage.py check`, and the Customer repo has no CI at all. The vendor app's auto-deploy workflow pushes straight to the production VPS on every push to its deploy branch, gated by nothing. Neither frontend has meaningful test coverage.

---

## What I'm doing next

I've queued the fixes that are safe for me to make directly — mechanical, self-contained, and verifiable the same way the earlier 9 bugs were (compile-check, scoped diff review, one commit per fix): the reschedule `TypeError`, the broken cross-app cancel call, the two IDOR views, the company-check sweep, the hardcoded webhook secret, the `ALLOWED_HOSTS` hardcoding, the WebSocket auth hole, the fake connection badge, and the Maps failure fallback. I'll work through these one at a time and report back as they land.

A few things are genuinely outside what I can do from here, because they require access I don't have or a decision only you can make:

- **Rotating the leaked credentials** — the database password, Gmail app password, Maps/OAuth keys — has to happen in the Google Cloud Console, Gmail account settings, and your Razorpay dashboard, then the new values need to go into your real `.env` files on the server. I can remove the files from git going forward and fix the `.gitignore`, but I can't rotate secrets in third-party consoles myself.
- **Consolidating the two map stacks** (Google Maps vs. Leaflet/OSRM) into one is a real architectural decision with cost implications (Google Maps billing vs. free OSM tiles) — I'd want your steer before picking one and ripping out the other.
- **Setting up Sentry, CI test-gating, and a secrets manager** are infrastructure decisions I can scaffold once you tell me which providers you want (e.g., which Sentry plan, whether GitHub Actions secrets are acceptable or you want a dedicated vault).
- **The two conflicting migration leaves in the vendor repo** need a decision about which one is authoritative before I merge them — I don't want to guess on your live schema history.
- **Building out no-show/arrival-timeout dispatch escalation** is a genuinely new feature, not a bug fix — happy to build it once we've scoped what "no-show" should actually trigger (auto-reassign? notify ops? refund?).

I'll flag each of these again as I reach them in the fix queue, in case you want to unblock any in parallel.
