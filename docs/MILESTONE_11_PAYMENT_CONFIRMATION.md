# M11 — Payment & Confirmation Experience

## Purpose
The booking journey now has a dedicated financial closing workspace instead of mixing accounting details into the booking form.

## Confirmation policies
Company-level policy:
- Manual approval
- Posted customer invoice required
- Paid deposit required

Deposit policy uses the booking's accounting-derived `amount_paid`; a planned schedule never pretends to be payment.

## Financial snapshot
The workspace displays:
- contract total
- actual paid amount
- actual invoice residual
- invoice progress
- required deposit
- next due date
- overdue scheduled amount
- payment schedule timeline

## Payment schedule
Schedules are planning metadata only. They allocate the accounting-derived paid amount sequentially for presentation. Rebuilding a schedule does not create a payment.

## Confirmation
The UI calls the canonical `qimam.booking.action_confirm()`. The model itself enforces the configured financial gate, so confirmation cannot be bypassed through this client action.

## Existing M10 invoice hardening remains
Draft and posted invoices reserve invoice capacity. Invoice creation is protected by a booking-specific PostgreSQL transaction advisory lock.

## Production gate
Real Odoo 13 UAT is still required for reconciliation behavior, invoice/payment state transitions, JS/QWeb runtime, and concurrent invoice creation.
