# M21 — On-demand Integrated Demo Dataset

No demo data is loaded during module installation.

A Booking Manager opens Odoo Settings > Booking, selects an allowed `custom.branches` branch and presses **إنشاء نسخة ديمو متكاملة**.

The builder is idempotent per company + branch and never deletes/replaces real customer data. It creates realistic Saudi-style sample customers and a connected catalog: 3 periods, 3 halls, 5 services, package, room/suite types and 4 stay resources.

Event scenarios cover draft, hold, confirmed, preparing, live event, completed, cancelled, full-day/all-period booking, add-ons, package and discount. Stay scenarios cover draft, hold, confirmed, checked-in, checked-out and cancelled. A readiness checklist demonstrates done/progress/todo/blocking operations.

Accounting documents are deliberately not force-posted by the demo builder. Posting invoices/payments must exercise the normal Odoo accounting workflow so demo generation cannot manufacture fake posted accounting entries. The existing booking/stay financial wizards are used interactively to demonstrate invoice/deposit/payment/refund paths.
