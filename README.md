# QimamHD Booking V2

Odoo 13 wedding/event hall booking platform.

## Foundation included in this milestone
- One clean Odoo module.
- Configurable halls and booking periods.
- Availability key: **Company + Hall + Date + Period**.
- Multiple periods per booking.
- Optional operational start/end time.
- Backend double-booking validation.
- Quick Booking popup to keep the main UI light.
- Clean booking form with progressive disclosure.
- Odoo standard invoice linkage.
- Configurable invoice policy foundation.
- Cancellation wizard that refuses to silently release a slot while posted invoices exist.
- API V2 foundation for halls, periods, availability and booking creation.
- Security groups and company isolation.
- Automated availability tests.
- Full roadmap and financial lifecycle specification under `docs/`.

## Important
This is the V2 foundation milestone, not the production-complete release.
Accounting reversal/refund automation, payment schedules, dashboard, availability matrix UI,
operations/checklists, reports, migration scripts and Flutter token authentication are intentionally
gated for later milestones after this core is installed and tested.


## Milestone 2 added
- Transaction-safe availability locking.
- Contract price/tax snapshots.
- Financial status summary.
- Full/deposit/final invoice wizard.
- Safer cancellation behavior around accounting documents.
