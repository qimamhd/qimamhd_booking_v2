# QimamHD Booking V2 — Production Roadmap

## Product direction
A visually calm, premium hall-booking system. The first screen must show only what the employee needs now.
Complex operations belong in focused wizards/popups. Odoo remains the business-logic source of truth;
Flutter consumes stable API contracts.

## M0 — Architecture & safety
- One module: `qimamhd_booking_v2`.
- Separate Hall / Period / Package / Service / Booking concepts.
- Standard Odoo accounting.
- Server-side validation for every critical rule.
- Versioned `/api/v2/`.
- Migration strategy from both V1 modules.

## M1 — Booking Core
- Configurable periods (morning/afternoon/evening are data, not hardcoded logic).
- Multiple periods per booking.
- Optional times.
- Availability = company/branch scope + hall + date + period.
- Draft does not block; Hold/Confirmed/Preparing/Event/Completed block; Cancelled releases.
- Concurrency hardening before production.
- Hold expiration policy.

## M2 — Pricing & commercial rules
- Hall pricing.
- Packages and add-ons.
- Day/season pricing.
- Discount approvals.
- Odoo tax engine only.
- Confirmed-price snapshots.
- Capacity warnings/rules.

## M3 — Financial Lifecycle
Supported invoice policies:
1. Manual invoice — safest for businesses that need accounting review.
2. Full invoice on confirmation — simple and recommended for straightforward operations.
3. Deposit invoice + final invoice — recommended where deposits are legally/accountingly invoiced.
4. Installment/schedule invoices — for businesses requiring invoices by contractual milestones.

The policy is configurable; the UI shows only the relevant action.

Payment capabilities:
- Cash/bank/card journals from Odoo.
- Partial and full payment.
- Multiple payments.
- Deposit tracking.
- Due schedule.
- Refund/reversal flow.
- No dynamic creation of payment methods.
- No silent overpayment.
- Paid/remaining values reconciled to accounting documents.

## M4 — Reversal & cancellation safety
- Booking cancellation is a controlled wizard, not a state toggle.
- Draft invoice: may be cancelled/removed under permission.
- Posted invoice: requires credit note/reversal according to accounting policy.
- Paid invoice: payment/refund/reconciliation must be resolved before slot release when policy requires it.
- Reversing an invoice never automatically frees the hall.
- Cancelling a payment never automatically cancels a booking.
- Cancelling a booking never deletes posted accounting history.
- Reopening a cancelled booking must re-check availability.
- Every reversal stores actor, reason, timestamp and linked documents.

## M5 — Security & audit
Roles:
- Booking User
- Booking Supervisor
- Accountant
- Operations User
- Branch Manager
- System Manager

Audit:
hall/date/period/state/price/discount/invoice/refund/cancellation changes.

## M6 — Odoo UI/UX
Design language:
- visual breathing room;
- strong hierarchy;
- short forms;
- contextual actions;
- smart buttons for secondary information;
- wizards for complex operations;
- RTL-first review.

Main journeys:
- Quick booking popup.
- Availability board.
- Booking workspace.
- Financial wizard.
- Cancellation/reversal wizard.
- Today events.
- Operations.
- Reports/configuration.

## M7 — Availability Board
Rows = halls; columns = configured periods.
Statuses: Available / Hold / Confirmed / Operational Block.
Click available cell -> quick booking popup prefilled.
Click occupied cell -> booking preview/open subject to permission.

## M8 — Practical intelligence
Explainable assistance only:
- suggest alternate hall when occupied;
- suggest nearest available date/period;
- warn about missing deposit;
- readiness/risk alerts;
- customer-history insights;
- unusual discount/payment warnings;
- 30/60/90-day forecast.
No black-box automatic financial decisions.

## M9 — Operations
- checklist templates;
- booking checklist;
- responsible employee;
- event readiness score;
- delivery/return/damage records;
- today events.

## M10 — Reports
- daily/upcoming bookings;
- hall occupancy;
- revenue by hall/branch;
- collections/outstanding;
- cancellation reasons;
- discounts;
- service popularity;
- customer sources;
- employee performance;
- 30/60/90 forecast;
- Gregorian/Hijri analysis.

## M11 — API freeze before Flutter
- auth/access/refresh token design;
- customers;
- halls;
- periods;
- availability;
- packages/services;
- bookings;
- finance;
- operations;
- dashboard;
- reports;
- attachments.
Stable error codes, pagination and permission parity with Odoo UI.

## M12 — Migration
Rehearse V1 -> V2 on copied production DB.
Preserve contract number, customer, date, historical hall/service meaning,
amounts, invoices, payments and state.
Reconciliation report before/after + rollback plan.

## M13 — QA/UAT
Unit + integration + API + security + concurrency + migration + RTL + accounting reconciliation.
Flutter starts only after Odoo V2 and API contract pass UAT.
