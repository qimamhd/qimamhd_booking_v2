# M16 — V1 → V2 Migration Foundation

## Safety rules
- V1 is read-only to the migration process.
- Dry Run is available per branch.
- Migration is idempotent through `qimam.booking.migration.map`.
- Every successful/blocked/error record has a traceable legacy ID.
- Operational scope is `custom.branches`.
- No legacy record is silently converted from Events to Stays.

## Event mapping
Legacy `hotel.master` is treated as the legacy hall/event contract.
- partner → partner
- branch → same `custom.branches`
- company → accounting metadata
- start date → event date
- department → branch-scoped V2 hall
- department price → hall contract price snapshot
- legacy lifecycle → draft/confirmed/completed/cancelled
- original contract number is preserved where available.

V1 did not have the new canonical period occupancy model. Imported single-day legacy bookings therefore use a dedicated branch period `legacy_full_day`. This is deliberately conservative: historical bookings block the imported day instead of pretending to know morning/evening allocation.

## Multi-day legacy events
They are BLOCKED for explicit review. They are **not** automatically converted into hotel stays. This prevents corrupting the two-domain architecture.

## Accounting
This milestone does not duplicate posted invoices or payments. Existing V1 accounting documents must be linked/mapped in a dedicated accounting migration pass after their exact legacy relationships are verified in a real database. Creating duplicate accounting documents would be unsafe.

## Hotel migration
No hotel V1 source model has been assumed. Stay migration starts only when an explicit legacy hotel source/mapping exists.

## Release gate
Before production migration:
1. clone production DB;
2. install/update V2;
3. run Dry Run per branch;
4. resolve blocked rows;
5. run migration;
6. reconcile counts/totals/contracts by branch;
7. verify accounting links;
8. UAT before cutover.
