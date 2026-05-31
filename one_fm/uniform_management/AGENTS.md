# Uniform Management Module

Owner: GSD / Operations team
Path: `one_fm/one_fm/uniform_management/`

## Purpose

Manages employee uniform allocation, tracking, and expiry notifications. Links designations to uniform profiles and tracks individual employee uniform issuance.

## Key DocTypes

- **Designation Profile** / **Designation Profile Item** — defines which uniform items are required per designation (e.g., "Security Guard" requires boots, shirt, trousers, belt)
- **Employee Uniform** / **Employee Uniform Item** — tracks uniforms issued to individual employees, including sizes, quantities, and expiry dates

## Key Business Rules

1. **Designation drives uniform requirements.** Each `Designation Profile` maps a designation to a list of required uniform items.
2. **Expiry notifications.** `notify_gsd_and_employee_before_uniform_expiry` runs daily to alert GSD and the employee before uniforms expire.
3. **Uniforms link to purchase flow.** Uniform requests may trigger a `Request for Material` in the purchase module.

## Scheduler Events

| Schedule | Method | Purpose |
|---|---|---|
| Daily | `employee_uniform.notify_gsd_and_employee_before_uniform_expiry` | Expiry notifications |

## Reports & Print Formats

This module contains `report/` and `print_format/` subdirectories for uniform-related reporting and printing.

## Testing

```bash
bench run-tests --module one_fm.uniform_management
```
