# M14 — Security, Audit & Hardening

## Stay concurrency fix
The hotel/stay advisory lock is now keyed by company + resource only. Check-in date is deliberately excluded, so overlapping reservations with different start dates serialize on the same room/resource before conflict search.

## Sensitive audit
A read-only manager audit model records sensitive booking/stay changes including actor, company, timestamp, changed fields, and before/after snapshots. Chatter remains useful for user-facing history; this log is intended for security/forensic review.

## Authorization
Commercial discounts are now enforced in the backend: only Booking Supervisor/Manager may apply a non-zero discount. UI visibility is not treated as security.

## Multi-company
Additional record rules cover services, packages, payment schedules, operation templates/items, and security audit entries. Existing booking/hall/period/resource/stay isolation remains.

## Reopen race
Cancelled event bookings now acquire the canonical hall/day advisory lock and check availability before changing back to draft.

## Still intentionally unresolved
Branch architecture is not invented in M14. The legacy module used `custom.branches`; V2 currently uses company isolation. Branch migration/API semantics must be decided explicitly before API freeze.
Accounting reversal/refund UAT is also still required in real Odoo 13.

## Production gate
Static validation is not runtime proof. Real PostgreSQL two-cursor concurrency tests, ACL/record-rule tests with multiple users/companies, and Odoo 13 browser/runtime UAT remain mandatory.
