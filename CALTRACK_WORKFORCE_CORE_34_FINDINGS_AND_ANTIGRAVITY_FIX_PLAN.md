# CalTrack Workforce — Core Application Code Audit
## 34 Executable Findings + Root Causes + Permanent Fix Plan + Antigravity Prompt

**Audit target:** latest uploaded `workforce-app.zip`

**Primary focus:** job dispatch, job fetch, candidate eligibility, offer lifecycle, assignment, redispatch, workflow/state machine, Redis, SSE/realtime, GPS/location, live tracking, maps/navigation, and the technician-side UI paths that directly affect those flows.

**Audit method:** line-level review of the current non-backup backend/frontend source with call-site tracing across the core execution paths. Backup trees under `.backup_outer_pre_vendor_replace/` were not treated as live implementation. The audit follows the runtime call graph rather than merely reading feature names/comments.

> **Important:** This document identifies code-level defects and architectural risks visible in the supplied snapshot. It does not claim that every item has already reproduced in production. Findings are marked by confidence and impact.

---

# Executive Verdict

## Production status

**NOT PRODUCTION-SAFE YET for the core Workforce job/dispatch/realtime/location workflow.**

The dominant problem is **trigger duplication**:

```text
GPS update ───────────────┐
Presence toggle ──────────┤
Jobs GET ─────────────────┤──> dispatch reconsideration
SSE connection ──────────┤
Redis worker ─────────────┘

                         + multiple event-writing paths
                         + multiple location producers
                         + multiple state consumers
```

This creates a system where a read, a GPS packet, or an SSE connection can indirectly start expensive business processing. That increases DB pressure, makes realtime less stable, and makes job visibility/assignment behavior timing-dependent.

The fastest permanent stabilization is **not** to redesign the whole app. It is to enforce four boundaries:

```text
1. ONE dispatch engine
2. ONE authoritative event publisher
3. ONE continuous GPS producer
4. PostgreSQL = durable source of truth; Redis = transport/acceleration only
```

---

# Severity Key

- **P0 — Critical:** correctness, duplicate dispatch, assignment integrity, or production stability risk.
- **P1 — High:** strong operational/functional flaw likely to affect users or scale.
- **P2 — Medium:** correctness/maintainability issue that becomes important as usage grows.

---

# 34 Findings

## 1. Dispatch is triggered from multiple unrelated request paths

**Severity:** P0

**Where:**
- `backend/workforce_api/views.py:2046-2050`
- `backend/workforce_api/views.py:2127-2158`
- `backend/workforce_api/views.py:6167-6168`
- `backend/workforce_api/views.py:7034-7035`
- `backend/workforce_api/services/automatic_dispatch.py`
- `backend/workforce_api/services/redis_dispatch.py`

### What is causing it

The same `reconsider_jobs_for_employee()` operation can be launched from:

- online/presence changes;
- `GET /jobs`;
- GPS update requests;
- the SSE stream;
- the independent dispatch worker.

### What this affects

A single technician can cause several independent reconsideration operations to overlap.

That affects:

- DB load;
- dispatch latency;
- offer duplication pressure;
- SSE stability;
- job visibility timing;
- Redis queue usefulness;
- overall predictability.

### Root cause

**Business orchestration is embedded inside transport/UI endpoints instead of one dispatch boundary.**

### Permanent fix

Make automatic dispatch executable only through one explicit service/worker path:

```text
business event
   ↓
enqueue_dispatch(job_id, reason)
   ↓
one dispatch worker
   ↓
dispatch_job(job_id)
```

Remove direct `reconsider_jobs_for_employee()` launches from presence, jobs GET, GPS, and SSE.

### Acceptance check

Search all call sites and prove that request handlers do not directly invoke dispatch/reconsideration except the dedicated dispatch service/worker.

---

## 2. SSE still runs dispatch reconciliation inside the long-lived stream

**Severity:** P0

**Where:** `backend/workforce_api/views.py:7007-7040`

### What is causing it

Inside `event_stream()` the server periodically executes:

```python
reconsider_jobs_for_employee(emp_obj)
```

### What this affects

The SSE stream becomes dependent on the runtime cost of dispatch.

A long dispatch cycle can delay:

- heartbeats;
- event delivery;
- reconnect behavior;
- proxy stability.

This is directly relevant to the earlier `ECONNRESET` symptoms.

### Root cause

**SSE is being used as an execution scheduler instead of an event transport.**

### Permanent fix

Delete dispatch/reconsideration from `event_stream()` entirely.

SSE must only:

```text
authenticate
→ subscribe/read events
→ emit events
→ emit heartbeat
→ cleanup
```

Dispatch must run independently.

### Acceptance check

`rg` for `reconsider_jobs_for_employee` and `dispatch_job` inside realtime/SSE code must return zero business-execution calls.

---

## 3. Every GPS update can spawn dispatch reconsideration

**Severity:** P0

**Where:** `backend/workforce_api/views.py:6167-6168`

### What is causing it

The location endpoint launches:

```python
threading.Thread(
    target=reconsider_jobs_for_employee,
    args=(emp.id,),
    daemon=True,
).start()
```

### What this affects

The GPS subsystem becomes a dispatch scheduler.

With continuous tracking, the same technician can generate repeated dispatch work at telemetry frequency.

### Root cause

**Telemetry and business orchestration are coupled.**

### Permanent fix

GPS endpoint should only:

1. validate location;
2. persist latest location;
3. update active tracking state;
4. optionally update Redis location state;
5. emit location event when appropriate.

No dispatch call.

If employee availability changes because location makes them eligible/ineligible, publish an explicit availability event or let the dedicated dispatch worker reconcile on its own schedule.

### Acceptance check

No dispatch/reconsideration calls remain in GPS update handlers.

---

## 4. Job list GET also starts dispatch work

**Severity:** P0

**Where:** `backend/workforce_api/views.py:2127-2158`

### What is causing it

The employee job-list GET performs a background sweep and then directly starts `reconsider_jobs_for_employee()` for the employee.

### What this affects

A read operation can mutate system behavior and begin dispatch.

This creates:

```text
open Jobs page
→ dispatch starts
→ refresh page
→ dispatch starts again
```

### Root cause

**CQRS boundary violation:** query/read endpoint is performing command/business scheduling.

### Permanent fix

`GET /jobs` must be read-only.

It may reconcile derived display data only if that work is bounded and non-mutating. It must not enqueue or execute dispatch.

### Acceptance check

Calling the jobs endpoint twice must not create new dispatch work by itself.

---

## 5. Offer creation sends `technician.assigned` before acceptance

**Severity:** P1

**Where:** `backend/workforce_api/services/automatic_dispatch.py:935-948`

### What is causing it

When an offer is merely created, the code calls the Customer webhook with:

```text
technician.assigned
```

while `WorkforceJobOffer.status` is still `OFFERED`.

### What this affects

Downstream Customer-side integrations can interpret “assigned” as a confirmed technician assignment even though the technician has not accepted yet.

### Root cause

**Offer lifecycle and assignment lifecycle use the same external event semantic.**

### Permanent fix

Create distinct event semantics:

```text
technician.offer_sent
```

at offer creation, and:

```text
technician.assigned
```

only after atomic acceptance succeeds.

Do not break the existing Customer integration contract blindly: update the event mapping in the Workforce integration layer and verify the consumer contract.

### Acceptance check

Offer creation produces no external “assigned” event. Accepted assignment produces exactly one.

---

## 6. Service matching uses permissive substring/alias rules

**Severity:** P0

**Where:** `backend/workforce_api/services/automatic_dispatch.py:153-194`

### What is causing it

Examples:

```python
req_clean in it_clean
it_clean in req_clean
```

and alias matching that uses individual request words.

### What this affects

Technicians can potentially match services for the wrong category when names overlap or aliases are too broad.

This is directly relevant to your rule:

```text
AC technician ≠ Painter ≠ Mason
```

### Root cause

**Human-readable service strings are being used as authorization logic.**

### Permanent fix

Dispatch authorization must be relational:

```text
Service
  ↓
required skill(s)
  ↓
verified employee skill(s)
```

Aliases may normalize labels, but cannot grant eligibility on their own.

### Acceptance check

Create an AC job with a painter-only technician and prove dispatch eligibility is false.

---

## 7. Empty service is treated as an eligibility bypass

**Severity:** P0

**Where:** `backend/workforce_api/services/automatic_dispatch.py:158-159`

### What is causing it

```python
if not requested_service:
    return True, "EMPTY_SERVICE_BYPASS", ""
```

### What this affects

Jobs with missing/empty service information can bypass service matching.

### Root cause

**Missing data is treated as permissive rather than unsafe.**

### Permanent fix

For automatic dispatch:

```text
missing service → cannot dispatch automatically
```

Return a clear reason such as `SERVICE_REQUIRED_FOR_DISPATCH` and escalate to admin/manual routing.

### Acceptance check

A job without service/category must remain unassigned and produce a diagnostic reason.

---

## 8. The dedicated relational service-skill requirement model is not the dispatch authority

**Severity:** P0

**Where:** `backend/workforce_api/models.py:2109+`

Model:

```text
WorkforceServiceSkillRequirement
```

but the dispatch gate primarily evaluates onboarding strings and verified skills through `canonical_service_match()`.

### What this affects

There is now a source-of-truth conflict:

```text
relational configuration
vs
string matching
```

### Root cause

**The schema supports stronger authorization than the runtime uses.**

### Permanent fix

Refactor Gate 6 to use:

```text
WorkforceServiceSkillRequirement
→ required skill IDs
→ employee verified skill IDs
```

Aliases only normalize service selection before this relational comparison.

### Acceptance check

The same service always maps to the same required skill set irrespective of wording differences.

---

## 9. Dispatch ranking is distance-first, not score-first

**Severity:** P1

**Where:** `backend/workforce_api/services/automatic_dispatch.py:635-646`

### What is causing it

Final sort is:

```python
ranked_candidates.sort(
    key=lambda x: (x["distance_km"], -x["score"])
)
```

### What this affects

A much higher quality technician can lose to a slightly closer technician.

Example:

```text
Tech A: 2 km, score 40
Tech B: 4 km, score 100
→ Tech A wins
```

### Root cause

The code computes a composite score but the final ordering primarily ignores it.

### Permanent fix

Choose one explicit ranking policy.

Recommended:

```text
hard gates first
→ composite score
→ distance as deterministic tie-breaker
```

Do not leave ranking semantics implicit in a tuple sort.

### Acceptance check

Add a test where a farther high-score technician must win according to the chosen business rule.

---

## 10. One employee can hold multiple offers across different jobs

**Severity:** P1

**Where:**
- `backend/workforce_api/models.py:430+`
- `backend/workforce_api/services/workload.py`
- dispatch offer creation in `automatic_dispatch.py`

### What is causing it

The database uniqueness rule prevents duplicate offer rows for the same `(job, employee)` only. It does not enforce one live offer across all jobs for the employee.

The current `supersede_other_offers_for_employee()` behavior primarily resolves this after an acceptance.

### What this affects

A technician can potentially see several competing exclusive offers before choosing one.

### Root cause

**Offer concurrency policy is not enforced at the database/dispatch boundary.**

### Permanent fix

Decide the business rule explicitly.

For the CalTrack single-active-workload model, recommended:

```text
one employee = max one OFFERED job
```

Enforce it transactionally in dispatch, with a partial unique constraint if PostgreSQL schema permits the exact semantics, or a transaction-locked availability/offer reservation strategy.

### Acceptance check

Dispatch two jobs concurrently to the same technician and prove only one remains `OFFERED`.

---

## 11. Offer wave metadata exists but dispatch does not implement a real wave engine

**Severity:** P1

**Where:**
- `backend/workforce_api/models.py:434-450`
- `backend/workforce_api/services/automatic_dispatch.py:780+`

### What is causing it

`WorkforceJobOffer` stores `wave_number` with an allowed range of 1–6, but offer creation does not visibly select a real dispatch wave and defaults to the initial value.

### What this affects

The schema suggests progressive waves while the dispatch implementation effectively behaves like a single-candidate offer cycle plus redispatch.

### Root cause

**Data model and execution model are out of sync.**

### Permanent fix

Either:

1. implement real wave progression; or
2. remove/deprecate unused wave semantics.

Recommended implementation:

```text
wave 1 → candidate subset
wait/expire
wave 2 → next subset
...
```

using explicit candidate history and deterministic wave IDs.

### Acceptance check

A dispatch test must show the exact sequence of candidates by wave.

---

## 12. Redis dispatch consumer acknowledges business failures too broadly

**Severity:** P1

**Where:** `backend/workforce_api/services/redis_dispatch.py:450-458`

### What is causing it

After:

```python
success, msg = reconcile_fn(...)
```

the code calls `acknowledge_dispatch_job(msg_id)` regardless of whether `success` is true.

### What this affects

A Redis work item can be acknowledged even when the business operation returns a failure such as no candidate.

The DB sweep may later recover the job, but Redis is no longer a reliable representation of outstanding dispatch work.

### Root cause

**Transport success and business success are conflated.**

### Permanent fix

Distinguish:

```text
message successfully processed
```
from:

```text
dispatch found no candidate
```

Recommended:

- ACK when the message has been safely interpreted and the business outcome is durably represented;
- retain/retry only for retryable infrastructure failures;
- route poison messages to dead-letter after bounded attempts.

### Acceptance check

Test:

```text
Redis read succeeds
→ dispatch DB failure
→ no ACK
```

and:

```text
Redis read succeeds
→ valid no-candidate business result
→ ACK + durable unassigned state
```

---

## 13. Redis dispatch worker has no strong dead-letter / poison-message policy

**Severity:** P2

**Where:** `backend/workforce_api/services/redis_dispatch.py:308-369, 430-458`

### What is causing it

Pending message recovery uses reclaim/claim, but there is no clear bounded retry count + dead-letter policy.

### What this affects

A malformed or permanently failing dispatch message can repeatedly consume worker capacity.

### Root cause

**Retries are based on age, not bounded attempt semantics.**

### Permanent fix

Store/track retry attempt count and implement:

```text
attempt 1..N → retry with delay
attempt N+1 → dead-letter
admin-visible failure reason
```

Do not silently discard the job.

### Acceptance check

Inject a poison message and prove it is not retried forever.

---

## 14. `ServiceRequest.save()` still contains dispatch orchestration

**Severity:** P0

**Where:** `backend/service_requests/models.py:417-442`

### What is causing it

A model save can register `transaction.on_commit()` and enqueue dispatch, with a DB fallback to immediate reconciliation when Redis is unavailable.

### What this affects

Any code path that saves a `ServiceRequest` can unintentionally trigger dispatch.

This makes business behavior implicit and can surprise callers.

### Root cause

**Domain persistence and workflow orchestration are coupled inside the model layer.**

### Permanent fix

Move this logic into an explicit service:

```text
create/update booking
→ commit
→ enqueue dispatch command
```

Model `save()` should persist state only.

### Acceptance check

Saving an ordinary ServiceRequest field that does not represent a dispatch event must not enqueue dispatch.

---

## 15. Redis-unavailable fallback can still execute full dispatch synchronously after commit

**Severity:** P1

**Where:** `backend/service_requests/models.py:425-435`

### What is causing it

When Redis is unavailable, the post-commit callback calls:

```python
reconcile_booking_for_dispatch(..., use_redis_geo=False)
```

### What this affects

Redis outages can convert an inexpensive enqueue path into a synchronous, potentially expensive DB dispatch operation.

### Root cause

**Redis is optional, but the fallback strategy is not equally asynchronous.**

### Permanent fix

Use a durable database-backed dispatch-outbox/retry mechanism for Redis outage scenarios, or a single existing background worker that can poll pending dispatch rows.

Avoid running the full dispatch engine on an API callback path.

### Acceptance check

Disable Redis and create multiple jobs; request latency should remain bounded while jobs still enter a retryable dispatch queue.

---

## 16. Acceptance audit event records the wrong `previous_status`

**Severity:** P1

**Where:** `backend/workforce_api/views.py:3619-3723`

### What is causing it

The offer is changed:

```python
offer.status = "ACCEPTED"
offer.save()
```

before the lifecycle event is created. The later metadata uses:

```python
offer.status if offer else "OFFERED"
```

which can therefore produce `ACCEPTED` as the previous status.

### What this affects

Audit/history consumers can see:

```text
previous_status = ACCEPTED
new_status = accepted
```

instead of:

```text
previous_status = OFFERED
new_status = accepted
```

### Root cause

**Previous state is read after mutation.**

### Permanent fix

Capture before mutation:

```python
previous_offer_status = offer.status
```

then write the lifecycle event from that immutable variable.

### Acceptance check

Acceptance lifecycle event must always report the real pre-transition value.

---

## 17. Redis GEO implementation exists but is not the canonical candidate-selection path

**Severity:** P1

**Where:**
- `backend/workforce_api/services/redis_dispatch.py:40-220`
- `backend/workforce_api/services/automatic_dispatch.py:410-647`
- `backend/workforce_api/services/automatic_dispatch.py:1108-1110`

### What is causing it

Redis GEO supports:

```text
update_technician_dispatch_geo()
find_nearby_technician_candidates()
```

but the main `get_eligible_candidates()` implementation shown in the live dispatch path scans employee candidates through PostgreSQL and calculates Haversine distance directly.

### What this affects

Redis GEO can become decorative infrastructure rather than an actual optimization.

### Root cause

**There are two candidate-discovery implementations, but the boundary between them is incomplete.**

### Permanent fix

Pick a declared architecture.

Recommended production path:

```text
Redis GEO = shortlist only
PostgreSQL = authoritative eligibility verification
```

If Redis GEO is not ready, remove it from the claimed critical path and keep PostgreSQL authoritative.

### Acceptance check

The dispatch service must explicitly state whether Redis GEO is enabled and demonstrate the exact code path when enabled.

---

## 18. Redis GEO freshness policy differs from PostgreSQL dispatch freshness policy

**Severity:** P1

**Where:** `backend/workforce_api/services/redis_dispatch.py:32-37, 182-220` vs `backend/workforce_api/services/automatic_dispatch.py:34-35, 522-575`

### What is causing it

Redis GEO defaults to 120 seconds, while automatic dispatch uses `MAX_GPS_AGE_SECONDS = 300` (5 minutes).

### What this affects

The same technician can be:

```text
fresh enough for DB dispatch
but
stale in Redis GEO
```

or vice versa depending on configured overrides.

### Root cause

**No single location-freshness policy by business purpose.**

### Permanent fix

Define one canonical policy object/config:

```text
DISPATCH_LOCATION_MAX_AGE
TRACKING_LOCATION_MAX_AGE
UI_LOCATION_MAX_AGE
```

The dispatch service must use the same configured value for both Redis shortlist filtering and final DB verification.

### Acceptance check

A single test matrix must cover 0s/30s/120s/300s/301s location ages.

---

## 19. Event publishing is fragmented: many paths write `WorkforceEventLog` directly

**Severity:** P0

**Where:** multiple locations in:
- `backend/workforce_api/views.py`
- `backend/workforce_api/services/automatic_dispatch.py`
- `backend/workforce_api/services/workload.py`

Central abstraction exists at:
- `backend/workforce_api/services/realtime.py:166+`

### What is causing it

Some code paths use:

```python
WorkforceEventLog.objects.create(...)
```

while the central service offers:

```python
publish_workforce_event(...)
```

### What this affects

Some events can be durable in PostgreSQL but never go through the Redis realtime transport path.

### Root cause

**No single event-publication contract.**

### Permanent fix

Route every realtime-worthy business event through one publisher.

Do not ban direct event-row creation for purely internal audit events, but clearly classify:

```text
AUDIT_EVENT
REALTIME_EVENT
```

and enforce the corresponding path.

### Acceptance check

`OFFER_CREATED`, `JOB_ASSIGNED`, `STATUS_CHANGE`, `JOB_LOCATION_UPDATE`, `NOTIFICATION_CREATED` must have a documented publisher path.

---

## 20. SSE is PostgreSQL-polled every second instead of acting as a lightweight event pipe

**Severity:** P1

**Where:** `backend/workforce_api/views.py:7041-7058`

### What is causing it

The long-lived generator loops and queries `WorkforceEventLog` every second.

### What this affects

Connected technician count multiplies steady DB polling load.

Example:

```text
100 SSE clients × 1 DB query/sec ≈ 100 polling queries/sec
```

before other application traffic.

### Root cause

**SSE is implemented as frequent database polling, with no transport-level event wait.**

### Permanent fix

Preferred:

```text
Redis PubSub/stream → SSE
```

with PostgreSQL event log used for replay/recovery.

At minimum, increase the DB polling interval and only poll when there are no transport notifications, but do not add expensive dispatch logic to the loop.

### Acceptance check

Idle SSE should not generate one SQL query per second per client.

---

## 21. SSE reconnect has `Last-Event-ID` support server-side but the client does not visibly participate in replay

**Severity:** P1

**Where:**
- server: `backend/workforce_api/views.py:6975-6998`
- client: `frontend/src/hooks/useRealtimeStream.js:226+`

### What is causing it

The server reads `Last-Event-ID`, but the client opens the stream with only a token URL and the current client implementation does not clearly persist/send the last delivered event ID on reconnect.

### What this affects

Events emitted during a disconnect can be skipped.

### Root cause

**Replay protocol is only half implemented.**

### Permanent fix

Use both:

```text
Last-Event-ID replay
```

and:

```text
REST reconciliation after reconnect
```

The runtime should persist the last SSE event ID in memory/ref and send it on the next connection.

### Acceptance check

Emit event A, disconnect client, emit event B, reconnect, and verify B is either replayed by ID or recovered by mandatory REST reconciliation with no lost business state.

---

## 22. SSE/database connection lifecycle is overly defensive but still fragile because work happens inside the generator

**Severity:** P1

**Where:** `backend/workforce_api/views.py:7007-7098`

### What is causing it

The generator repeatedly calls `connection.close()` in multiple branches while remaining a long-running response.

The design is trying to manually control DB connections around a streaming request while the generator also performs periodic business work.

### What this affects

Hard-to-predict behavior under reconnects, DB restarts, proxies, and long-lived connections.

### Root cause

**The stream owns responsibilities that should be outside the stream.**

### Permanent fix

Keep the stream free of ORM-heavy work except bounded event fetches/replay.

Use a stable streaming connection strategy compatible with the deployment server, and ensure cleanup is deterministic on disconnect.

### Acceptance check

Open an SSE connection for several minutes and verify no repeated DB connection churn/error loop occurs.

---

## 23. `EmployeeJobsPage` duplicates runtime state and can remain stale

**Severity:** P1

**Where:** `frontend/src/pages/employee/EmployeeJobsPage.jsx:208-269`

### What is causing it

The page copies runtime data into:

```javascript
const [jobs, setJobs] = useState(cachedJobs);
```

and only synchronizes it when `cachedJobs.length > 0 && jobs.length === 0`.

### What this affects

Runtime can receive an event and refresh active jobs while the page still renders its own stale `jobs` array.

This directly matches the symptom:

```text
notification appears
but
job list does not update
```

### Root cause

**Two sources of client job state.**

### Permanent fix

Make runtime context authoritative for active jobs.

The page can derive:

```javascript
const jobs = combine(activeJobs, completedJobs)
```

without a second persisted local jobs store.

Keep local state only for UI concerns such as selection/loading/search.

### Acceptance check

A new offer event must change the rendered list without requiring a full page reload.

---

## 24. The dashboard/cockpit currently takes only the first incoming offer

**Severity:** P1

**Where:** `frontend/src/components/employee/dashboard/PortalCockpitLayout.jsx:123`

### What is causing it

```javascript
const offer = incomingOffers && incomingOffers.length > 0
  ? incomingOffers[0]
  : null;
```

### What this affects

If the runtime ever exposes multiple simultaneous offers, the cockpit can hide all but one.

### Root cause

**UI assumes one-offer semantics while the backend currently does not enforce it globally.**

### Permanent fix

Either:

- enforce one active offer per employee server-side and make this explicit; or
- make cockpit render a proper offer queue/list.

Do not let the UI silently mask backend concurrency.

### Acceptance check

Backend and UI tests must agree on the maximum number of live offers allowed.

---

## 25. Technician acceptance automatically starts `ON_THE_WAY`

**Severity:** P1

**Where:** `frontend/src/pages/employee/EmployeeJobsPage.jsx:278-291`

### What is causing it

After:

```javascript
await apiAcceptJobOffer(jobId);
```

the page immediately calls:

```javascript
await apiTransitionJob(jobId, 'ON_THE_WAY');
```

### What this affects

A technician can accept a job while stationary and the workflow immediately reports transit.

### Root cause

**Acceptance and travel-start are conflated in the UI flow.**

### Permanent fix

Separate:

```text
OFFERED
→ ACCEPTED
→ Start Trip
→ ON_THE_WAY / EN_ROUTE
```

Acceptance should only secure assignment.

### Acceptance check

After accepting, backend state must be `accepted` until the technician explicitly starts the trip.

---

## 26. Expired-offer path can call redispatch synchronously inside acceptance request

**Severity:** P1

**Where:** `backend/workforce_api/views.py:3619-3627`

### What is causing it

If an offer is expired, the request marks it expired and immediately calls:

```python
run_automatic_dispatch(job_obj)
```

### What this affects

A technician's API request can be delayed by the full dispatch operation.

### Root cause

**User-action endpoint is doing workflow scheduling and dispatch execution inline.**

### Permanent fix

Mark offer expired, commit, then enqueue redispatch.

Return the correct conflict response immediately.

### Acceptance check

Expired acceptance should not execute a full candidate scan synchronously.

---

## 27. Reject/cancel paths also execute redispatch synchronously before the outer request is fully decoupled

**Severity:** P1

**Where:**
- `backend/workforce_api/views.py:3989-3990`
- `backend/workforce_api/views.py:4144-4147`
- `backend/workforce_api/views.py:4334`

### What is causing it

Rejection/cancellation directly invokes dispatch logic in the request path.

### What this affects

Slow redispatch increases response latency and creates ordering risk with downstream events/webhooks.

### Root cause

**Redispatch is treated as a direct command rather than an asynchronous consequence of a committed state change.**

### Permanent fix

Use:

```text
transaction.atomic()
→ state change
→ transaction.on_commit(enqueue_redispatch)
→ HTTP response
```

The worker performs the actual candidate selection.

### Acceptance check

Request completion should not depend on dispatch-engine runtime.

---

## 28. Company context is silently forced to company ID 1 inside dispatch

**Severity:** P0

**Where:** `backend/workforce_api/services/automatic_dispatch.py:827-830`

### What is causing it

If the job has no company, dispatch sets:

```python
job_obj.company_id = 1
```

### What this affects

A missing tenant/company assignment can be silently repaired to a default tenant.

This is a multi-tenant data integrity risk.

### Root cause

**Dispatch is compensating for an upstream ownership/data-integrity defect.**

### Permanent fix

Do not guess tenant ownership.

Instead:

```text
missing company → refuse automatic dispatch
→ durable error/event
→ admin escalation
```

Company assignment must be resolved at booking creation/integration boundary.

### Acceptance check

A company-less job must never silently become company 1.

---

## 29. Territory matching is string-based and can create weak/ambiguous geographic ranking

**Severity:** P2

**Where:** `backend/workforce_api/services/automatic_dispatch.py:602-604`

### What is causing it

Territory bonus is based on whether employee city text appears in the job address string.

### What this affects

India-specific address spelling, abbreviations, localities, and multilingual forms can produce false positives/negatives.

### Root cause

**Text search is being used as a geographic signal.**

### Permanent fix

Keep territory as a soft ranking signal only and prefer:

```text
pincode
city/administrative region IDs
service zones
coordinates
```

Never use string territory matching as a hard eligibility gate.

### Acceptance check

Different spellings of the same locality must not produce completely different eligibility outcomes.

---

## 30. GPS watcher fallback can create watcher lifecycle ambiguity

**Severity:** P1

**Where:** `frontend/src/hooks/useGPSPosition.js:130-162, 301-335`

### What is causing it

`WebGeolocationAdapter.watch()` can create a replacement watcher internally and stores its ID in:

```javascript
this._watchId
```

while the consuming hook keeps the returned watcher ID in:

```javascript
watchIdRef.current
```

### What this affects

The hook can potentially clear a different watcher ID from the one actually active after fallback.

This can lead to duplicate/orphaned GPS watchers.

### Root cause

**Two owners manage one native geolocation lifecycle.**

### Permanent fix

Make the adapter the sole owner of the native `watchPosition` lifecycle and return one stable handle, or make the hook own every native watcher explicitly.

Recommended:

```text
adapter.startWatch() → handle object
handle.stop() → clears current native watcher
```

### Acceptance check

Force high-accuracy failure, trigger fallback, unmount component, and verify zero native watchers remain.

---

## 31. GPS fallback can accept location up to 5 minutes old

**Severity:** P1

**Where:** `frontend/src/hooks/useGPSPosition.js:62-95`

### What is causing it

High-accuracy failure falls back to:

```javascript
maximumAge: 300000
```

which is 5 minutes.

### What this affects

For dispatch and live technician navigation, a stale position can materially misrepresent technician proximity.

### Root cause

**One freshness policy is reused for different purposes.**

### Permanent fix

Use purpose-specific freshness:

```text
manual location scan: may accept cached location
UI continuity: may accept cached location
DISPATCH: strict freshness
LIVE NAVIGATION: strict freshness
```

For dispatch, stale fallback should never make a technician newly eligible.

### Acceptance check

A >dispatch-threshold cached location cannot qualify a technician for a new offer.

---

## 32. Multiple frontend components can write technician location directly

**Severity:** P1

**Where:**
- `frontend/src/context/EmployeeRuntimeProvider.jsx:354-389`
- `frontend/src/context/EmployeeRuntimeProvider.jsx:405-430`
- `frontend/src/components/employee/ClockInCard.jsx`
- `frontend/src/components/common/TopHeader.jsx:88-95`
- `frontend/src/components/employee/JobTrackingMap.jsx:616-635`

### What is causing it

There is a central watcher, but several UI components also call `apiUpdateLocationFull()` directly.

### What this affects

Location telemetry can be produced through multiple paths, creating inconsistent timing, duplicate updates, or hidden coupling between UI and tracking.

### Root cause

**Centralized GPS design is only partially centralized.**

### Permanent fix

Make `EmployeeRuntimeProvider` the sole continuous telemetry producer.

Other components may request an explicit one-shot manual fix through a runtime API such as:

```text
requestFreshLocation()
```

They should not independently implement tracking logic.

### Acceptance check

Only one continuous watcher exists for an authenticated online employee.

---

## 33. Navigation route recalculation is triggered from every location event and can multiply listeners/work

**Severity:** P1

**Where:** `frontend/src/components/employee/navigation/useTechnicianNavigation.js:183-265`

### What is causing it

Every `workforce:location-updated` event evaluates route progression and can call `requestRoadRoute()`.

The time/movement throttle helps, but the effect depends on multiple values and registers a listener whenever those dependencies change.

### What this affects

During active navigation, repeated event-listener re-registration and route recalculation can create unnecessary routing work and race conditions.

### Root cause

**High-frequency telemetry is tightly coupled to navigation recalculation.**

### Permanent fix

Keep one stable event subscription.

Use refs for fast-changing values:

```text
location event
→ update refs
→ evaluate throttle
→ enqueue/recalculate route only when threshold met
```

Also ensure only one route request can be in flight per job/origin generation.

### Acceptance check

100 location updates must not produce 100 Google route requests.

---

## 34. Navigation uses a synthetic constant-speed ETA fallback

**Severity:** P2

**Where:** `frontend/src/components/employee/navigation/useTechnicianNavigation.js:311-327`

### What is causing it

When route duration is unavailable, ETA falls back to:

```javascript
(totalDistanceMeters / 1000) * 180
```

which assumes roughly 20 km/h.

### What this affects

Urban/outer-city Indian routing can produce highly inaccurate ETA when real route calculation fails.

### Root cause

**Fallback ETA is a distance-only heuristic rather than a routing result.**

### Permanent fix

Treat route ETA as unavailable when no route result exists, or use a documented provider-specific fallback with explicit degraded status.

Do not present a heuristic as precise ETA.

### Acceptance check

UI clearly distinguishes:

```text
ROUTE ETA
```
from:

```text
ESTIMATED / DEGRADED ETA
```

---

# Additional Cross-Cutting Observations

These are not counted as additional findings because they are already covered by the 34 items above.

## A. Latest Vite proxy is already corrected in the supplied snapshot

The current `frontend/vite.config.js` contains:

```text
frontend/vite.config.js:6
VITE_WORKFORCE_API_URL || http://127.0.0.1:8001
```

and the dev server is on port `5176`.

Therefore, the earlier `8000` mismatch is **not present in this latest uploaded snapshot**. Do not ask Antigravity to re-fix it unless an environment file overrides it incorrectly.

## B. Client realtime layer already has useful recovery mechanisms

`EmployeeRuntimeProvider` has single-flight refresh logic and preserves last known jobs on refresh errors (`frontend/src/context/EmployeeRuntimeProvider.jsx:159-243`). Keep these protections.

## C. The acceptance transaction already has good locking foundations

`WorkforceJobAcceptOfferView` uses transaction locking and checks conflicting active jobs (`backend/workforce_api/views.py:3570-3660`). Preserve this foundation while fixing lifecycle/event semantics.

## D. State machine already closes tracking sessions on terminal states

`backend/service_requests/state_machine.py:231-247` closes active tracking sessions and reconciles employee availability on completed/cancelled/redispatching/unable-to-complete. Preserve this centralized behavior.

---

# Recommended Fix Order

Do not let Antigravity fix these randomly. The order matters.

## Phase 1 — P0 Stabilization

Fix in this order:

1. Finding 1 — duplicate dispatch triggers.
2. Finding 2 — dispatch inside SSE.
3. Finding 3 — dispatch inside GPS.
4. Finding 4 — dispatch inside jobs GET.
5. Finding 7 — empty-service bypass.
6. Finding 8 — relational service/skill authority.
7. Finding 14 — dispatch inside `ServiceRequest.save()`.
8. Finding 28 — hardcoded company fallback.
9. Finding 19 — unified event publisher.

### Phase 1 target architecture

```text
Booking/state event
       ↓
transaction commit
       ↓
enqueue dispatch
       ↓
ONE dispatch worker
       ↓
service/skill verification
       ↓
workload verification
       ↓
location freshness
       ↓
ranking
       ↓
offer
```

Nothing else starts dispatch.

---

## Phase 2 — Realtime + Redis

Fix:

10. Finding 20 — SSE DB polling.
11. Finding 21 — replay/reconnect.
12. Finding 22 — stream lifecycle.
13. Finding 12 — Redis ACK semantics.
14. Finding 13 — dead-letter strategy.
15. Finding 17 — Redis GEO integration contract.
16. Finding 18 — unified freshness policy.

### Phase 2 target architecture

```text
Business event
    ↓
publish_workforce_event()
    ↓
PostgreSQL durable event
    ↓
Redis transport
    ↓
SSE
    ↓
EmployeeRuntimeProvider
```

Recovery:

```text
SSE reconnect
    ↓
REST reconciliation
    ↓
PostgreSQL authoritative state
```

---

## Phase 3 — Assignment + Workflow correctness

Fix:

17. Finding 5 — offer vs assigned webhook semantics.
18. Finding 10 — one-live-offer policy.
19. Finding 11 — real wave semantics.
20. Finding 16 — previous status audit bug.
21. Finding 25 — acceptance vs travel.
22. Finding 26 — expired-offer synchronous redispatch.
23. Finding 27 — rejection/cancellation synchronous redispatch.

---

## Phase 4 — Location + Map + UI consistency

Fix:

24. Finding 23 — stale jobs page.
25. Finding 24 — first-offer-only cockpit.
26. Finding 30 — GPS watcher ownership.
27. Finding 31 — location freshness policy.
28. Finding 32 — single telemetry producer.
29. Finding 33 — navigation route recalculation control.
30. Finding 34 — degraded ETA semantics.
31. Finding 9 — ranking semantics.
32. Finding 29 — territory matching.

---

# Final Target Architecture

```text
                         CUSTOMER BOOKING / WORKFLOW EVENT
                                      |
                                      v
                              PostgreSQL state
                                      |
                              transaction.on_commit
                                      |
                                      v
                              DISPATCH REQUEST
                                      |
                              one worker/queue
                                      |
                                      v
                              dispatch_job(job_id)
                                      |
                     +----------------+----------------+
                     |                |                |
                     v                v                v
                service/skill      workload       location freshness
                authorization      availability     + Redis GEO
                     |                |                |
                     +----------------+----------------+
                                      |
                                      v
                                  ranking
                                      |
                                      v
                               ONE live offer
                                      |
                       +--------------+--------------+
                       |                             |
                       v                             v
                    OFFERED                      PostgreSQL event
                       |                             |
                    ACCEPT                           v
                       |                           Redis
                       v                             |
                  ASSIGNMENT                         v
                       |                            SSE
                       v                             |
             accepted / on_the_way                Runtime
                       |                             |
                       v                       REST recovery
                    tracking
                       |
                       v
                 GPS telemetry
                       |
                 +-----+-----+
                 |           |
                 v           v
            PostgreSQL     Redis fast state
                 |
                 v
            location history
```

---

# Antigravity Master Execution Prompt

Copy/paste this prompt into Antigravity from the **root of the current Workforce codebase**.

```text
CALTRACK WORKFORCE — CORE PRODUCTION HARDENING
34-FINDING EXECUTABLE FIX PLAN

You are working against the current live Workforce codebase.
Do NOT use .backup_outer_pre_vendor_replace as the implementation source.
Do NOT redesign unrelated UI.
Do NOT create duplicate services when an existing authoritative service already exists.
Do NOT make cosmetic changes.

OBJECTIVE
=========
Fix the core Workforce execution architecture so job dispatch, job fetch,
offer/assignment, Redis, SSE, GPS/location, tracking, maps and technician UI
have one deterministic source of truth and one execution path.

CRITICAL RULES
==============
1. PostgreSQL is the durable business source of truth.
2. Redis is transport/cache/acceleration only.
3. SSE is server→browser realtime transport only.
4. REST is the recovery/reconciliation path.
5. GPS telemetry must never directly execute dispatch.
6. GET /jobs must never execute dispatch.
7. SSE must never execute dispatch.
8. Presence toggle must not directly execute dispatch.
9. ServiceRequest.save() must not own dispatch orchestration.
10. One dedicated dispatch execution path only.
11. One continuous GPS producer per authenticated online employee.
12. One realtime event publishing abstraction for realtime business events.
13. Missing tenant/company or service data must fail safely, not guess.
14. Customer price/invoice logic is out of scope; do not introduce hardcoded money.

============================================================
PHASE 1 — REMOVE DUPLICATE DISPATCH TRIGGERS
============================================================

Inspect and fix these exact current locations:

- backend/workforce_api/views.py
  - presence/online path around 2046-2050
  - employee jobs GET around 2127-2158
  - GPS update around 6167-6168
  - SSE stream around 7034-7035

Remove direct execution/thread creation for:
- reconsider_jobs_for_employee
- dispatch_job
- run_automatic_dispatch

from those request/stream paths.

Do NOT simply wrap each call in another daemon thread.
That is not a fix.

Create/use ONE authoritative dispatch command path:

business state change
→ transaction.on_commit()
→ enqueue dispatch request
→ existing Redis Stream/background worker
→ dispatch_job(job_id)

If Redis is unavailable, do not execute a full dispatch scan synchronously from
an HTTP request callback. Use a bounded durable fallback mechanism already
available in the project or implement the smallest DB-backed retry/outbox path.

Acceptance:
- no dispatch from GPS endpoint
- no dispatch from jobs GET
- no dispatch from SSE
- no dispatch from presence endpoint
- only dedicated worker/service runs dispatch

============================================================
PHASE 2 — MAKE SSE A DUMB EVENT PIPE
============================================================

Inspect:
- backend/workforce_api/views.py WorkforceRealtimeStreamView
- frontend/src/hooks/useRealtimeStream.js
- backend/workforce_api/services/realtime.py

Remove all expensive business work from SSE, especially:
- reconsider_jobs_for_employee
- candidate evaluation
- dispatch
- workload scans
- pricing calculation
- other large synchronous DB work

SSE should only:
- authenticate
- establish stream
- deliver realtime events
- send heartbeat
- cleanup on disconnect

Heartbeat must remain independent of dispatch.

Reduce/replace per-second PostgreSQL polling if the existing Redis realtime
transport can carry events. PostgreSQL EventLog remains replay/recovery state.

Implement reconnect/recovery safely:
- persist last received SSE event ID in the client runtime/ref
- send Last-Event-ID on reconnect
- always perform REST reconciliation after reconnect
- use bounded backoff already present in useRealtimeStream.js
- do not create reconnect storms

Do not expose JWTs in logs.

Acceptance:
- SSE idle for 2+ minutes without dispatch work
- heartbeat continues
- DISPATCH_STARTED/OFFER_CREATED/JOB_ASSIGNED/STATUS_CHANGE events arrive
- reconnect works
- runtime rehydrates from REST after reconnect

============================================================
PHASE 3 — UNIFY REALTIME EVENT PUBLISHING
============================================================

Inspect all direct:
WorkforceEventLog.objects.create(...)

calls across dispatch, offer, assignment, cancellation, notifications,
location and workflow code.

Classify events as:
- AUDIT ONLY
- REALTIME BUSINESS EVENT

All realtime business events must use:
    publish_workforce_event(...)

Do not duplicate event rows.
Do not break durable audit semantics.

Required events to verify:
- DISPATCH_STARTED
- CANDIDATES_EVALUATED
- OFFER_CREATED
- JOB_ASSIGNED / assignment event
- EMPLOYEE_JOB_ACCEPTED
- STATUS_CHANGE
- ARRIVAL_DETECTED
- JOB_COMPLETED
- PAYMENT_COLLECTED
- NOTIFICATION_CREATED
- JOB_LOCATION_UPDATE

Acceptance:
Every event has one documented publishing path.

============================================================
PHASE 4 — FIX DISPATCH AUTHORIZATION
============================================================

Inspect:
- canonical_service_match
- check_candidate_eligibility
- get_eligible_candidates
- WorkforceServiceSkillRequirement
- WorkforceEmployeeSkill

Change the business rule to:

Service
→ required skill(s)
→ verified employee skill(s)
→ eligible

String aliases may normalize labels but must NOT grant authorization.

Required safety changes:
- empty/missing service → fail closed
- do not use substring matching as authorization
- do not allow unrelated service aliases to match

Required proof test:
AC job + painter-only technician = NOT ELIGIBLE
Painting job + AC-only technician = NOT ELIGIBLE
Matching verified skill = ELIGIBLE

============================================================
PHASE 5 — FIX DISPATCH RANKING
============================================================

Inspect automatic_dispatch.py final ranking.
Current code sorts primarily by:
    distance_km
then:
    -score

Make ranking policy explicit.

Recommended:
1. hard eligibility gates
2. composite score
3. distance as deterministic tie-breaker

Do not leave business ranking hidden inside tuple sort.

Add tests for:
- closer but lower-score technician
- farther but higher-score technician
- exact skill vs broad skill
- stale GPS

============================================================
PHASE 6 — FIX OFFER CONCURRENCY + WAVES
============================================================

Decide and enforce:

ONE EMPLOYEE = ONE LIVE EXCLUSIVE OFFER

unless the existing business requirement explicitly says otherwise.

Use transaction-safe locking/constraints.

Also reconcile WorkforceJobOffer.wave_number with the real execution model.
If waves are intended, implement explicit progressive waves.
If not intended, deprecate/remove unused wave semantics.

Acceptance:
Two simultaneous jobs for the same employee cannot leave two exclusive
OFFERED rows if the business rule is one-offer-only.

============================================================
PHASE 7 — FIX OFFER / ASSIGNMENT SEMANTICS
============================================================

In automatic_dispatch.py:
Do NOT emit customer event "technician.assigned" merely because an offer was
created.

Use:
    technician.offer_sent

at offer creation.

Use:
    technician.assigned

only after atomic acceptance/assignment succeeds.

Verify the Customer integration contract before changing the event payload,
but do not preserve incorrect semantics merely for backward compatibility.

============================================================
PHASE 8 — FIX ACCEPTANCE STATE TRANSITIONS
============================================================

Inspect WorkforceJobAcceptOfferView.

Fix previous-status audit bug by capturing previous state BEFORE mutation:

previous_offer_status = offer.status

Then mutate the offer and write lifecycle audit from the captured value.

Acceptance must result in:
    OFFERED → ACCEPTED

It must NOT automatically mean:
    ACCEPTED → ON_THE_WAY

Frontend must separate:
    Accept Job
from:
    Start Trip

The current EmployeeJobsPage code around 278-291 directly calls:
    apiTransitionJob(jobId, 'ON_THE_WAY')

after acceptance.
Remove that automatic transition.

============================================================
PHASE 9 — MOVE REDISPATCH OUT OF USER REQUESTS
============================================================

Inspect these paths:
- expired offer acceptance
- employee cancellation
- employee rejection
- redispatching transitions

Do:

transaction.atomic()
→ update authoritative job/offer state
→ transaction.on_commit(enqueue redispatch)
→ return HTTP response

The dispatch worker performs the actual redispatch.

Do not call the full dispatch engine synchronously from these API handlers.

============================================================
PHASE 10 — REMOVE MODEL-LEVEL DISPATCH ORCHESTRATION
============================================================

Inspect:
backend/service_requests/models.py around 417-442

Remove automatic dispatch orchestration from ServiceRequest.save().

Model save must persist state only.

Move dispatch scheduling to explicit application/service layer code using:
transaction.on_commit()

No hidden dispatch side effect should remain in model.save().

============================================================
PHASE 11 — REMOVE TENANT GUESSING
============================================================

Inspect:
backend/workforce_api/services/automatic_dispatch.py around 827-830

Remove:
    job_obj.company_id = 1

If company/tenant is missing:
- do not guess
- return a durable dispatch failure reason
- keep job unassigned
- notify/admin-escalate through existing mechanism

Acceptance:
No job without company is silently assigned company 1.

============================================================
PHASE 12 — REDIS DISPATCH SEMANTICS
============================================================

Inspect:
backend/workforce_api/services/redis_dispatch.py

Fix message handling so these outcomes are distinct:

A. infrastructure failure
→ do not ACK
→ retry/recover

B. valid business result, including no eligible technician
→ persist outcome
→ ACK

C. malformed/poison message
→ bounded retries
→ dead-letter/admin-visible failure

Do not ACK merely because reconcile_fn returned without throwing.

Add retry attempt tracking or the smallest equivalent mechanism.

============================================================
PHASE 13 — REDIS GEO CONTRACT
============================================================

Inspect:
backend/workforce_api/services/redis_dispatch.py
backend/workforce_api/services/automatic_dispatch.py

Decide and document:

Redis GEO = candidate shortlist only
PostgreSQL = final eligibility authority

If Redis GEO is not actually used in the active path, do not claim it is.
Either wire it properly or keep PostgreSQL as the active path until deliberately
promoted.

Unify location freshness policy for dispatch.
Do not let Redis use 120 sec while final dispatch uses 300 sec without an
explicit reason/configuration.

============================================================
PHASE 14 — SINGLE GPS PRODUCER
============================================================

Inspect:
- EmployeeRuntimeProvider
- useGPSPosition
- ClockInCard
- TopHeader
- JobTrackingMap

Establish ONE continuous telemetry owner:
EmployeeRuntimeProvider / useLocationTracker

Other components may request:
requestFreshLocation()

but must not start their own tracking loops or silently write telemetry on their
own.

Fix WebGeolocationAdapter watcher ownership so fallback never creates an orphan
watcher.

Use purpose-specific location freshness:
- dispatch: strict
- live tracking: strict
- manual scan/UI continuity: can be more tolerant

Stale cached position must never make a technician newly dispatch-eligible.

============================================================
PHASE 15 — FIX ACTIVE JOB UI SOURCE OF TRUTH
============================================================

Inspect:
frontend/src/pages/employee/EmployeeJobsPage.jsx

Remove the duplicated long-lived jobs state:
    const [jobs, setJobs] = useState(cachedJobs)

Use runtime state as the source of truth for job data.
Keep only UI state locally:
- active tab
- selection
- search
- loading/error
- modal state

The rendered job list must react immediately when EmployeeRuntimeProvider
refreshes activeJobs.

Acceptance:
SSE event → runtime refresh → job appears without page reload.

============================================================
PHASE 16 — OFFER UI CONSISTENCY
============================================================

Inspect:
frontend/src/components/employee/dashboard/PortalCockpitLayout.jsx

Current code uses:
    incomingOffers[0]

Make this consistent with the backend concurrency policy.

If backend guarantees one live offer, document and test that invariant.
If multiple offers are intentionally supported, render them rather than hiding
all but the first.

============================================================
PHASE 17 — NAVIGATION ROUTE REQUEST CONTROL
============================================================

Inspect:
frontend/src/components/employee/navigation/useTechnicianNavigation.js

Keep one stable location listener.
Use refs for high-frequency mutable state.

Ensure:
- at most one route request is in flight per route generation
- time/movement throttle is applied
- stale route results cannot overwrite newer routes
- location event count does not equal route request count

Target:
100 GPS updates != 100 Google route requests.

If no provider route is available, display degraded ETA explicitly instead of
pretending a constant-speed estimate is exact.

============================================================
PHASE 18 — TEST THE CORE BUSINESS INVARIANTS
============================================================

Create or extend tests for exactly these scenarios:

1. New booking dispatches once.
2. Opening Jobs page does not dispatch.
3. GPS update does not dispatch.
4. SSE connection does not dispatch.
5. Presence toggle does not duplicate dispatch.
6. AC job never reaches painter-only technician.
7. Missing service cannot auto-dispatch.
8. Missing company cannot become company 1.
9. Two workers cannot create two winning offers for one job.
10. One employee cannot hold multiple exclusive offers if one-offer policy is active.
11. Expired offer redispatch is asynchronous.
12. Reject redispatch is asynchronous.
13. Cancel redispatch is asynchronous.
14. Acceptance previous_status is OFFERED.
15. Acceptance state is ACCEPTED, not ON_THE_WAY.
16. OFFER_CREATED does not emit technician.assigned.
17. Accepted assignment emits technician.assigned once.
18. SSE idle >2 minutes remains stable.
19. SSE heartbeat remains independent of dispatch.
20. SSE reconnect recovers missed business state.
21. Redis infrastructure failure does not create duplicate offers.
22. Poison Redis message does not retry forever.
23. GPS fallback watcher cleans up correctly.
24. Stale GPS cannot qualify for dispatch.
25. New job appears in EmployeeJobsPage without reload after runtime refresh.
26. Navigation route requests are throttled.
27. Active tracking closes on terminal state.
28. Employee availability is reconciled once after terminal state.

============================================================
IMPLEMENTATION RULES
============================================================

- Reuse existing models/services where appropriate.
- Do not create a second dispatch engine.
- Do not create a second GPS tracker.
- Do not create a second event log.
- Do not create a second job store in the frontend.
- Do not use daemon threads per request/SSE/GPS update.
- Do not hide exceptions with broad silent catches where the failure matters.
- Do not hardcode prices, invoice amounts, customer payment amounts, or tenant IDs.
- Do not change Customer UI; only preserve/verify the integration contract.
- Do not break the state machine unless required by the invariant above.
- Do not report success merely because compilation passes.

============================================================
REQUIRED FINAL OUTPUT
============================================================

Return only:

1. FINDINGS FIXED
   Numbered 1-34 with PASS/PARTIAL/NOT FIXED.

2. FILES CHANGED
   Exact paths.

3. CORE FLOW BEFORE/AFTER
   One short diagram.

4. TESTS RUN
   Exact test names/commands and pass/fail.

5. REMAINING BLOCKERS
   Only real blockers.

6. PRODUCTION VERDICT
   READY / NOT READY

Do not claim "production ready" if any P0 finding remains.
```

---

# Suggested Antigravity Execution Strategy

Do **not** paste the entire codebase into one context window. The prompt above is designed so Antigravity can work from the repository directly.

Recommended execution order:

```text
Prompt pass 1:
P0 dispatch + SSE + model-save orchestration

Prompt pass 2:
Redis + event publisher + replay/reconnect

Prompt pass 3:
assignment + state-machine + offer lifecycle

Prompt pass 4:
GPS + tracking + navigation + UI synchronization

Prompt pass 5:
full invariant test run + production verdict
```

The same master prompt can be used in one run, but the four-pass approach is safer when the repository is large and Antigravity context is limited.

---

# Key Files Antigravity Must Inspect First

```text
backend/workforce_api/services/automatic_dispatch.py
backend/workforce_api/services/redis_dispatch.py
backend/workforce_api/services/realtime.py
backend/workforce_api/services/workload.py
backend/workforce_api/views.py
backend/workforce_api/models.py
backend/service_requests/models.py
backend/service_requests/state_machine.py

frontend/src/context/EmployeeRuntimeProvider.jsx
frontend/src/hooks/useRealtimeStream.js
frontend/src/hooks/useGPSPosition.js
frontend/src/pages/employee/EmployeeJobsPage.jsx
frontend/src/components/employee/dashboard/PortalCockpitLayout.jsx
frontend/src/components/employee/JobTrackingMap.jsx
frontend/src/components/employee/navigation/useTechnicianNavigation.js
frontend/src/components/employee/ClockInCard.jsx
frontend/src/components/common/TopHeader.jsx
frontend/vite.config.js
```

---

# Final Recommendation

The most important correction is to stop treating realtime transport, GPS telemetry, frontend reads, and presence changes as dispatch triggers.

The production-safe contract should be:

```text
WRITE / BUSINESS EVENT
        ↓
PostgreSQL transaction
        ↓
on_commit
        ↓
ONE DISPATCH WORKER
        ↓
ONE OFFER / ASSIGNMENT PATH
        ↓
ONE EVENT PUBLISHER
        ↓
Redis transport
        ↓
SSE
        ↓
EmployeeRuntimeProvider
        ↓
REST reconciliation when necessary
```

And for location:

```text
ONE GPS WATCHER
      ↓
location API
      ↓
PostgreSQL latest state
      ↓
Redis fast state (optional/accelerator)
      ↓
tracking + map
```

**No page GET, GPS packet, or SSE heartbeat should ever start the dispatch engine.**

