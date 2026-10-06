# M19 — Hotel Financial Lifecycle

Hotel stays now have an accounting lifecycle independent from event-period bookings while using Odoo Accounting as the source of truth.

## Contract
- Stay price snapshot: nightly price + stay tax snapshot.
- Official total uses `account.tax.compute_all()`.
- Draft and posted invoices reserve invoice capacity.
- Advisory lock per stay serializes invoice-capacity decisions.
- Full, deposit, and remaining/final invoices are supported.
- Posted invoices and credit notes drive invoiced/credited/paid/due/progress values.
- Standard `account.move.reversal` creates credit notes/reversal behavior.
- Cancellation never deletes posted accounting documents.
- Draft invoices can only be cancelled through the controlled cancellation wizard.
- Reopening a cancelled stay requires no unresolved net posted financial exposure and rechecks room availability under the resource lock before changing state.
- Invoice/payment reversal does not release the room. Stay state remains the availability authority.

## Confirmation policy
The existing company financial policy is applied consistently to Events and Stays: manual, posted invoice required, or paid deposit required. Invoices may now be prepared while Draft/Hold so invoice/deposit policies do not deadlock confirmation. This also fixes the equivalent event-flow deadlock.

## Branches
Operational scope remains `custom.branches`. If `account.move` exposes `branch_id` through the installed branch module, generated stay invoices/refunds inherit the stay branch.

## Remaining runtime gate
Real Odoo 13 tests are mandatory for `account.move.reversal`, `button_cancel`, reconciliation/refunds, price-included taxes, rounding, concurrent invoice creation, and branch propagation.
