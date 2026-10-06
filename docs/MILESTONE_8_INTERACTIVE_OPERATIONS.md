# M8 — Interactive Operations

## Today Operations
A dedicated non-traditional workspace merges only today's actionable operational items:
- event bookings;
- arrivals;
- departures.
Accounting detail is intentionally excluded.

## Booking Drawer
A lightweight snapshot opens over the workspace/planner.
For hotel stays it supports context-safe primary actions:
- confirmed -> Check in;
- checked in -> Check out.
Full Odoo form remains available as a secondary action.

## Hotel continuous bars
The room timeline now has visual reservation spans across the visible day window.
The cells remain the click targets for creating a stay; bars open the booking snapshot.

## Safety
All writes still invoke model workflow methods. The client does not directly write state.
Availability remains enforced server-side.
