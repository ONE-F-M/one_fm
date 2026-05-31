# Operations Module

Owner: Operations team
Path: `one_fm/one_fm/operations/`

## Purpose

Manages shift scheduling, attendance, site/post allocation, roster management, contracts, patrol routes, checkpoint scanning, cleaning operations, and field incident reporting. This is the largest and most complex module in the app.

## Key DocTypes

### Core Hierarchy

- **Operations Site** → top-level location (linked to Project)
- **Operations Shift** → a shift within a site (AM/PM/Night, linked to Shift Type)
- **Operations Post** → a physical post within a shift (guard position, reception desk, etc.)
- **Operations Role** → designation-like role specific to operations (e.g., "Security Guard", "Receptionist")

### Scheduling & Roster

- **Employee Schedule** — daily assignment of employee to post/shift, used by the Roster page
- **Post Schedule** — planned schedule for a post (how many staff, which roles)
- **Post Allocation Plan** / **Post Allocation Employee Assignment** — bulk assignment tooling
- **Post Scheduler Checker** — automated checker that validates roster completeness at 04:10 daily
- **Default Shift Checker** — verifies employees have a default shift assigned
- **Roster Day Off Checker** / **Roster Client Day Off Checker** — validates day-off compliance against contracts

### Attendance & Checkin

- **Employee Checkin Issue** — records checkin anomalies
- **Face Recognition Log** — biometric checkin results from gRPC facial recognition service
- **Checkin Radius Log** — geofence compliance log
- **Missing POC Attendance** — tracks missing point-of-contact attendance

### Contracts

- **Contracts** — master contract record linked to Project, Customer, and Operations Site. Controls invoicing, post count, shift config. Has auto-renewal logic (`auto_renew_contracts`) and termination-date-based renewal.
- **Contract Item** / **Contract Items Operation** — line items within a contract
- **Contract Addendum** — amendments to active contracts
- **Contract Asset** — assets assigned to a contract
- **Contract Compliance Checker** — validates contract terms are met

### Patrol & Checkpoints

- **Checkpoints** — physical checkpoint locations for guard tours
- **Checkpoints Assignment** / **Checkpoints Route Assignment** — route planning for patrols
- **Checkpoint Assignment Scan** — QR scan records during patrols
- **Patrol Routes** / **Route Plan** / **Route Plan Assignment** — patrol route definitions

### Cleaning Operations

- **Cleaning SOP** — standard operating procedures for cleaning
- **Cleaning Objects** / **Cleaning Spaces** / **Cleaning Tools** / **Cleaning Consumables** — cleaning resource master data
- **Cleaning Master Tasks** — task definitions for cleaning operations

### Incidents & Reports

- **Incident Form** — field incident reports
- **Shift Report** — end-of-shift supervisor report
- **MOM** (Minutes of Meeting) / **MOM Followup** / **MOM Action** — meeting minutes with automatic followup reminders (weekly penalty for non-compliance)

### Other

- **Shift Permission** — employee permission to arrive late or leave early
- **Operations Post Activation** — activating/deactivating posts
- **Change Request** / **Operations Changes** — workflow for operational changes
- **Additional Deployment** / **Temporary Post** — ad-hoc staffing

## Key Business Rules

1. **Roster must be complete before shifts start.** The `Post Scheduler Checker` runs at 04:10 daily to flag unfilled posts.
2. **Contracts drive post count.** Changing a contract's headcount must cascade to Operations Post and Employee Schedule.
3. **Day-off rules are contract-driven.** The `Roster Client Day Off Checker` validates that scheduled day-offs match what the client contract allows.
4. **Attendance is marked automatically** at 12:45 PM daily (`mark_all_attendance` in overrides). Manual attendance correction goes through `Attendance Request`.
5. **MOM followups auto-escalate.** `mom_followup_reminder` runs daily; `mom_followup_penalty` runs weekly.
6. **Process Tasks** can be scheduled via cron expressions or monthly-on-day patterns, creating Tasks automatically.

## Scheduler Events (Cron)

| Schedule | Method | Purpose |
|---|---|---|
| `10 4 * * *` | `schedule_roster_checker` | Creates Post Scheduler Checker |
| `10 4 * * *` | `create_default_shift_checker` | Validates default shifts |
| `30 13 * * *` | `roster_day_off_checker.generate_checker` | Validates day-offs |
| `30 4 * * *` | `check_roster_client_day_off` | Client day-off compliance |
| Daily | `auto_renew_contracts` | Auto-renew expiring contracts |
| Daily | `send_contract_reminders` | Notify about upcoming expirations |
| Daily | `renew_contracts_by_termination_date` | Renew by termination date |
| Weekly | `mom_sites_followup` / `mom_followup_penalty` | MOM escalation |
| `* * * * *` | `create_task_on_cron_process_task` | Runs every minute for process tasks |

## Testing

```bash
bench run-tests --module one_fm.operations
```

Tests are in individual doctype directories (e.g., `operations/doctype/contracts/test_contracts.py`). Also see `one_fm/tests/` for integration tests involving operations logic (shift assignment, overtime).

## Cross-Module Dependencies

- **overrides/**: `attendance.py`, `shift_request.py`, `shift_assignment.py`, `employee_checkin.py`, `shift_type.py` heavily customize standard HRMS behavior
- **api/tasks.py**: Runs shift assignment (`assign_am_shift`, `assign_pm_shift`), attendance processing, penalty generation, overtime handling
- **one_fm/one_fm/**: Contains `Employee Schedule`, `Roster Post Actions`, `Roster Employee Actions` core DocTypes
- **legal/**: Penalty issuance for attendance/operations violations
- **grd/**: Work permit status affects employee scheduling eligibility
