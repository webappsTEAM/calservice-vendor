# CalTrack / SEVO — What Got Fixed

A plain-English rundown of the ten fixes made across the vendor app and the customer app, and how each was checked.

## Vendor app (technician/vendor codebase, `testing` branch)

**1. Fake photo submissions were getting accepted.**
Technicians were able to submit job photos that were blank black frames — 28 of 29 stored photos on file turned out to be byte-for-byte identical black images, meaning the camera capture wasn't actually working and nobody had noticed. The fix adds a real check (using the Pillow image library) that rejects a photo if it's just a solid black frame, so a technician can no longer "complete" a job with a photo that shows nothing.

**2. Job start / clock-in was broken.**
There was a bug in how a technician's clock-in was recorded when starting a job, which the fix corrects.

**3. Session, presence, and location tracking issues.**
Several related problems with how a technician's login session, online/offline presence, and live location were being tracked and kept in sync were fixed together.

**4. Hold, resume, and overtime handling — plus a delay webhook.**
Added proper support for a technician putting a job on hold and resuming it later, correct overtime calculation, and a webhook that fires when a job is running late (so the system — and presumably the customer — gets notified of delays).

Plus one housekeeping commit to clean up inconsistent line endings across the codebase.

## Customer app (customer-facing booking codebase, `claude` branch)

**5. Session handling fix, plus WebSocket / live-tracking fixes.**
Corrected a session-handling bug and fixed problems with the WebSocket connection used for real-time order tracking.

**6. Same-day booking cutoff was fake, and delay notifications were added.**
The only cutoff time that stopped someone from booking a slot that had already passed was living in the frontend and checking the *browser's* clock — so it was both easy to bypass and simply wrong for any customer whose device wasn't set to Indian time. The backend only checked that the date wasn't in the past, with no time-of-day check at all, meaning a customer could book a slot from earlier that same day. The fix moves the real cutoff logic onto the server: bookings are now blocked once it's past a configurable hour (6 PM by default) same-day, and a minimum lead time (60 minutes by default) is enforced too — both adjustable via settings rather than hardcoded. A customer-facing delay notification was added alongside this.

Plus the same line-ending cleanup commit as the vendor side.

## How these were checked at the time

Every changed file was compiled/parsed (Python via `py_compile`, JS/JSX via `esbuild`) and cross-checked so nothing referenced a function that didn't actually exist. The vendor backend was running live and responded with a healthy status after reloading the new code, and the new hold/resume endpoints came back as "exists but needs login" (401) rather than "doesn't exist" (404) — confirming they were really wired in, not just written. Pillow was confirmed installed, so the black-photo rejection was genuinely active rather than silently doing nothing.

One gap noted at the time: the customer backend wasn't responding when checked, so the booking-cutoff and delay-notification changes were verified by code inspection and compilation, not by hitting a live server.

## Where things stand now

That verification was done in a working session that has since ended, along with its running servers and the live git repos. To re-confirm all ten fixes are still in place and working, the repos need to be reconnected (or re-uploaded) so they can be re-tested rather than taken on the earlier word.
