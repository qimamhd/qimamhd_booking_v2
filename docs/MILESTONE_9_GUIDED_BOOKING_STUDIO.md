# M9 — Guided Booking Studio

The primary booking creation path is no longer a traditional Odoo form.

## Flow
1. Customer
2. Need/date
3. Availability choice
4. Visual review
5. Success

Event and hotel flows remain distinct.

### Event
Customer -> date + hall + periods -> server availability quote -> review -> create.

### Hotel
Customer -> check-in/out + guests -> server filters non-overlapping capacity-compatible resources -> choose room -> review -> create.

## Safety
- Availability is checked while quoting and again when creating.
- Final creation calls canonical ORM models, so model constraints remain authoritative.
- UI never writes booking state directly.
- A successful create returns the canonical record id/name.
- Existing M8 planners/operations remain intact.

## Deliberate omissions
Packages/services/tax/deposit are not faked into the Studio yet. They will be added only through canonical backend pricing/accounting helpers, so the visual flow never becomes a second pricing engine.
