# Booking / Invoice / Payment Lifecycle

## Principle
Booking, Invoice and Payment have independent states. No document silently destroys or rewrites the state
of another domain. Cross-domain actions are explicit, permissioned and auditable.

## Invoice policy options
### Manual
User chooses when to invoice. Best during early rollout and for businesses requiring accountant review.

### Full on confirmation
One invoice for the confirmed contract. Operationally simple and a strong default where business policy permits.

### Deposit + final
Deposit invoice at booking milestone, final invoice for remaining contractual value.
Must prevent duplicate invoicing and reconcile deposit treatment correctly.

### Schedule
Invoices generated from approved payment milestones. Best for formal installment contracts but requires the
strongest controls.

## Cancellation matrix
| Booking situation | Allowed booking action | Financial requirement |
|---|---|---|
| Draft, no invoice/payment | Cancel | None |
| Hold, no invoice/payment | Cancel and release slot | None |
| Draft invoice only | Cancel booking after draft invoice handling | Cancel/delete draft under permission |
| Posted unpaid invoice | Do not silently release | Credit note/reversal workflow |
| Partially paid | Financial review | Reverse invoice as required + refund/reconcile payment |
| Fully paid | Financial review | Approved refund/credit/reconciliation |
| Invoice reversed but booking active | Booking stays active | User must explicitly cancel booking |
| Payment reversed but booking active | Booking stays active | Recalculate financial status and warn |

## Reopen rules
A cancelled booking can only be reopened through a dedicated action that re-checks:
- hall availability;
- date;
- every period;
- financial document state;
- permissions.

## Non-negotiable safeguards
- Never delete posted accounting history from booking actions.
- Never free availability solely because an invoice was reversed.
- Never cancel an invoice solely because a booking was cancelled.
- Never create a payment method dynamically.
- Never calculate official paid amount from custom payment rows when Odoo accounting is the source of truth.
- Every sensitive reversal requires a reason.
