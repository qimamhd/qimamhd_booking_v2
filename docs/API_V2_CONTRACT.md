# Qimam Booking API V2 — Frozen Candidate Contract

API version: `2.0`

## Architectural invariant
There are two booking domains. They share identity, company context, permissions and envelope conventions, but **not availability semantics**.

### Events
Namespace: `/api/v2/events/*`

Canonical availability key:
`branch + hall + date + period(s)`

Endpoints:
- `events/catalog`
- `events/availability`
- `events/bookings/create`
- `events/bookings/get`
- `events/bookings/action`

Allowed actions: `hold`, `confirm`, `prepare`, `start_event`, `complete`.

### Stays
Namespace: `/api/v2/stays/*`

Canonical availability key:
`branch + resource + [checkin, checkout)`

Endpoints:
- `stays/resources`
- `stays/availability`
- `stays/bookings/create`
- `stays/bookings/get`
- `stays/bookings/action`

Allowed actions: `hold`, `confirm`, `checkin`, `checkout`, `cancel`.

Adjacent stays are valid because checkout is exclusive.

## Shared endpoints
- `/api/v2/bootstrap`
- `/api/v2/customers/search`

`bootstrap` returns company business mode and server capabilities. Clients must use capabilities instead of assuming a domain is enabled.

## Envelope
Success:
`{"success": true, "api_version": "2.0", "data": ...}`

Failure:
`{"success": false, "api_version": "2.0", "error": {"code": "...", "message": "..."}}`

Stable error families in this candidate:
- `ACCESS_DENIED`
- `VALIDATION_ERROR`
- `AVAILABILITY_CONFLICT`
- `BUSINESS_RULE_VIOLATION`
- `INVALID_PAYLOAD`

## Authority
The client MUST NOT calculate official availability, tax, booking totals, financial status, readiness, or lifecycle validity. Odoo is authoritative.

## Authentication status
Business endpoints require opaque Bearer access tokens issued by `/api/v2/auth/login`. Access tokens expire after 30 minutes. Refresh tokens expire after 30 days and rotate on every refresh. Optional device binding is supported. Odoo ACLs, groups, and branch record rules are evaluated as the token user.

## Branch status
Branch isolation is canonical. The module depends on legacy-compatible `custom_branch_13`, uses model `custom.branches`, defaults to `user.branch_id`, and authorizes against `user.allowed_branch_ids`. `company_id` remains technical/accounting metadata and is not the operational reporting boundary.

## Compatibility
Do not repurpose event fields for stays or stay fields for events. Future incompatible changes require a new API version.


## Branch selection
Every operational API call defaults to `user.branch_id`. A caller may send `branch_id` only when that branch is in `user.allowed_branch_ids`. Availability, catalogs, bookings, resources and reporting are scoped to that validated branch.
