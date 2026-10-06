# M10 — Commercial Booking Experience

## Commercial Configurator
Event bookings now continue into a dedicated visual configurator after the canonical booking record is created:
- packages;
- optional services;
- live contract summary;
- discount;
- Odoo tax calculation;
- final total.

The browser never implements tax math. `qimam.booking.commercial.service` performs the quote using `account.tax.compute_all`.

## Snapshot rule
When commercial configuration is applied, service price/tax values are copied into booking service lines. Future master-data price changes do not rewrite the signed booking economics.

## Invoice capacity hardening
Previous logic considered only posted invoices when deciding remaining invoice percentage. That allowed multiple draft invoices to reserve the same capacity.

M10 separates:
- `_net_invoiced_factor()` = posted economic/reporting exposure.
- `_reserved_invoice_factor()` = active draft + posted customer invoices minus posted credits.
- `_lock_financial_capacity()` = transaction advisory lock before invoice creation.

The invoice wizard now calculates and creates against reserved capacity under the booking-specific lock.

## Important production validation
This is source/static validation. Before production, test draft/post/cancel/credit-note combinations in a real Odoo 13 database, including two concurrent invoice-creation transactions.
