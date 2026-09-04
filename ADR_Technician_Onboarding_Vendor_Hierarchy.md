# ADR-001: Technician Onboarding & Vendor Hierarchy Model

**Status:** Proposed
**Date:** September 1, 2026
**Deciders:** Caldim Engineering / SEVO product & engineering

## Context

Two kinds of technicians need to get into the app: people who work for themselves, and people who work for a vendor business that has its own team. The question on the table is how onboarding should route each kind into the right place, and separately, whether a technician should ever be able to act as a "boss" over other technicians.

This isn't a blank-slate design — a fair amount of this is already built, and the recommendation below builds on what's there rather than replacing it. Here's what I found in the actual codebase:

- There are already two separate signup paths. `WorkforceSignupView` is the everyday technician signup. If it's given a `company_id` or `company_slug`, the new technician is enrolled directly onto that vendor's team. If not, they fall through to a shared default holding company and get their own personal wallet instead — this is already called the "Individual Worker Model" in the code's own comments.
- There's a second signup path, `ProviderSignupView`, for a business registering itself as a vendor. It creates a company record, a manager account for whoever signed up, and a shared "head wallet" for that company. It hands back a `company_id`/slug that the vendor can then give to their own workers so `WorkforceSignupView` routes those workers onto the vendor's team instead of the individual track.
- Money routing follows a simple rule at job-settlement time (`resolve_payee_wallet`): if the technician has their own personal wallet, that gets paid — full stop — and only if they don't does the job fall back to their employer's shared wallet. This rule is checked fresh on every single job, not just once.
- Onboarding already has a "which services do you do" step built in — a technician can select services from a catalog during signup, and each selected service gets its own pending/approved/rejected status that an admin can review individually.
- There's no concept today of one technician being the "boss" of others. The only hierarchy that exists is at the company level: a company has admin/manager users and employee users, and vendor's team members are all peers under that one company.
- The service selections technicians make during onboarding are saved, but nothing downstream — job dispatch, technician matching — actually reads that field yet. It's collected but not yet acted on.

## Decision

### 1. Individual-first, assign-to-vendor-later onboarding

**Recommendation: keep signup itself simple and identical for everyone, but treat "joining a vendor" as something that can happen either at signup or afterward — not as two different signup forms.**

Practically, this means every technician goes through the same onboarding screens (personal details, services, documents), and at one point in that flow they're asked "are you joining an existing team, or working on your own?" If they have a vendor's invite code, they enter it right there and are enrolled onto that vendor's team from day one — this is exactly the `company_id`/`company_slug` path that already exists. If they don't have one, they go through as an individual — also already built.

The part that's genuinely new is your proposal's second half: letting a vendor claim a technician *after* that technician already signed up on their own. That's a real gap today — there's no way to move someone from the individual track onto a vendor's team once they've onboarded. It's worth adding, because it covers a very ordinary situation: someone downloads the app and signs up before any vendor has reached them, and a vendor recruits them a week later.

There's one thing this needs that doesn't exist yet, and it matters enough to call out clearly: **once a technician gets their own personal wallet, the settlement logic pays that wallet forever, with no way to turn it off.** So simply moving someone's company record over to the vendor wouldn't actually redirect their future earnings to the vendor's shared wallet — the code would keep paying their personal wallet regardless, silently. Supporting "assign to a vendor after the fact" properly means adding a way to deactivate that personal-wallet routing at the moment of assignment, so that from that point forward, jobs settle into the vendor's head wallet like any other team member's. Whatever the technician already earned individually stays in their personal wallet and remains withdrawable — only future jobs change where the money goes.

**Why not do it the way you originally described — onboard literally everyone as individual first, always?** Two reasons. First, it adds a wallet-provisioning step for every single technician even when a vendor is standing right there ready to onboard their own team directly, which is wasted work for the common vendor-recruiting case. Second, it means every vendor-track technician briefly has a live personal wallet that then has to be deactivated, which is more moving parts than just not creating it in the first place when the vendor relationship is already known at signup. Letting people declare a vendor relationship at signup when they have one, and offering the after-the-fact assignment path for when they don't, gets you the same flexibility without that extra churn for the majority of vendor signups.

### 2. "Boss and subordinate" technicians

**Recommendation: don't build a second, parallel hierarchy for this. A technician who leads their own small team of subordinates is, structurally, exactly what "provider business" already means in this system.**

The `ProviderSignupView` path already does precisely what "make a worker the boss of a small crew" needs: it gives that person their own company record, makes them the manager of it, and gives them a code their own workers can use to join under them. If a technician wants to bring on a couple of helpers, the right move is to let them register as a provider (even a tiny one, one person plus a few workers) rather than inventing a "reports to this other technician" field bolted onto individual accounts.

The reason to avoid a second hierarchy model is that the company/tenant structure already carries a lot of weight in this codebase — cross-tenant data isolation, admin permissions, wallet ownership, job assignment scoping are all built around "which company does this person belong to." A separate peer-to-peer boss/subordinate relationship would either have to duplicate all of that (extra surface area to get wrong) or sit awkwardly alongside it without actually controlling any of those things, which would be confusing — a "boss" who couldn't see their subordinates' documents or manage their payouts wouldn't feel like a boss at all. Reusing the existing company model means a promoted technician instantly gets a real admin dashboard, real payout control over their team's wallet, and real document review — because the app already builds all of that for every provider company, it doesn't need to be built twice.

The only piece worth adding here is friction-reduction: letting an existing individual technician "upgrade" into a provider company from inside their own account (pre-filling their existing profile into the new company's admin account) rather than requiring a completely separate signup flow with a new email/login. That's a smaller, self-contained addition on top of `ProviderSignupView`, not a new data model.

### 3. Onboarding workers for specific services

**Recommendation: build on what's already there — the services step and the per-service approval status are already collected, they just need to start being used.**

The onboarding flow already lets a technician pick which services they offer from a catalog, and each pick gets tracked with its own approval state, independent of the others — so a technician could be approved for "AC repair" while "electrical wiring" is still pending review, for example. That's a solid foundation and doesn't need to be rebuilt.

What's missing is the other end of it: job assignment doesn't currently look at any of this. A job comes in for a specific service, but nothing today filters "which technicians are actually approved to do this service" before offering it to someone. Right now a technician's list of services is captured and displayed, but has no effect on what work they're offered. Closing that loop is the highest-value next step here — it's what turns "we asked what services you do" into something that actually matters operationally, rather than a form field nobody reads.

A reasonable phased approach:
1. When a job request specifies a service, only offer/assign it to technicians who have that exact service in their *approved* (not just selected) service list.
2. Let admins review and approve services one at a time per technician, the way documents are already reviewed one category at a time — this pairs naturally with the per-service status that's already stored.
3. Longer-term, this is also the natural place to attach service-specific requirements — a certification document only required for certain services, for instance — without having to touch the general document-upload flow.

## Trade-off Summary

| Approach | Pros | Cons |
|---|---|---|
| Signup-time choice only (current) | Simple, no wallet-migration complexity | Can't recruit an already-onboarded individual technician onto a vendor's team |
| Individual-first for everyone, always assign after | Uniform onboarding, no upfront branching | Extra wallet provisioning/deactivation for every vendor-track signup; more moving parts for the common case |
| **Signup-time choice + optional after-the-fact assignment (recommended)** | Handles both the common case (vendor recruits directly) and the edge case (technician signs up solo, gets recruited later) without extra overhead for the majority | Requires adding the wallet-routing cutover logic described above |
| New boss/subordinate hierarchy field | Feels closer to the literal request | Duplicates or bypasses the existing company-based permissions, wallet, and tenant-isolation model |
| **Reuse the existing provider/company model for "boss" (recommended)** | Free admin dashboard, wallet control, and document review for the promoted technician; no new permission model to build | Slightly heavier for a "boss" of just one or two people than a lightweight hierarchy field would be |

## Consequences

- Adding after-the-fact vendor assignment requires closing the wallet-routing gap (a personal wallet currently can't be "switched off" once created) — without that fix, assigning a technician to a vendor company would not actually change where their future earnings go, which would be a confusing and hard-to-notice bug in production.
- Treating "boss with subordinates" as "becomes a provider" means no new hierarchy data model, but does mean product/UX should offer a lightweight "upgrade to a small team" path from an individual account, rather than only advertising provider signup to people who already think of themselves as a full business.
- Making service selections actually filter job assignment is the one item here that's pure upside with no real trade-off — it's finishing something that's already half-built, not a new architectural decision.

## Action Items
1. [ ] Add a way to deactivate an `INDIVIDUAL_WORKER` wallet's job-settlement priority so `resolve_payee_wallet` stops paying it once a technician joins a vendor team.
2. [ ] Add an admin-facing "assign technician to my team" action that reassigns `Employee.company` and applies the wallet cutover above.
3. [ ] Add an in-app "upgrade to a provider team" path that lets an existing individual technician register a company (via the existing `ProviderSignupView` logic) without a separate signup form.
4. [ ] Wire approved `service_roles` into job assignment/dispatch so only technicians approved for a given service are offered jobs in that category.
5. [ ] Add a per-service admin approval action alongside the existing per-document approval action, since the data model already supports per-service status.
