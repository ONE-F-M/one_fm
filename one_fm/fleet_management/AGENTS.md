# Fleet Management Module

Owner: Operations / Admin team
Path: `one_fm/one_fm/fleet_management/`

## Purpose

Manages company vehicle fleet: vehicle leasing contracts, lease vehicle records, vehicle types, and route optimization configuration.

## Key DocTypes

- **Vehicle Leasing Contract** / **Vehicle Leasing Contract Item** — leasing agreement records with contract terms, costs, and renewal dates
- **Lease Vehicle** / **Lease Vehicle Item** — individual leased vehicle records
- **Vehicle Type** — vehicle classification (sedan, SUV, bus, etc.)
- **Route Optimization API Configuration** — configuration for external route optimization service integration

## Key Business Rules

1. **Vehicle naming is auto-generated.** `vehicle_naming_series` in `fleet_management/utils.py` provides custom naming for Vehicle DocType (registered via doc_events hook in hooks.py).
2. **Vehicle creation from contracts.** `after_insert_vehicle` in `vehicle_leasing_contract.py` triggers post-creation logic when a new Vehicle is inserted.
3. **Vehicles link to Operations.** Vehicles may be assigned to Operations Sites for transport operations.

## Utilities

- `one_fm/fleet_management/utils.py` — vehicle naming series and helper functions

## Cross-Module Dependencies

- **hooks.py doc_events**: Vehicle `autoname` and `after_insert` hooks
- **operations/**: Vehicles may be linked to site transport

## Testing

```bash
bench run-tests --module one_fm.fleet_management
```
