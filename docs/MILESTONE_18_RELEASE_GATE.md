# M18 — QA / UAT / Production Release Gate

No new business feature is introduced here. M18 is the production gate.

## Automatic static gate
Run `python3 scripts/release_gate.py`.
A failure blocks deployment.

## Mandatory staging gates
### Branch isolation
Use Branch A/B and A-only, B-only, A+B users. Events, stays, planners, dashboards, reports and API must never leak another unauthorized branch.

### Events
Draft non-blocking; hold/confirmed/preparing/event/completed blocking; cancelled releases; different periods allowed; same period rejected; concurrent same-slot test permits exactly one; reopen rechecks under lock; cross-branch hall/period rejected.

### Hotel
For one room test exact overlap, contained, contains, left/right overlap (all rejected), adjacent checkout==next checkin (allowed), draft/cancelled non-blocking, hold/confirmed/checked-in blocking, cross-branch resource rejected, and two concurrent overlapping bookings with different check-in dates (exactly one succeeds).

### Finance
Test no invoice, draft, posted unpaid, partial, paid, deposit/full confirmation policy, duplicate-draft capacity, credit note, refund, payment reversal, cancellation and reopen. Posted accounting documents are never silently deleted.

**NO-GO:** hotel/stay accounting is not yet integrated to the same canonical invoice/payment/reversal lifecycle. If hotel invoicing/payment is part of Release 1.0 sold scope, it must be implemented before GO.

### Operations
Readiness generation, blocker enforcement, Mission Control, branch isolation.

### API/Auth
Real HTTP: login, invalid password, non-booking user, access expiry, refresh rotation/reuse rejection, device mismatch, logout/revoke, Nginx Authorization forwarding, branch escalation, event/stay semantic separation.

### Migration
Dry Run per branch, execute, rerun without duplicates, reconcile counts/contracts/customer/date/hall/state, verify V1 unchanged. Accounting mapping remains a separate mandatory pass where historical accounting must be retained.

### UI
Arabic RTL: Booking OS, hall planner, hotel timeline, Studio, Payment & Confirmation, Mission Control, Executive Dashboard. No JS/QWeb console errors or clipped primary actions.

## Automatic NO-GO conditions
Any failure in concurrency, branch isolation, accounting integrity, authentication, or migration idempotency.

## Known product truth
Current Hijri conversion is civil/tabular, not official Saudi Umm al-Qura.
