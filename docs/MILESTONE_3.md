# Milestone 3 — Dues, Reversal, Reopen & Hold Expiry

## Payment schedule
Two guided schedule modes:
- Deposit + final balance.
- Equal installments.

The schedule does not invent payments. Actual paid/due amounts remain derived from posted Odoo accounting documents.

## Due intelligence
Booking shows only a compact summary:
- next due date;
- overdue amount;
- paid;
- due.
Detailed installments live behind a smart button.

## Financial reversal
Accountants get a focused wizard based on Odoo 13 `account.move.reversal`.
It creates the standard credit-note/reversal documents and links them back to the booking.
Financial reversal never releases the hall automatically.

## Cancellation safety
Posted documents continue to block booking cancellation.
The accountant resolves credit/refund/reconciliation first; the booking supervisor then performs the explicit cancellation.

## Reopening
Cancelled bookings have an explicit Reopen action.
Reopening checks whether another booking has occupied the original hall/date/period.
Posted accounting documents also block reopen until resolved.

## Temporary hold expiry
A scheduled job checks expired holds every 15 minutes.
A clean hold is cancelled and the slot is released.
If posted accounting documents exist, the system does not silently release the slot and records a chatter warning.

## UX decision
No payment table is dumped into the booking's first viewport.
Financial details are progressively disclosed through smart buttons and focused popups.
