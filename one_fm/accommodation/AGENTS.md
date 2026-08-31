# Accommodation Module

Owner: Admin / Accommodation team
Path: `one_fm/one_fm/accommodation/`

## Purpose

Manages employee housing: buildings, units, floors, spaces (rooms), beds, occupancy tracking, check-in/check-out, inspections, meter readings, asset distribution, and leave movement for accommodated employees.

## Key DocTypes

### Hierarchy

- **Accommodation** → top-level building/property (linked to Contact)
- **Accommodation Unit** → a unit within a building (apartment, villa)
- **Floor** → floor within a building
- **Accommodation Space** → a room or space within a unit
- **Bed** → individual bed within a space
- **Accommodation Space Bed** — child table linking beds to spaces

### Types & Configuration

- **Accommodation Type** — property type classification (company-owned, rented, etc.)
- **Accommodation Space Type** / **Accommodation Unit Space Type** / **Bed Space Type** — configuration for space and bed types

### Occupancy Management

- **Book Bed** / **Bulk Book Bed** — assign employees to beds (single and bulk)
- **Available Bed** — tracks bed availability
- **Accommodation Checkin Checkout** — employee move-in/move-out tracking
- **Accommodation Leave Movement** — tracks employees on leave from accommodation
- **Nearest Accommodation** — finds nearest accommodation for an employee

### Assets & Consumables

- **Accommodation Asset** — assets within accommodation (furniture, appliances)
- **Accommodation Asset and Consumable** — combined asset/consumable tracking
- **Accommodation Distribution Asset** / **Accommodation Distribution Consumable** — distribution records
- **Accommodation Receiving Form** — receiving goods into accommodation

### Inspections & Maintenance

- **Accommodation Inspection** / **Accommodation Inspection Reading** — periodic inspections
- **Accommodation Inspection Parameter** / **Accommodation Inspection Template** — inspection criteria
- **Accommodation Building Condition** — building condition assessments
- **Accommodation Meter** / **Accommodation Meter Reading** / **Accommodation Meter Reading Record** — utility meter tracking

### Other

- **Accommodation Object** / **Accommodation Space Object** — objects/items within spaces

## Key Business Rules

1. **Bed capacity is enforced.** Booking a bed checks space capacity before allowing assignment.
2. **Checkin/checkout tracks occupancy.** Every employee move creates an `Accommodation Checkin Checkout` record.
3. **Contact syncing.** When a Contact is updated, `accommodation_contact_update` (via doc_events hook) syncs the data to linked accommodation records.
4. **Monthly utility processing.** `execute_monthly` in `accommodation/utils.py` runs as a monthly scheduler event.
5. **Accommodation links to Employee.** Employees have accommodation-related custom fields that link to Bed/Space records.

## Utilities

- `one_fm/accommodation/utils.py` — monthly execution hook and helper functions

## Scheduler Events

| Schedule | Method | Purpose |
|---|---|---|
| Monthly | `accommodation.utils.execute_monthly` | Monthly utility processing |

## Cross-Module Dependencies

- **hooks.py doc_events**: Contact `on_update` and `validate` hooks sync accommodation data
- **one_fm/one_fm/**: Some accommodation-related DocTypes may exist in the core module

## Testing

```bash
bench run-tests --module one_fm.accommodation
```
