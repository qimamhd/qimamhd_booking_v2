# M15 Branch Architecture Correction

The legacy booking system was inspected directly before this change.

Confirmed legacy contract:
- dependency: `custom_branch_13`
- branch model: `custom.branches`
- current branch: `user.branch_id`
- allowed branches: `user.allowed_branch_ids`
- legacy booking (`hotel.master`) stored `branch_id`
- legacy record rule filtered bookings by allowed branches.

V2 now follows that operational boundary.

`company_id` is retained where Odoo accounting/currency requires it, but availability, booking visibility, resources, event/hotel operations, executive reporting, and API scope use `branch_id`.

Both booking domains are branch-scoped:
- Events: branch + hall + date + periods
- Stays: branch + resource + [checkin, checkout)

The API validates requested branch server-side and rejects branches outside `allowed_branch_ids`.
