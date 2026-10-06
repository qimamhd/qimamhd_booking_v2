# Milestone 6 — Visual Planners

## Hall planner
A custom Odoo 13 client action renders a calm monthly grid.
Each day shows:
- Gregorian day number;
- Hijri display label;
- available slot count or full/available state;
- booking count and temporary holds only when relevant.

Clicking a day opens the existing strict day/period availability workspace.
No availability rule is duplicated in JavaScript.

## Hotel planner
A custom room-by-day timeline renders:
- sticky room column;
- 14-day window;
- Gregorian day plus Hijri label;
- state-colored occupied cells;
- hover affordance on empty cells.

Click occupied -> open stay.
Click empty -> prefilled one-night stay.

The backend remains authoritative for overlap validation.

## Hijri rule
Hijri is presentation metadata, never a second editable booking date.
The current implementation uses deterministic civil/tabular Hijri conversion so it has no external dependency.
For Saudi official-calendar parity, a configurable Umm al-Qura provider can replace the presentation converter later without changing booking keys.

## Visual language
Green = free, amber = hold/partial pressure, blue = confirmed, soft green = checked-in, red = full/critical.
Whitespace and progressive disclosure are preferred over dense dashboards.

## Next hardening
- exact Umm al-Qura provider option;
- true continuous reservation bars spanning cells rather than repeated occupied cells;
- drag/resize only after permission and collision semantics are fully specified;
- business-mode-aware menu visibility.
