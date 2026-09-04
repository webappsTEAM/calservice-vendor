# Razorpay / RazorpayX Integration — Status Report

**Prepared for:** Caldim Engineering — SEVO Workforce Platform
**Date:** September 1, 2026
**Branch:** `sevo-gap-fixes-stage0` (local only, nothing pushed)

## The short version

There are two different Razorpay products involved here, and it's worth separating them clearly because they're at very different stages.

**Razorpay Payments** (the standard checkout product customers use to pay for jobs) is not part of this piece of work at all — it's untouched.

**RazorpayX (Payouts)** is what pays workers and providers out of their in-app wallet to their bank account or UPI. This is what "the Razorpay integration" refers to in everything below. The code side of this is complete: the app can create payouts, receive confirmation webhooks, and gracefully queue withdrawals if RazorpayX isn't switched on yet. The business side is not complete: your Razorpay merchant account doesn't have RazorpayX access activated yet, and that's outside what code can fix. To get around that block for now, a safe local-only "pretend it worked" mode has been added so the whole withdrawal experience can be tested without waiting on Razorpay.

## What RazorpayX actually does in this app

Workers and providers earn money into an in-app wallet as jobs are completed. That wallet is just a ledger — numbers in the database — until someone asks to actually withdraw the money to their real bank account or UPI ID. RazorpayX is the piece that makes that real transfer happen. It's Razorpay's payouts product, a separate thing from the checkout widget customers use, but conveniently it uses the same API key and secret as regular Razorpay Payments — so the test credentials you already have work for both.

## What has been built

**Sending money out.** When someone requests a withdrawal, the app registers them with RazorpayX as a payee (a "contact" plus a "fund account" tied to their bank details or UPI ID — this only has to happen once per person) and then fires the actual payout request. If RazorpayX hasn't been switched on for this environment yet, the app doesn't error out or lose the request — it quietly marks it "awaiting activation" so nothing is lost, and it can be retried automatically the moment real credentials exist.

**Hearing back from RazorpayX.** A payout doesn't complete instantly — RazorpayX processes it and then calls back into our app to say whether it succeeded, failed, or was reversed. That callback (a "webhook") is now wired up: there's a public endpoint that receives it, checks that the message genuinely came from RazorpayX (not someone spoofing it), and updates the withdrawal's status accordingly. If a payout comes back as failed, the money that was provisionally deducted from the wallet is automatically put back, so the balance stays accurate. This was actually a place I found and fixed a real bug — the signature check that verifies a webhook is genuine was comparing against a re-built copy of the message instead of the exact original one RazorpayX sent, which would have caused every single real webhook to be rejected as invalid. That's fixed now.

**Catching up once activation happens.** There's a small command an operator can run (or that can be scheduled) that goes through every withdrawal that's stuck waiting on activation and retries them all in one go, for the day RazorpayX access finally comes through.

**Wiring in your test credentials.** The Key ID, Key Secret, and webhook secret you provided are saved in your local environment file (not committed to git, so they're private to your machine) under the names the code expects. The one piece that's still blank is the RazorpayX account number — because that only exists once RazorpayX is actually activated for your merchant account, which hasn't happened yet (more on that below).

## The activation block (not a code problem)

RazorpayX needs its own current account to be set up and switched on for a merchant, separately from the everyday Razorpay Payments checkout that's presumably already working. Right now, trying to reach that setup from your Razorpay dashboard — whether through the direct RazorpayX link or the "Get a Current Account" / "Unlock Banking+" prompts — leads to an access-denied page. This isn't a team-permissions issue; it was confirmed you're the account Owner, which normally has full access to everything. That points to this simply being a step Razorpay itself hasn't turned on yet for this merchant account, which means it needs to be resolved through Razorpay support rather than anything in the codebase. You started raising a support ticket for this and hit a submission error, which you said you'd come back to later — so this piece is currently paused on your side, not blocked on mine.

## The workaround: testing everything without waiting on Razorpay

Since the real activation is out of anyone's hands for now but you still wanted to see the whole withdrawal flow working end to end, a local-only "mock mode" has been added. When it's switched on, a withdrawal request skips the real RazorpayX call entirely and simulates a successful payout instead — the same wallet debit happens, the same success status is set, the same statement and history entries appear — so you can click through the entire experience as if RazorpayX were live.

Safety was the main design concern here, since this is the kind of thing that could be dangerous if it ever leaked into a real environment: it's built so it can only ever activate when the app is explicitly running in local debug mode. Even if the mock-mode switch were accidentally left on somewhere, it simply cannot fire unless debug mode is also on, and a real deployment never runs in debug mode. On top of that, every trace of a simulated payout is clearly and permanently marked as fake — the payout ID, the reference number, the ledger note, the on-screen message, and the log entry all say so — so a mock withdrawal can never be mistaken for a real one, now or when reviewing history later.

This mode is currently switched on in your local environment, so you're able to test the complete flow right now.

## What's genuinely done vs. what's still waiting

**Done and working (locally, with test credentials):**
- Creating a payout and registering payee bank/UPI details with RazorpayX
- Receiving and verifying RazorpayX's confirmation callbacks, including the signature-check bug fix
- Automatically reversing a wallet debit if a payout later fails
- Gracefully queuing withdrawals instead of failing when RazorpayX isn't switched on
- A way to retry all queued withdrawals once it is switched on
- A safe, clearly-labeled local test mode that simulates the entire withdrawal experience

**Still outstanding, and not something code can fix:**
- Razorpay activating RazorpayX / a current account for your merchant account — currently blocked by an access-denied page even for the account Owner, and paused on the support-ticket step
- Once that's activated, the RazorpayX account number needs to be added to your environment, and mock mode should be switched back off so real payouts take over

Everything above is committed to your local git history only — nothing has been pushed anywhere, and the real credentials never leave your local, git-ignored environment file.
