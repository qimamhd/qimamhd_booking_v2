# Milestone 5 — Multi-vertical booking architecture

## Strict separation
Two booking concepts intentionally remain separate:
- Event booking: one date + one/more periods, for halls/events.
- Stay booking: check-in/check-out interval, for rooms/apartments/chalets.

They share customers, company, currency and later accounting services, but they do not share conflict semantics.

## Resource abstraction
`qimam.booking.resource.type` defines whether a resource is `event` or `stay`.
`qimam.booking.resource` represents the physical bookable asset.

This prevents room concepts from leaking into hall booking and vice versa.

## Hotel overlap rule
A stay conflicts only when:
`existing.checkin < requested.checkout AND existing.checkout > requested.checkin`
for the same company/resource and a blocking state.
Back-to-back stays (checkout == next checkin) are valid.

## UI strategy
Events: monthly dual-calendar direction + day/period availability workspace.
Hotels: room/stay planner direction + check-in/out workflow.
Mixed businesses: separate workspaces under one booking app.

The current hotel UI uses Odoo's native colored calendar as a safe baseline.
A custom room-row/day-column timeline client action is the next presentation layer; it will consume the same strict stay engine instead of duplicating availability logic.
