# M22 — Mobile Operations API

Adds branch-scoped read endpoints required by Flutter M5:

- `POST /api/v2/events/bookings/list`: event bookings in an inclusive date range.
- `POST /api/v2/stays/bookings/list`: stays intersecting a requested calendar range using canonical half-open stay semantics.

Both endpoints use the existing Bearer guard, active branch validation, optional state filtering and a bounded result limit. They serialize through the same canonical `_event()` / `_stay()` payloads used by detail/create/action endpoints.

This milestone does not duplicate business logic in Flutter. Lifecycle actions still use the existing `/bookings/action` endpoints.
