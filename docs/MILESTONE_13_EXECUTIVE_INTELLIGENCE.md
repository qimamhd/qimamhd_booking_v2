# M13 — Executive Intelligence

## Goal
A decision surface, not a collection of standard Odoo reports.

## Period intelligence
The dashboard accepts 7/30/90 day presets or a custom range. The backend automatically compares the selected period with the immediately preceding period of equal length.

## KPIs
- booking count
- confirmed booking value
- hall-period occupancy
- cancellation rate
- hold-to-confirmed operational conversion
- scheduled overdue amount

All calculations are company-scoped.

## Forecast
30/60/90 day forward view includes only bookings currently in confirmed/preparing/event states. It is a pipeline forecast, not recognized accounting revenue.

## Rankings
Top halls and services are derived from canonical booking and booking service lines. No browser-side business calculation is used.

## Drill-down
Bookings, confirmed value, cancellations, holds, and overdue attention can open the canonical booking records behind the number.

## Financial interpretation
Dashboard booking value is an operational/commercial KPI. Official financial statements remain in Odoo Accounting.

## Production gate
M13 passes static source validation only. Real Odoo 13 runtime/UAT and performance testing with production-sized data remain required.
