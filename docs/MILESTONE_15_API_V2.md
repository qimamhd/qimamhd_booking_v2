# M15 — API V2 Domain Finalization

The API is now explicitly split into two first-class domains:
1. Events / halls: date + hall + periods.
2. Hotel / stays: resource + half-open date interval.

A shared bootstrap advertises company mode and capabilities. Flutter must select flows from this response.

The old provisional `/periods`, `/halls`, `/availability`, `/bookings/create` routes remain temporary event-only compatibility aliases. New clients must use `/events/*` and `/stays/*`.

Important release blockers still open:
- dedicated access/refresh token authentication and revocation/device policy;
- branch mapping decision from legacy `custom.branches`;
- real HTTP integration tests in Odoo 13;
- permission matrix tests;
- financial endpoints for stay bookings are not invented until stay accounting is canonically integrated.
