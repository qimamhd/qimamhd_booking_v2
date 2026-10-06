# M17 — API Security & Production Authentication

## Token model
- 30-minute opaque access token
- 30-day opaque refresh token
- SHA-256 hashes only are stored in PostgreSQL
- refresh token is one-time: refresh revokes the old session pair and issues a new pair
- logout revokes the current session
- expired/revoked sessions are purged by cron
- inactive Odoo users cannot continue using an access token

## Device binding
Login may include `device_id` and `device_name`. If a session is device-bound, every protected request must send the same value in `X-Device-ID`. Device binding is optional at this stage; policy enforcement can be made mandatory per company later.

## Authorization
Protected `/api/v2/*` business routes no longer trust an Odoo browser session. They require:
`Authorization: Bearer <access_token>`

After token verification the ORM environment is switched to the token's real Odoo user. Therefore ACLs, record rules, `allowed_branch_ids`, supervisor/manager groups and branch constraints remain authoritative.

## Login
`POST /api/v2/auth/login`
Payload: `db`, `login`, `password`, optional `device_id`, `device_name`.

Only users in Booking User (or inherited Supervisor/Manager) may receive tokens.

## Refresh
`POST /api/v2/auth/refresh`
Payload: `db`, `refresh_token`, optional `device_id`.

## Logout
`POST /api/v2/auth/logout` with Bearer token.

## Domain integrity remains unchanged
Events: branch + hall + date + periods.
Stays: branch + resource + [checkin, checkout).

## Security notes
No plaintext token is persisted. Generic authentication failures avoid exposing internal exception details. Business endpoints continue returning stable API envelopes.

## Runtime gate
Static source checks are not enough. Before production, HTTP integration tests on real Odoo 13 must verify auth=none DB selection behavior, request.env switching, refresh rotation, concurrent requests, record rules, reverse proxy Authorization header forwarding, and mobile logout/revoke.
