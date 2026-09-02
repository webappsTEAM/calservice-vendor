# Booking Intake → Vendor Fulfillment: Queue & Dispatch Framework

**Prepared for:** Caldim Engineering — SEVO Workforce Platform
**Date:** September 2, 2026
**Status:** Framework for engineering design; builds on existing dispatch engine

---

## 0. What already exists, and what this framework adds

Before laying out the framework, it's worth being precise about what's already built versus what's being designed here, because a good chunk of this is already running in the vendor app.

There is already a real automatic-dispatch engine (`services/automatic_dispatch.py`) that does most of the hard part: it finds eligible technicians near a booking, ranks them, and makes a single, exclusive, time-boxed offer to the best candidate — falling back to the next candidate if that offer is declined or times out. That's the mechanism that turns "a booking came in" into "a specific technician got asked." What it does *not* yet do is vary how long that offer window stays open based on anything — it's a single fixed five-minute window for every booking everywhere, regardless of how urgent the job is, how many technicians are actually nearby, or what kind of service it is. That's the specific gap this framework is designed to close, alongside laying out the full chain end to end so a team building or reviewing this has the whole picture in one place, not just the parts that already work.

Everything below is organized as a progression through the booking's life, and at each stage says what already happens today, what's being proposed, and why it matters.

---

## 1. Booking intake and transmission to the vendor application

**What happens.** A customer submits a booking in the customer-facing app: service category, issue description, address with GPS coordinates, preferred date/time, and payment method. That booking is written into a `ServiceRequest` record — the same table structure is shared between the customer app and the vendor (workforce) app, so there's no separate "transmit to vendor" API call to design; the record itself is the shared source of truth both sides read and write. The moment that record is saved in a dispatchable state (draft, new request, or confirmed), it automatically triggers the dispatch engine — this happens synchronously off the model's own save method, so there's no polling delay between "customer submitted" and "the system starts looking for a technician."

**Why this matters.** Sharing one table instead of an API handoff between two separate systems eliminates an entire class of "the vendor app never received the booking" failure mode — there's nothing to fail to deliver, because there's only one record. The trade-off is that both sides have to stay in careful agreement about what each field means and who's allowed to write to it, which is why the existing model carries detailed comments about exactly which fields mirror the customer app's version field-for-field.

**Data required at this stage:** customer identity, service category/issue title, precise GPS coordinates (dispatch cannot proceed without these — a booking with no coordinates is explicitly rejected from dispatch and flagged, not silently dropped), address text, preferred timing, payment method, and which vendor/company tenant this booking belongs to (bookings are tenant-scoped — dispatch only considers technicians within the same company as the booking).

**Data quality gate.** If GPS coordinates are missing, the booking is marked `unassigned` immediately rather than attempted — this is a deliberate fail-fast: attempting to rank technicians by distance from an unknown point would produce meaningless results, so the system surfaces the problem (a booking stuck with no location) rather than silently guessing.

---

## 2. Candidate assembly: who's even eligible

Before anything about location or timing, a booking needs a pool of technicians who are structurally allowed to do the work at all. This existing step (a nine-gate eligibility check) filters candidates down before ranking ever begins:

- Active account, online, and currently set to "available" (not offline, not on-break, not already marked busy)
- Belongs to the same company/tenant as the booking
- Has no other active job in progress right now (one technician, one job, at a time — this is checked twice: once cheaply during ranking, and again as a final concurrency check right before the offer is actually created, closing the small window where two bookings could race for the same technician)
- Approved for the specific service being requested, matched against their verified skills and approved service list
- Mandatory compliance documents (licenses, background checks, insurance, etc.) are current, not expired or rejected
- Vehicle documents (insurance, permits) current if the role requires a vehicle
- Hasn't already been offered, and hasn't already declined, this specific booking

**Why gate before rank, not the other way around.** Ranking is only meaningful among people who could actually legally and practically do the job — running distance/skill scoring across every technician in the company regardless of eligibility would waste effort ranking people who'd just get rejected anyway, and worse, could produce a top-ranked candidate who then fails a hard eligibility check, adding a wasted round trip. Filtering first keeps every candidate that reaches the ranking step genuinely offer-able.

---

## 3. Ranking: who gets asked first

Every technician who clears the eligibility gate gets scored, and the booking goes to whoever ranks highest — this is where location and availability actually enter the picture as a *ranking* signal (as opposed to the timing rules in section 4, which are a separate thing).

**Location.** A technician's live GPS position (from their last reported location, which must be fresh — older than two minutes and it's treated as stale and excluded, since a two-hour-old location is worse than no location) is compared against the booking's coordinates. Anyone farther than 50 km is excluded outright; within that radius, closer distance directly increases score, so the dispatch engine's first instinct is always "who's nearest," not merely "who's technically reachable."

**Availability and reliability, beyond the online/available flag.** A technician who's clocked in for their shift right now scores higher than one who's merely marked available but hasn't clocked in — a small but meaningful signal that they're actually at their post. A technician's recent history of accepting versus declining or ignoring offers (over a rolling 30-day window, and only once they have enough of a track record for it to be meaningful — a technician's first offer or two is never penalized for a fluke) nudges their score down if they've been unreliable, so the system naturally prefers technicians who tend to actually take the jobs they're offered.

**Skill and territory fit.** A verified skill that matches the requested service adds to the score, weighted by how proficient the technician is rated at it. A technician whose home city matches the booking's address also gets a bonus — a proxy for local familiarity beyond raw GPS distance.

**Ordering rule.** Distance is the primary sort key — nearest technician wins, full stop — and score is only the tiebreaker among technicians who are roughly equally close. This is a deliberate choice: customers waiting for a technician generally care more about "how long until someone shows up" than about small differences in scorecard rating, so proximity leads.

---

## 4. Queue lifetime rules: how long an offer sits with one technician

This is the section that needs the most new design work, since today's system uses one fixed number everywhere. Here's the recommended approach, and why each variation matters.

**The base mechanism (already built, keep as-is).** Rather than a static, precomputed queue of technicians sitting and waiting their turn, the system computes the ranked candidate list fresh every time it needs to make an offer, and only ever holds *one* active, exclusive offer open per booking at a time. When that offer is declined, ignored, or times out, the *next* offer is a fresh re-ranking, not just "move to position two on a list computed five minutes ago." This matters because technician availability changes constantly — someone could go offline, get busy, or change location in those five minutes — so re-ranking at the moment of each new offer, rather than trusting a stale precomputed order, keeps every offer going to whoever is genuinely best-positioned right now, not whoever looked best minutes ago.

**Why the offer window should vary — the design gap.** A single fixed window, no matter what value you pick, is wrong for someone. A five-minute window is generous when there are twenty eligible technicians nearby and painfully slow for an urgent leak when there's exactly one technician in range who might be mid-job and needs a moment to check. The right window depends on three things, and all three are already sitting in data the system has at dispatch time — they just aren't being used for this purpose yet.

| Factor | How it should shift the window | Why |
|---|---|---|
| **Booking priority/urgency** (already a field on every booking — Low/Normal/High/Urgent, currently unused for timing) | Urgent bookings get the shortest window (e.g., 2 minutes); Low-priority bookings can afford the longest (e.g., 10 minutes) | An urgent booking sitting idle while one technician thinks it over for five minutes is exactly the failure mode this should prevent — urgency should visibly buy speed |
| **Candidate pool depth** (how many eligible technicians exist for this booking right now — the ranking step already computes this as a side effect) | A thin pool (1-2 eligible candidates) gets a longer window, since burning the one good option on a timeout is expensive; a deep pool (10+) gets a shorter window, since there's always a strong next option a moment away | This directly optimizes for total time-to-assignment, not just per-offer politeness — with plenty of backup, moving fast costs little; with few options, moving fast can cost a lot if the timeout forces a much worse fallback |
| **Service type / location density** (a rural or lower-density service area, or a service category with historically few qualified technicians) | Sparse areas/service types get a longer window by default, since the realistic alternative to "wait a bit longer for this technician" may be "no other technician exists within range at all" | This should be a per-service-category and/or per-zone configuration value, not hardcoded, since which categories are "thin" will change over time and differs by city |

**Recommended shape, concretely:** a small lookup table (priority × pool-depth-bucket × service-category-or-zone) that resolves to an offer duration, with sane defaults so a new service category or zone that hasn't been explicitly configured still gets a reasonable value rather than failing. This keeps the tuning knobs in configuration/data, not in code, since these numbers will need real-world adjustment as operational patterns emerge — exactly the same "configurable, not hardcoded" principle this platform already applies elsewhere (service criteria, compliance requirements).

**What "escalation" should mean when the window runs out.** Today, when an offer expires, the system automatically re-ranks and re-offers to the next candidate — that part's solid and should stay. What's worth adding on top:
1. **Progressive radius widening** after a small number of consecutive expiries with no acceptance (e.g., after 2 failed offer cycles, widen the search radius by a defined step, rather than staying capped at the same fixed radius indefinitely) — this trades a longer commute for a real technician over continuing to fail against an empty pool.
2. **Admin escalation** (already built) fires once the candidate pool is genuinely exhausted, marking the booking `unassigned` and notifying a company admin — this should additionally include *why* it's unassigned (no candidates in range vs. every candidate declined) so an admin knows whether to widen criteria manually or intervene directly.
3. **Customer-facing signal** — once a booking has been through more than one or two full offer cycles without acceptance, the customer app should receive an update reflecting the delay honestly (still "matching you with a technician," but the ETA expectation should soften) rather than looking identical to a booking that matched instantly.

---

## 5. The handoff chain: from confirmation to active service

Putting the whole thing together as one continuous chain, with the state each stage leaves the booking in:

1. **Customer confirms booking** → `ServiceRequest` created in a dispatchable status (draft/new/confirmed).
2. **Automatic dispatch triggers** (same transaction as booking creation) → eligibility gate + ranking run → booking moves to `unassigned` while a candidate is sought (this is a deliberate intermediate state: the booking is not yet tied to any technician, so nothing downstream mistakes "an offer went out" for "someone's coming").
3. **Exclusive offer created** for the top-ranked eligible technician, with an expiry timestamp set per the rules in section 4 → technician receives a push notification.
4. **Customer is told a technician is being matched** (deliberately without technician details yet — the customer app is only told "someone was asked," not who, until there's an actual acceptance, so a declined offer never has to be walked back in front of the customer).
5. **Technician responds, or the window lapses:**
   - **Accepts** → offer status becomes `ACCEPTED`, booking moves to `assigned`, technician identity/contact now flows to the customer app, and every other pending offer for this booking (there shouldn't be any, since offers are exclusive, but this is the safety net) is marked superseded.
   - **Declines** → offer marked `REJECTED`/`DECLINED`, that technician is excluded from consideration for this booking going forward, and step 3 repeats immediately against a freshly ranked pool.
   - **Window expires with no response** → offer marked `EXPIRED`, same re-ranking-and-reoffer loop as a decline, and this technician's declined/expired history quietly feeds their reliability score for future rankings (section 3).
6. **Technician actively working the job** → the existing job lifecycle takes over from here (en route → arrived → in progress → completion), which is already a mature, separately built part of the system and out of scope for this framework.
7. **No eligible technician found at all** → booking marked `unassigned`, admin notified with a reason, held for manual intervention or automatic re-attempt once conditions change (e.g., a new technician comes online or clocks in nearby — the existing system already re-evaluates pending bookings reactively whenever a technician's location updates, which naturally catches this case without needing a dedicated retry timer).

---

## 6. Touchpoints and data at each stage

| Stage | System touchpoint | Key data read | Key data written |
|---|---|---|---|
| Intake | Customer app → shared `ServiceRequest` table | service category, GPS, address, timing, payment method, tenant/company | new `ServiceRequest` row, dispatchable status |
| Candidate assembly | Dispatch engine, eligibility gates | technician status/availability, company match, skills, compliance docs, active-job check | (read-only at this stage) |
| Ranking | Dispatch engine, scoring | live GPS + freshness, distance, skill proficiency, clock-in state, 30-day offer history, scorecard rating/SLA | ranked candidate list (in-memory, not persisted) |
| Offer | Dispatch engine, notification service | booking priority, candidate pool depth, service/zone timing config | new `WorkforceJobOffer` row, expiry timestamp, technician notification |
| Response | Technician app, offer endpoint | technician's accept/decline action | offer status, booking status, (on accept) `assigned_employee` on the booking |
| Expiry sweep | Background dispatch worker | offers past their expiry timestamp | offer status → `EXPIRED`, triggers re-offer |
| Escalation | Dispatch engine, admin notification | consecutive-failure count, exhausted candidate pool | booking status → `unassigned`, admin notification with reason |
| Handoff to service | Existing job lifecycle (unchanged by this framework) | accepted offer, technician identity | booking status progression through to completion |

---

## 7. Edge cases worth designing for explicitly

- **Two bookings competing for the same technician at once.** The final busy-check right before an offer is created (section 2) closes most of this, but under real concurrency a company should still expect an occasional race; the fix is the existing row-level lock during offer creation, not a new mechanism — worth confirming this lock is held for the full "check busy, then create offer" sequence, not just part of it.
- **A technician's GPS goes stale mid-consideration.** If a technician's location hasn't updated recently enough by the time an offer would be created, they should be excluded from that specific ranking pass rather than offered a job based on a location that might be wrong by then — this is already the rule, just worth stating as intentional rather than incidental.
- **A technician accepts right as their offer would have expired.** The response and the expiry sweep can race; whichever transaction commits first should win, and the loser should fail cleanly (an already-expired offer can't be accepted; an already-accepted offer's expiry sweep should no-op) rather than both partially succeeding.
- **Every eligible technician has already declined this specific booking.** Once a booking exhausts its entire eligible pool without any radius widening, it should escalate to admin rather than looping forever re-ranking the same empty set — worth an explicit "no remaining candidates, including after widening" terminal state distinct from "genuinely nobody nearby at all."
- **A booking's priority changes after dispatch has already started** (e.g., a customer escalates urgency, or an admin manually flags it). The in-flight offer's expiry shouldn't retroactively change, but the *next* offer cycle should pick up the new priority's timing rules.
- **Very low technician density areas where even a widened radius returns nobody.** This isn't a dispatch-logic problem to solve by making the radius unbounded — a customer 80 km from the nearest technician should get an honest "not currently serviceable here" signal rather than an offer to someone who'll take an hour to arrive; this argues for a hard outer radius ceiling even after widening, with the `unassigned` + admin-notified path as the deliberate outcome, not a failure to fix.

---

## 8. Why this framework is structured this way

The throughline across every recommendation here is the same one already implicit in the existing dispatch engine's design: prefer configuration over hardcoding (timing rules as data, not constants), prefer re-evaluating fresh information over trusting stale precomputed state (re-ranking every offer cycle rather than working down a fixed list), and make every "nobody's available" outcome a visible, reasoned state rather than a silent dead end. The variable queue-lifetime rules in section 4 are the one genuinely new piece of business logic this framework adds; everything else is either already built and described here for completeness, or a small, targeted extension (progressive radius widening, richer escalation reasons, honest customer-facing delay signaling) layered onto a dispatch engine that's already doing the hard part correctly.
