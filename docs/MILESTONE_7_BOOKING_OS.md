# M7 — Booking OS Experience

This milestone deliberately moves the daily operator away from traditional Odoo forms.

## One product, two mental models
The top-level workspace follows company mode:
- Events: starts with today's event pulse and the Hall Planner.
- Hotel: starts with arrivals/departures/active stays and a guest-first availability search.
- Mixed: explicit Events / Hotel switch. No merged planner.

## Guest-first hotel workflow
The receptionist starts with:
1. check-in;
2. check-out;
3. guest count.
The backend returns only capacity-compatible, non-overlapping resources, sorted by base price/capacity/name.
The user chooses an option, then completes the stay record.

## Event workflow
The operator starts with the month, not a dense booking form.
The month is dual-calendar presentation and opens strict day/period availability.

## Interaction principles
- One dominant action per context.
- Progressive disclosure.
- Status color has semantic meaning, never decoration alone.
- Empty states explain the next action.
- Mobile/responsive layouts remain usable.
- Backend remains authoritative; UI never bypasses collision validation.

## Production gates still required
Static Python/XML checks are not an Odoo runtime installation.
Before production: install on a clean Odoo 13 DB, update module, run ORM tests, test assets/QWeb in browser, verify RTL on supported browsers, test concurrent booking with two transactions, and validate accounting flows.
