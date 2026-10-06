# Milestone 2 — Availability Safety + Financial Lifecycle

Implemented in this ZIP:

## Availability hardening
- PostgreSQL transaction advisory lock per company + hall + date.
- Conflict check remains period-aware.
- This serializes simultaneous confirmation attempts for the same hall/day and prevents the normal ORM race.
- Direct backend state changes still pass the same integrity validation.

## Contract price snapshot
- Hall price and hall taxes are copied into the booking.
- Later edits to the hall master do not silently rewrite old contracts.
- Service lines already carry their own price/tax snapshot.
- Booking discount is distributed proportionally across contract lines so tax is recomputed on the discounted base.

## Financial status
Booking now exposes:
- total invoiced;
- total credited;
- paid;
- due;
- invoicing progress;
- human financial status.

Accounting remains the source of truth.

## Invoice wizard
The booking form no longer creates an invoice immediately.
A focused popup supports:
- full remaining contract;
- deposit percentage;
- final remaining invoice.

Every generated invoice is a draft for accountant review.
The invoice stores its contract factor so V2 can safely know how much of the contract has been invoiced.

## Cancellation
- Draft invoices may be cancelled explicitly by the cancellation wizard.
- Any posted accounting document blocks booking cancellation.
- The slot is not released until accounting reversal/refund/reconciliation is handled.
- Reversing an invoice never auto-cancels the booking.
- Cancelling a payment never auto-cancels the booking.

## Still gated before production
- Automated credit-note helper with explicit accountant permissions.
- Payment schedule model and due reminders.
- Payment smart navigation/reconciliation detail.
- Expired-hold cron.
- Full database-level stress test with two concurrent cursors.
- Availability Board UI.
