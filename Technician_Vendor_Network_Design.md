# Technician–Vendor Network — Product & Technical Design

**Prepared for:** Caldim Engineering — SEVO Workforce Platform
**Date:** September 1, 2026
**Status:** Proposed design, not yet built

---

## 0. The one decision that matters most

Before anything else, there's a real conflict to name between what you're asking for and how the current codebase is built, because getting this wrong would mean rebuilding the whole thing later.

Today, an `Employee` record belongs to exactly one `Company`, via a required foreign key. That single relationship is used everywhere — which admin can see this technician's documents, which tenant's jobs they can be assigned, which company's payroll rules apply to them, and so on. It's a classic single-tenant-per-worker model, and it's baked into dozens of places in the existing code.

What you're describing is fundamentally different: a technician's identity has to be independent of any vendor, and their relationships with vendors have to be many-to-many, each with its own independent lifecycle. That cannot be represented by "which company does this Employee belong to" — it needs its own table.

So the core design decision is this: **the technician's account (their login, their profile, their single identity, their own wallet) stays exactly what it is today — one `Employee` row, homed under one "primary" company record for administrative purposes (which, for an independent technician, is the existing shared default company your platform already uses). Vendor relationships are layered on top as a completely separate many-to-many table.** That table — not `Employee.company` — is what actually governs which vendors a technician works with, what each vendor requires of them, and what state each of those relationships is in. `Employee.company` stops being "who owns this technician" and becomes "where this technician's platform-level account lives," which is a much smaller and less loaded piece of information.

This is the piece that makes everything else in this document work, and it's additive — nothing about how jobs, wallets, or documents already work has to be torn out. It just stops treating one particular foreign key as the source of truth for something it was never really designed to represent.

---

## 1. Complete business workflow

At the highest level, three things happen, and they happen independently of each other:

A vendor decides what kind of technicians they want, either by describing criteria and letting the platform suggest matches, or by naming someone they already know. Either way, this produces an **invitation** — a proposal, not a commitment. The technician, whenever they get around to it, looks at the invitation and decides yes or no. Only a "yes" produces a **relationship** — an ongoing, named connection between that one technician and that one vendor, which then has its own status that can change over time (paused, ended, etc.) independent of the technician's other relationships or their independent work.

Nothing in this chain ever removes the technician's ability to keep working for themselves, or to be in this same process with other vendors at the same time. Every invitation and every relationship is scoped to exactly one vendor-technician pair.

## 2. User journeys

**Technician journey (new to the platform, invited by email):**
1. Ravi gets an email: "ABC Home Services wants to add you to their technician network."
2. He doesn't have an account yet, so the email links him to a signup page that already knows his email and which vendor invited him.
3. He completes the normal technician signup (personal details, skills, documents) — this is exactly today's individual-technician onboarding, unchanged.
4. Once his profile is live, his one pending invitation from ABC is sitting in his dashboard.
5. He reviews it, hits Accept. A relationship now exists between him and ABC, status ACTIVE.
6. He keeps working independently and can be invited by, and accept, other vendors at any time — nothing about accepting ABC constrains him.

**Technician journey (existing user, discovered via matching):**
1. Ravi already has an account with AC Repair and AC Installation listed as approved skills.
2. CoolCare Services runs a "find technicians" search for AC Repair OR AC Installation technicians in Bengaluru, and Ravi shows up in the results.
3. CoolCare sends him an invitation with a note about what they're offering.
4. It appears in Ravi's "New Invitations" list in-app (no email needed since he already has an account, though a notification still goes out).
5. Ravi can view CoolCare's profile, requirements, and any offered terms before deciding. He accepts, rejects, or leaves it pending.

**Vendor journey:**
1. ABC Home Services wants to grow its AC repair coverage in Bengaluru.
2. They define criteria: skill = AC Repair OR AC Installation, location = Bengaluru, minimum experience = 2 years.
3. They run "Find Technicians" and get a ranked list of matches with enough information to judge fit (skills, experience, rating, location).
4. They invite a handful directly from the results, and separately invite one technician they already know by typing in his email.
5. Over the following days they watch their "Technician Network" screen: some invitations get accepted (moving to ACTIVE), some are rejected, some sit pending, and they can nudge or cancel a stale one.
6. Later, if a relationship isn't working out, they can suspend or terminate it without it affecting the technician's account as a whole or any of their other vendor relationships.

## 3. Technician-side screens

- **My Vendor Network** — every vendor the technician has an ACTIVE, SUSPENDED, or recently ended relationship with, each showing status and the skills/scope that relationship covers.
- **New Invitations** — invitations in INVITED or PENDING state, each showing who's asking, why, what they require, and what's being offered, with clear Accept/Reject actions.
- **Available Opportunities** (optional, later phase) — open vendor postings a technician could proactively express interest in, rather than only being invited.
- **Vendor relationship detail** — one vendor's full picture: scope of work, terms, history, an option to leave.
- **My Profile / Skills** — the technician's own skills, certifications, experience, location, availability — the same attributes vendor criteria get matched against, so what a technician fills in here is exactly what makes them discoverable.

## 4. Vendor-side screens

- **Technician Network** — every technician with any relationship to this vendor, filterable by status, searchable by name/skill.
- **Find Technicians** — the criteria builder plus matching results.
- **Invite Technician** — the direct-by-email flow, with an optional personal message.
- **Pending Invitations** — invitations this vendor has sent that haven't been answered yet, with the ability to cancel or resend.
- **Requirements/Criteria management** — saved criteria sets a vendor reuses when searching (e.g., "AC Team" = AC Repair OR AC Installation, Bengaluru, 2+ years).
- **Relationship detail** — one technician's history with this vendor: when invited, when accepted, jobs done together, current status, actions to suspend/terminate.

## 5. Invitation workflow

An invitation is created one of two ways — a vendor selects a technician from search results, or a vendor types in an email directly — and both converge on the same object. If the email belongs to an existing technician, the invitation is immediately visible in their dashboard and a notification is sent. If it doesn't, an email invite is sent instead, carrying a signed link that pre-fills the invitation context into the signup flow; the invitation stays dormant (not yet delivered in-app) until that person actually creates an account with that exact email, at which point it becomes visible to them like any other. Either way, an invitation records who sent it, who (or which email) it's for, what criteria/requirements prompted it if any, an optional message, and an expiry — invitations shouldn't sit open forever.

## 6. Accept / Reject workflow

The technician sees the invitation with the vendor's identity, why they were approached (which criteria matched, or "direct invite"), what's being asked of them, and what accepting means in plain terms. Accept converts the invitation into an ACTIVE relationship and closes the invitation as ACCEPTED — the invitation record isn't deleted, it's kept as history. Reject closes the invitation as REJECTED and creates no relationship. Both are one technician acting on one invitation; nothing about it touches any of their other invitations or relationships. A technician can also simply leave an invitation untouched, in which case it eventually expires on its own.

## 7. Vendor discovery / matching workflow

A vendor builds a criteria set from configurable, extensible attributes (see section 9) rather than fixed dropdowns for "AC repair" and nothing else. Each criterion is scoped as required-match-all (AND) or match-any-one-of-a-set (OR) — e.g., "(AC Repair OR AC Installation) AND location = Bengaluru AND experience >= 2 years." Running the search evaluates every candidate technician's profile against that expression and returns ranked matches with enough summary information for a vendor to judge fit before inviting. Saved criteria sets let a vendor re-run the same search later without rebuilding it, and can optionally auto-surface new matching technicians as they onboard (a later enhancement, not needed for v1).

## 8. Entity / data model

Reusing what already exists in your codebase (`User`, `Employee`, `Company`) and adding what's new:

```
User (existing)               — login identity
  └── Employee (existing)     — technician profile: skills, docs, KYC, wallet link
         │
         │  (existing FK, redefined as "home/primary account context",
         │   NOT "who this technician works for")
         ▼
      Company (existing)      — for an independent technician, the shared
                                 default company already used today

Company (existing, reused as "Vendor" in this module)
  — a vendor is simply a Company that participates in the network;
    no new table needed for "vendor" itself

VendorTechnicianRelationship (NEW)      — the durable, many-to-many join
  - id
  - vendor_id            → Company
  - technician_id        → Employee
  - status                (see §11)
  - source_invitation_id → VendorInvitation (nullable; how this started)
  - scope_skills          (which skills/services this relationship covers —
                            a technician can have a broader personal skill
                            set than what any one vendor relationship covers)
  - engagement_type       (per-job / part-time / full-time / on-call — free-text
                            enum, extensible)
  - payment_model         (DIRECT_TO_TECHNICIAN / THROUGH_VENDOR — ties into
                            existing wallet routing, see §21)
  - started_at, ended_at
  - created_by, updated_at
  - UNIQUE (vendor_id, technician_id)   — one relationship row per pair,
                                           its own status carries the history

VendorInvitation (NEW)                   — the temporary, request-scoped object
  - id
  - vendor_id             → Company
  - technician_id         → Employee, nullable   (null until the invited
                                                    email resolves to an account)
  - invited_email          (always stored, even once technician_id is known —
                             this is what prevents duplicate technician creation,
                             see §15)
  - status                 (see §11)
  - channel                 (DIRECT_EMAIL / MATCHING_RESULT)
  - matched_criteria_id    → VendorCriteria, nullable (which search produced this,
                                                          if any)
  - message                 (optional personal note from the vendor)
  - expires_at
  - responded_at
  - created_at

VendorCriteria (NEW)                     — a saved, reusable search/requirement set
  - id
  - vendor_id             → Company
  - name                   ("AC Team", "Deep Cleaning Crew", ...)
  - expression              structured AND/OR tree over criteria terms (see below)
  - is_active
  - created_at, updated_at

CriteriaTerm (NEW, extensible attribute matching — avoid hardcoding)
  - id
  - criteria_id           → VendorCriteria
  - attribute_type          (SKILL / SERVICE_CATEGORY / LOCATION / EXPERIENCE_YEARS /
                              AVAILABILITY / EMPLOYMENT_TYPE / CERTIFICATION /
                              MIN_RATING / ... — an enum you can keep extending)
  - operator                (EQUALS / IN / GTE / LTE / CONTAINS, per attribute_type)
  - value                    (JSON — flexible per attribute_type)
  - group_id                 (terms sharing a group_id are OR'd together;
                               groups themselves are AND'd — a simple, standard
                               way to express your AND/OR example without a
                               bespoke query language)

TechnicianSkill (NEW, or promote the existing `service_roles` JSON field
  into a real table — recommended once vendor matching depends on it)
  - id
  - technician_id         → Employee
  - skill_id              → Skill (a real catalog table, not free text)
  - approval_status         (pending / approved / rejected — this already
                              exists conceptually in today's onboarding draft,
                              just needs to move into a queryable table)
  - years_experience
  - certified, certification_ref

Skill (NEW, or reuse whatever catalog backs today's onboarding "services" step)
  - id, name, category, is_active
```

## 9. Database relationship design

```
        Employee (Technician)
              │
              │  1 ──── * 
              ▼
  VendorTechnicianRelationship  ──── * ──── 1   Company (Vendor)
              ▲
              │ 0..1 (how it started)
              │
        VendorInvitation ──── * ──── 1   Company (Vendor)
              │
              │ 0..1 (which search produced it)
              ▼
        VendorCriteria ──── * ──── CriteriaTerm
```

The two relationships that matter most: `Employee ↔ Company` through `VendorTechnicianRelationship` is many-to-many with a unique constraint per pair, and `VendorInvitation` references the technician by email first and by `Employee` only once resolved — those two facts together are what makes "one technician, many vendors, no duplicates" actually hold at the database level rather than just in application logic.

## 10. Invitation vs. relationship — why they're two tables, not one

An invitation is disposable: it can be sent, expire, get rejected, get re-sent, and none of that should ever overwrite or complicate the record of an actual working relationship. A relationship is durable: once ACTIVE, it has its own history — suspensions, resumptions, the jobs done under it, eventual termination — that has nothing to do with how it originally started. Collapsing them into one table would mean either losing the history of rejected/expired invitations (bad for audit and for "has this vendor tried to reach this technician before"), or polluting the relationship table with rows that never became real relationships. Keeping `source_invitation_id` as a link, rather than merging the tables, gets you full traceability — "this active relationship started from invitation #4821, sent via direct email on this date" — without conflating the two lifecycles.

## 11. Status / lifecycle definitions

**VendorInvitation.status**
| Status | Meaning |
|---|---|
| `PENDING` | Sent, awaiting the technician's response (covers your "INVITED" as well — for an invitation there's no meaningful difference between "sent" and "pending response," so this design collapses those two into one state to keep the lifecycle honest about what's actually distinguishable) |
| `ACCEPTED` | Technician said yes — triggers relationship creation |
| `REJECTED` | Technician said no |
| `EXPIRED` | Not responded to within the invitation's window |
| `CANCELLED` | Vendor withdrew it before a response |

**VendorTechnicianRelationship.status**
| Status | Meaning |
|---|---|
| `ACTIVE` | Live, working relationship |
| `SUSPENDED` | Temporarily paused by either party — technician stays associated but isn't currently offered this vendor's jobs |
| `TERMINATED` | Ended — by vendor removal or technician leaving; kept as historical record, not deleted |

Two states from your suggested list — `INVITED`/`PENDING` and `REJECTED` — belong to the *invitation*, not the relationship, under this model: a rejected invitation never produces a relationship row at all, so there's no such thing as a relationship in a "rejected" state to track. This isn't a smaller model than what you sketched, just a more precise placement of each state onto the object it actually describes.

## 12. Notification requirements

- Technician: new invitation received (email + in-app), invitation about to expire, relationship suspended/terminated by a vendor.
- Vendor: invitation accepted, invitation rejected, invitation expired unanswered, technician-initiated relationship termination.
- Both channels should carry enough context to act without digging — who, what, and a direct link to respond.

## 13. Email invitation flow

1. Vendor submits an email (and optional message).
2. System checks whether any `Employee`/`User` already has that email.
3. If yes: create the `VendorInvitation` with `technician_id` set, mark it visible in-app, fire an in-app notification and a lighter-touch "you have a new invitation" email.
4. If no: create the `VendorInvitation` with `technician_id` null and `invited_email` set, send a full invitation email with a signed link encoding the invitation id.
5. That link drops the person into signup pre-filled with their email; on successful signup, a post-signup hook looks up any `VendorInvitation` rows matching the new account's email and backfills `technician_id` on all of them (there can be more than one waiting, per §15) so they now appear in the technician's dashboard.
6. From here, both paths converge on the same Accept/Reject action.

## 14. Edge cases

- **Same technician invited by the same vendor twice** — resend should update/re-open the existing `PENDING` invitation rather than create a second one; if the prior invitation was `REJECTED` or `EXPIRED`, a fresh invitation row is fine (it's a new ask, and keeping the old one preserves the fact that they said no once before).
- **Technician already has an ACTIVE relationship with a vendor who invites them again** — no-op, or treat it as an update to relationship scope/terms rather than a new invitation.
- **Vendor sends an invitation, technician never signs up** — invitation sits unresolved until it expires; no account, no relationship, nothing left behind but the expired invitation record.
- **Two vendors invite the same not-yet-registered email around the same time** — both invitations are created independently against the same `invited_email`; when the technician finally signs up, both resolve onto the one new `Employee` row and both appear in their dashboard, exactly as required in §6.
- **Technician rejects, vendor wants to try again later** — allowed; a new invitation is a distinct row, and the technician's dashboard/history can show "previously invited and declined by this vendor on [date]" for context.
- **Vendor deletes/deactivates their company** — relationships should be terminated (not deleted) so technicians retain accurate history of past vendor work.
- **A relationship's scope drifts from what the technician actually offers** (vendor added AC Repair to the relationship, technician never listed that skill) — worth a soft warning in the vendor UI, not a hard block, since scope is a negotiated term of the relationship, not strictly derived from the technician's profile.
- **Criteria search returns zero matches** — should suggest relaxing specific criteria (e.g., "3 technicians match if you drop the experience requirement") rather than a bare empty state.

## 15. Duplicate technician prevention

This is enforced at three layers, not just as a rule someone has to remember to check:
1. **Signup itself** already prevents duplicate accounts per email (existing `User.email`/username uniqueness) — nothing new needed here.
2. **Invitation resolution** keys off `invited_email`, not off creating a placeholder technician record — an invitation to someone without an account creates zero `Employee` rows, only an invitation row waiting for a real signup.
3. **Post-signup backfill** (§13 step 5) sweeps all pending invitations for the new account's email and attaches them to the one real `Employee` that now exists — so however many vendors independently invited that email before they ever signed up, they all resolve onto a single technician identity the moment that identity is created.

## 16. Multiple vendor relationship handling

Every relationship is its own row, its own status, its own scope, its own timeline — there is no field anywhere that says "the technician's vendor," singular. Accepting one invitation only ever writes one `VendorTechnicianRelationship` row; it has no side effect on any other invitation or relationship belonging to that technician. The technician's dashboard is simply "every relationship/invitation row where `technician_id` = me," which naturally supports any number of simultaneous vendors without special-casing.

## 17. Permissions and access control

- A technician can only read/act on invitations and relationships where they are the `technician_id` (or the matching `invited_email`, pre-resolution).
- A vendor admin/manager can only read/act on invitations and relationships where `vendor_id` is their own company — this reuses the exact tenant-isolation pattern already enforced throughout the existing codebase (`emp.company_id != user_company.id` checks), applied to the new tables.
- A vendor should never be able to see another vendor's relationship with a shared technician, or that technician's other vendors — a technician's network is visible only to the technician themselves and platform admins.
- Platform-level admins/superusers can see across all vendors, for support and dispute resolution.
- Sending an invitation, running a match search, and modifying a relationship's status should each be checked as a vendor-admin-level action, not available to every user in a vendor's company.

## 18. API-level considerations

- Keep invitation creation, response, and relationship management as distinct endpoints rather than overloading a single "technician update" endpoint — mirrors the two-table split and keeps audit logging clean.
- Matching search should be its own endpoint that accepts a criteria expression and returns paginated, ranked results — this is a read-heavy, potentially expensive query path (especially "OR"-heavy searches across a large technician base) and deserves its own indexing strategy (see §22) separate from simple CRUD.
- Rate-limit invitation creation per vendor to prevent spam-inviting large numbers of technicians.
- Webhook/event hooks on relationship status changes (ACTIVE, SUSPENDED, TERMINATED) are worth emitting internally even in v1, since job-dispatch, payroll, and notifications all need to react to them — better to design that as an event rather than have every consumer poll the relationship table directly.
- Idempotency on the direct-email-invite endpoint (same vendor, same email, sent twice quickly) — resolve per the resend rule in §14, not by erroring or duplicating.

## 19. UI/UX recommendations

- Every invitation card should answer, at a glance and in this order: who's asking, why (which criteria/skills), what's on offer, and what accepting actually commits the technician to — your own mockups in the prompt already get this right; keep that structure.
- Make it visually obvious that Accept never affects other pending invitations — a short reassuring line ("Accepting doesn't affect your other vendor relationships") the first time a technician sees multiple simultaneous invitations removes real hesitation.
- On the vendor side, surface relationship history even for rejected/expired invitations (greyed out, not hidden) so a vendor doesn't lose track of who they've already approached.
- Criteria-builder UI should default to a friendly form (checkboxes for skills within one OR group, separate required fields ANDed together) rather than exposing the AND/OR tree structure directly — most vendors won't want to think in boolean logic, they'll want "any of these skills, but definitely in this city."

## 20. Recommended terminology

Borrowing the mental model but not the game-specific words, since "clan" and "player" would confuse a professional workforce product:

| Concept | Recommended term | Avoid |
|---|---|---|
| The technician's own profile | **Technician Profile** | "Player" |
| A vendor business | **Vendor** | "Clan" |
| A vendor's set of wanted attributes | **Technician Requirements** or **Criteria** | "Clan requirements" |
| The proposal step | **Invitation** | "Clan invite" (fine informally, not in-product copy) |
| The ongoing connection | **Vendor Relationship** or **Network Membership** | "Membership" alone (too close to a paid-subscription connotation) |
| The technician's own screen | **My Vendor Network** | — (this one's already good, keep it) |
| The vendor's own screen | **Technician Network** | — (also good, keep it) |

## 21. Potential problems with this model

- **Payment routing ambiguity**: today's job-settlement logic (`resolve_payee_wallet`) unconditionally pays a technician's own personal wallet if one exists, before ever considering a company's wallet. That actually fits this model well by default — an independent technician stays paid directly regardless of how many vendor relationships they hold — but it means a vendor relationship where the *vendor* is supposed to collect payment and pay the technician separately (a true "through vendor" engagement) needs an explicit `payment_model` flag on the relationship (already included in §8) and settlement logic that branches on it, or every vendor relationship will silently behave as "technician paid directly" even when that's not the deal.
- **Criteria matching performance at scale**: an AND/OR expression over an arbitrary number of attributes, evaluated against a technician base in the thousands-to-millions range, is not a query you want to run as a naive filter chain. Left unaddressed this becomes a real bottleneck as the network grows (see §22 for the fix).
- **Relationship scope creep**: if `scope_skills` on a relationship is allowed to drift arbitrarily far from the technician's actual approved skills, "vendor relationship" and "technician's real capability" can quietly diverge, leading to jobs being offered for work the technician isn't actually approved for.
- **Invitation fatigue**: with matching making it easy to invite dozens of technicians at once, without a rate limit and clear per-vendor invitation history, technicians could be flooded, and vendors could lose track of who they've already tried.
- **Ownership language creeping back in**: it's easy for future features (analytics, reporting, admin tooling) to casually start treating "vendor's technicians" as if the vendor owns them, especially in list views/exports. Worth a standing rule in code review: any query joining `Company` to technicians must go through `VendorTechnicianRelationship`, never through `Employee.company`, for anything related to vendor network features.

## 22. Improvements recommended beyond the base ask

- **Promote skills to a real relational table** (the `Skill`/`TechnicianSkill` split in §8) rather than the current free-text JSON `service_roles` field — this is a prerequisite for efficient matching, not optional polish, once search volume grows past a trivial size.
- **Precompute a technician "searchable attributes" index** (a denormalized row or a search-optimized store — Postgres GIN/array indexes are enough at moderate scale; a dedicated search index like OpenSearch/Elasticsearch once you're truly at "millions of technicians") so that OR-heavy, multi-attribute criteria searches don't degrade into full-table scans as both sides of the marketplace grow.
- **Cap and audit bulk invitations** — a per-vendor daily invitation limit plus a visible "who have I invited before" list, addressing the invitation-fatigue risk above proactively rather than reactively.
- **Let a technician set default response preferences** (e.g., "auto-decline anything below ₹X per job," "only notify me about Bengaluru opportunities") once volume grows — not needed for launch, but the schema in §8 doesn't block adding it later.
- **Emit relationship-status-change events** (§18) from day one even before anything consumes them, so the event log itself becomes free audit history and a foundation for later analytics ("average time from invitation to acceptance," "vendor retention of technicians") without retrofitting instrumentation later.

## 23. End-to-end example: Ravi and three vendors

1. Ravi signs up independently — one `User`, one `Employee`, homed under the platform's shared default company exactly as today's individual-onboarding flow already works. No vendor involved yet.
2. **ABC Home Services** runs a match search for AC Repair OR AC Installation technicians in Bengaluru. Ravi matches. ABC invites him from the results. `VendorInvitation(vendor=ABC, technician=Ravi, status=PENDING, channel=MATCHING_RESULT)` is created; Ravi gets an in-app notification.
3. **CoolCare Services** doesn't search — their ops lead already knows Ravi from a prior job and types his email directly. `VendorInvitation(vendor=CoolCare, technician=Ravi, status=PENDING, channel=DIRECT_EMAIL)` is created; since Ravi already has an account, it shows up in-app immediately alongside ABC's.
4. **XYZ Facility Services** also finds him via search and invites him with a per-job payment offer noted in the invitation message. A third independent `VendorInvitation` row, same pattern.
5. Ravi's dashboard now shows three pending invitations, each showing who, why, what's required, and what's offered — exactly as laid out in your mockup.
6. Ravi accepts ABC: `VendorInvitation(ABC).status → ACCEPTED`, and a new `VendorTechnicianRelationship(vendor=ABC, technician=Ravi, status=ACTIVE, source_invitation=that invitation)` is created.
7. Ravi rejects CoolCare: `VendorInvitation(CoolCare).status → REJECTED`. No relationship row is ever created for CoolCare. Ravi's ABC relationship is entirely unaffected.
8. Ravi leaves XYZ's invitation untouched for now — it simply sits `PENDING` until he decides or it expires.
9. Two months later, ABC suspends the relationship during a quiet season: `VendorTechnicianRelationship(ABC).status → SUSPENDED`. Ravi still has his own profile, his own independent job stream, and can still respond to XYZ's still-pending invitation or accept new ones — nothing about ABC pausing him touches any of that.
10. At the database level, at every point in this story, there is exactly one `Employee` row for Ravi — never two, never three — with independently evolving invitation and relationship rows layered on top of it, which is the entire point of the design.
