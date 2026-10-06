# M12 — Operations & Event Readiness

## Mission Control
A dedicated event workspace separates operational readiness from accounting.
It shows one readiness score and three execution lanes:
- Before the event
- Event day
- After the event

## Templates
Managers configure reusable readiness templates. A template can be:
- required or optional;
- event-blocking or non-blocking;
- tied to a specific sold service.

Service-tied tasks are generated only when that service is actually present on the booking.

## Execution
Operational items support To Do, In Progress, Done, Blocked, and reset.
Completion records the responsible user/time.

## Hard gate
`qimam.booking.action_start_event()` now checks event-blocking operational items in the model itself. The UI cannot bypass the rule.

## Separation of concerns
Readiness percentage is operational. The Mission Control shows a compact financial status for awareness, but financial status is not mixed into operational completion.

## Next production work
Real Odoo 13 UAT remains mandatory. Before release, add company record rules for the new operational models, validate manager/user permissions, test multi-company isolation, and exercise the event-day workflow in browser.
