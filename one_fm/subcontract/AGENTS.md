# Subcontract Module

Owner: Operations / HR team
Path: `one_fm/one_fm/subcontract/`

## Purpose

Manages subcontractor staff lifecycle: staff requests, shortlisting, onboarding, and attendance tracking for third-party contracted employees.

## Key DocTypes

- **Subcontract Staff Request** — request for subcontractor staff to fill operational positions
- **Subcontract Staff Shortlist** / **Subcontract Staff Shortlist Detail** — shortlisted candidates from subcontractor companies
- **Onboard Subcontract Employee** — onboarding workflow for subcontractor staff

## Related DocTypes (in `one_fm/one_fm/`)

These DocTypes live in the core module but are part of the subcontract domain:
- **Subcontract Staff Attendance** / **Subcontractor Staff Attendance Item** — attendance records for subcontractor employees
- **Subcontractor Contracts** / **Subcontractor Items** — subcontractor company contracts
- **Subcontractor Exit** / **Subcontractor Exit Items** — offboarding subcontractor staff

## Key Business Rules

1. **Subcontractors have portal access.** The `Subcontractor` role grants portal access for attendance submission via `/subcontractor-attendance` route.
2. **Attendance is separate.** Subcontractor attendance uses `Subcontract Staff Attendance`, not the standard HRMS Attendance DocType.
3. **Staff requests flow to shortlisting.** A `Subcontract Staff Request` leads to `Subcontract Staff Shortlist`, then `Onboard Subcontract Employee`.

## Cross-Module Dependencies

- **hooks.py**: Portal menu item for subcontractor attendance
- **one_fm/one_fm/**: Core subcontractor DocTypes (contracts, attendance, exit)
- **operations/**: Subcontractor staff may be assigned to Operations Posts

## Testing

```bash
bench run-tests --module one_fm.subcontract
```
