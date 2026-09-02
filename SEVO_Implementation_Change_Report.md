# SEVO Implementation — Change Report

**Branch:** `sevo-gap-fixes-stage0` (local only, nothing pushed)
**Repo root:** `D:\Caldim\Calservices`
**Scope:** `vendor/backend/workforce_api/` and `vendor/frontend/src/` only. `Customer/Mobile App/` was never touched.
**Commit range:** `36e1fbc` → `2a4e995` (12 commits, one per backend/frontend half of each task)
**Verification performed:** `python3 -m py_compile` on every touched Python file (all clean), hand-written migrations verified via `importlib` against Django 5.2.17, a newline-convention audit against the pre-change baseline for every touched file (no accidental CRLF/LF corruption), brace/paren/tag balance checks on every touched JSX file, and a scoped `git diff --stat` after every commit to confirm only the intended files changed.

This implements the 8-section SEVO business/operational plan (wallet infrastructure, payouts, commission, onboarding, dispatch attribution, disputes, scorecards, financial controls, compliance, scheduled withdrawals) end to end. Each numbered item below is one commit; check it out with `git show <hash>` or `git log -p <hash> -1` to see the exact diff.

---

## 1. Wallet infrastructure data model — `36e1fbc`

**What:** The core ledger data model everything else builds on.

- `vendor/backend/workforce_api/models.py` (+278 lines) — `WalletAccount` (two kinds: `PROVIDER_HEAD` per company, `INDIVIDUAL_WORKER` per employee), `WalletLedgerEntry` (job credits, commission/withdrawal/clawback debits, HELD/RELEASED/CLAWED_BACK status), `WithdrawalRequest`, `SocialSecurityRegistration` scaffolding. Also the `auto_withdrawal_*` and `minimum_balance_alert_threshold` fields used later by Task 40.
- `vendor/backend/workforce_api/migrations/0015_sevo_wallet_infrastructure.py` (new, +141 lines)

**Verify:** `python manage.py migrate workforce_api` should apply `0015` cleanly; inspect the new tables (`workforce_wallet_account`, `workforce_wallet_ledger_entry`, `workforce_withdrawal_request`, `workforce_social_security_registration`) in the DB.

## 2. RazorpayX payout adapter — `fc28837`

**What:** The only module that talks to RazorpayX. Degrades gracefully to `AWAITING_RAZORPAYX_ACTIVATION` instead of crashing when credentials aren't configured (they aren't, in this environment).

- `vendor/backend/workforce_api/services/payouts.py` (new, 266 lines) — `is_configured()`, `ensure_fund_account()`, `execute_withdrawal()`, `handle_payout_webhook()`, `retry_pending_activations()`.

**Verify:** With no `RAZORPAYX_KEY_ID`/`RAZORPAYX_KEY_SECRET`/`RAZORPAYX_ACCOUNT_NUMBER` set, any withdrawal should end up `AWAITING_RAZORPAYX_ACTIVATION`, never crash.

## 3. Commission engine — `ef0b448`

**What:** The sole writer of ledger entries for a completed job.

- `vendor/backend/workforce_api/services/commission.py` (new, 264 lines) — `settle_completed_job()` computes gross/commission/net and writes the `JOB_CREDIT` + `COMMISSION_DEBIT`/`COD_COMMISSION_PAYABLE` pair, HELD until the dispute window passes.

**Verify:** Complete a job end-to-end in a test tenant and confirm two ledger entries appear for it, `HELD` initially.

## 4. Provider + individual worker onboarding (backend) — `28f5892`

- `vendor/backend/workforce_api/services/wallet_onboarding.py` (new, 157 lines) — `provision_provider_wallet()`, `provision_individual_wallet()`, `resolve_wallet_for_user()`, `set_payout_details()`.
- `views.py` (+193), `serializers.py` (+92), `urls.py` (+6) — `POST /workforce/provider/signup/`, `GET /workforce/wallet/me/`, `PATCH /workforce/wallet/payout-details/`.

## 5. Provider + wallet frontend flows — `2e39915`

- New `pages/auth/ProviderSignupPage.jsx` (256 lines), new `pages/admin/AdminWalletPage.jsx` (194 lines — later extended twice, see items 9 and 12), routing/nav wiring in `App.jsx`, `Sidebar.jsx`, `AuthProvider.jsx`, `SignupPage.jsx`.

**Verify:** `/workforce/provider-signup` and `/workforce/admin/wallet` should render and round-trip through the new endpoints.

## 6. Per-job wallet attribution — `044fcef`

- `serializers.py` (+33) — exposes which worker/company a job's ledger credit is attributed to, on the job serializer.

## 7. Dispute hold-and-clawback admin wiring — `5a4d1d7`

- `views.py` (+98), `urls.py` (+4) — `GET /workforce/admin/wallet/held-earnings/`, `POST /workforce/admin/wallet/clawback/`.
- `management/commands/release_wallet_holds.py` (new, 55 lines) — the daily/loop sweep that matures a `HELD` ledger entry to `RELEASED` once the dispute window passes.

**Verify:** `python manage.py release_wallet_holds --once` should run without error; a held entry older than `SEVO_DISPUTE_HOLD_HOURS` (default 48h) should flip to `RELEASED`.

## 8. Worker-level rating + SLA scorecards — `d894ed7` (backend) / `fbfb5fb` (frontend)

**Backend:**
- `models.py` (+51) — `WorkforceScorecard` (per-employee `rating_count`, `average_rating`, `sla_score`, `tier` BRONZE/SILVER/GOLD, needs `rating_count >= 3` to tier).
- `migrations/0016_workforce_scorecard.py` (new, 46 lines) — **the only new migration this session besides `0015`.**
- `services/scorecards.py` (new, 107 lines) — `recalculate_employee_scorecard()`, `recalculate_all_scorecards()`.
- `services/automatic_dispatch.py` (+21/-4) — dispatch ranking now includes a scorecard bonus (0–20 points, gated on `rating_count >= 3`).
- `views.py` (+85), `urls.py` (+2) — `GET /workforce/admin/scorecards/`; scorecard recalculated on every new job feedback submission.
- `management/commands/backfill_scorecards.py` (new, 46 lines).

**Frontend:**
- New `pages/admin/AdminScorecardsPage.jsx` (124 lines), scorecard banner added to `pages/employee/EmployeePerformancePage.jsx` (+30), nav/routing in `App.jsx`/`Sidebar.jsx`.

**Verify:** `python manage.py backfill_scorecards`, then check `/workforce/admin/scorecards` renders a sorted (worst-first) tier table; submit job feedback and confirm the employee's scorecard updates.

## 9. Financial controls: reconciliation + tax statements — `ec3848d` (backend) / `e53a29e` (frontend)

**Backend:**
- `services/reconciliation.py` (new, 184 lines) — `run_daily_reconciliation()` checks for missing settlements, gross/net mismatches (tolerance ₹0.05), and reports an *informational* expected-escrow-balance figure (explicitly **not** compared against a real bank statement — no live bank feed exists in this codebase; documented in the module docstring).
- `services/tax_statements.py` (new, 145 lines) — `generate_earnings_statement()`, `export_ledger_csv()`. **Deliberately excludes any TDS/tax-withholding computation** — the business plan itself says this needs CA/legal sign-off before go-live.
- `views.py` (+95), `urls.py` (+6) — `GET /workforce/wallet/statement/`, `GET /workforce/wallet/ledger/export/`, `GET /workforce/admin/reconciliation/`.
- `management/commands/run_daily_reconciliation.py` (new, 72 lines, supports `--date` and `--json`).

**Frontend:**
- `AdminWalletPage.jsx` (+152) — Earnings Statement card (month/year picker) + CSV wage-register download button.

**Verify:** `python manage.py run_daily_reconciliation --json` should run cleanly against your data; download the CSV from the wallet page and confirm it matches the ledger.

## 10. Social Security Code (2020) registration tracking — `332b706` (backend) / `24b727f` (frontend)

**Backend:**
- `services/social_security.py` (new, 158 lines) — `recompute_registration_status()` counts distinct days-worked per Indian financial year (Apr 1–Mar 31) for `INDIVIDUAL_WORKER`-only employees, flips to `ELIGIBLE_PENDING_REGISTRATION` at 90 days, never downgrades a `REGISTERED` row. **No automated government-portal integration** — this is deliberately an exportable worklist, not a Shram Suvidha API integration (none exists to integrate against).
- `services/commission.py` (+12) — hooks the eligibility recompute into every job settlement.
- `views.py` (+76), `urls.py` (+4) — `GET /workforce/admin/social-security/`, `POST /workforce/admin/social-security/mark-registered/`.
- `management/commands/update_social_security_eligibility.py` (new, 37 lines).

**Frontend:**
- New `pages/admin/AdminSocialSecurityPage.jsx` (206 lines) — status-filtered worklist with an inline "Mark Registered" flow requiring a portal reference ID. Wired into `App.jsx` (+9) and `Sidebar.jsx` (+9).

**Verify:** `python manage.py update_social_security_eligibility`; check `/workforce/admin/social-security` lists individual workers only (never provider-team workers) with correct day counts.

## 11. Scheduled withdrawals + minimum-balance alerts — `d9ec9b4` (backend) / `2a4e995` (frontend)

**Backend:**
- `services/withdrawals.py` (new, 202 lines) — `request_withdrawal()` (shared validation: available balance + KYC-tier daily cap, used by both on-demand and scheduled paths), `check_minimum_balance_alerts()` (in-app notification, 24h cooldown so it doesn't spam), `run_scheduled_withdrawals()` (fires each wallet's standing daily/weekly rule).
- `views.py` (+94), `serializers.py` (+21), `urls.py` (+4) — `POST /workforce/wallet/withdraw/`, `PATCH /workforce/wallet/auto-withdrawal/`.
- `management/commands/run_scheduled_withdrawals.py` and `check_minimum_balance_alerts.py` (new, 35 lines each). **Neither is scheduled anywhere yet** — you'll need to add them to your cron/systemd timer setup alongside `release_wallet_holds` and `run_daily_reconciliation`.

**Frontend:**
- `AdminWalletPage.jsx` (+211) — "Withdraw Now" card (amount + Max shortcut) and "Scheduled Withdrawals & Alerts" card (daily/weekly toggle, day-of-week picker, minimum-balance threshold input).

**Verify:** On the wallet page, set a minimum-balance threshold below your current balance, run `python manage.py check_minimum_balance_alerts`, and confirm no alert fires; lower the threshold above balance and re-run — an in-app notification should appear for the wallet owner (or the company's admins/managers for a provider head wallet).

---

## Full endpoint list added this session

```
POST   /workforce/provider/signup/
GET    /workforce/wallet/me/
PATCH  /workforce/wallet/payout-details/
POST   /workforce/wallet/withdraw/
PATCH  /workforce/wallet/auto-withdrawal/
GET    /workforce/wallet/statement/
GET    /workforce/wallet/ledger/export/
GET    /workforce/admin/wallet/held-earnings/
POST   /workforce/admin/wallet/clawback/
GET    /workforce/admin/scorecards/
GET    /workforce/admin/reconciliation/
GET    /workforce/admin/social-security/
POST   /workforce/admin/social-security/mark-registered/
```

## Full management-command list added this session

```
release_wallet_holds                    (Task 7  -- --once / --loop / --interval)
backfill_scorecards                      (Task 8  -- --company-id optional)
run_daily_reconciliation                 (Task 9  -- --date / --json)
update_social_security_eligibility       (Task 10 -- no args)
run_scheduled_withdrawals                (Task 11 -- no args)
check_minimum_balance_alerts             (Task 11 -- no args)
```
None of these are wired into a scheduler yet — that's an operational step for you to do before go-live (a cron entry or systemd timer per command, run daily except `release_wallet_holds` which is designed to loop every 15 minutes).

## Known, deliberate scope exclusions (documented in the relevant module docstrings, not silently assumed)

- **No TDS/tax withholding** anywhere in `tax_statements.py` — the plan itself flags this as needing CA/legal sign-off before go-live.
- **No live bank/escrow balance comparison** in `reconciliation.py` — the `expected_escrow_balance` figure is informational only, since no bank-statement API exists in this codebase; it's meant for manual human tie-out.
- **No automated Shram Suvidha portal integration** in `social_security.py` — registration is a manual admin action recording that someone actually did the government-portal submission.
- **No RazorpayX activation** in this environment — every payout path degrades to `AWAITING_RAZORPAYX_ACTIVATION` rather than failing.

## One pre-existing, unrelated item to be aware of

Running an *unscoped* `git status`/`git diff` in this repo shows a large number of deleted/modified files outside `vendor/backend/workforce_api` and `vendor/frontend/src` (top-level docs, `backend/` at repo root, etc.). That divergence predates this session and was not touched by any of this work — every check above was scoped specifically to the two directories this implementation lives in, both of which are fully clean (`git status` shows nothing pending).
