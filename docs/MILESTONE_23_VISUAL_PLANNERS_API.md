# M23 — Visual Planners API

Adds mobile-oriented, branch-scoped planner endpoints:

- `/api/v2/events/board`: halls × periods for one day, with booking identity and state per occupied cell.
- `/api/v2/stays/planner`: resources × 7–14 days, respecting canonical `[checkin, checkout)` semantics.

Both are protected by the existing Bearer guard and `active_branch()` authorization. Flutter renders these payloads; it does not reconstruct occupancy rules.
