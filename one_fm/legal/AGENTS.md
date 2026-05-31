# Legal Module

Owner: Legal / HR team
Path: `one_fm/one_fm/legal/`

## Purpose

Manages employee penalties, legal investigations, and disciplinary actions. Handles the full penalty lifecycle from issuance through investigation to deduction from salary.

## Key DocTypes

### Penalties

- **Penalty** — individual penalty record against an employee. Has custom permission query conditions and has_permission hooks for access control.
- **Penalty Issuance** / **Penalty Issuance Details** / **Penalty Issuance Employees** — bulk penalty issuance tool
- **Penalty Code** — penalty code definitions (mapped to labor law articles)
- **Penalty Type** — classification of penalties
- **Penalty Level** — severity levels (warning, deduction, suspension, termination)
- **Penalty List** — reference list of available penalties
- **Penalty Details** — child table for penalty specifics
- **Penalty and Investigation** — linking penalties to investigations
- **Penalty Deduction** / **Penalty Deduction Details** / **Penalty Deduction Schedules** — salary deduction records for penalties

### Investigations

- **Legal Investigation** / **Legal Investigation Employees** — formal investigation records
- **Legal Investigation Session** / **Legal Investigation Sessions** / **Legal Investigation Session Employees** — hearing/session tracking
- **Legal Investigation Penalty** — penalties resulting from investigations

### Configuration

- **Legal Settings** — module-wide configuration
- **Employee ID** — employee identification records for legal purposes

## Key Business Rules

1. **Automatic rejection.** `penalty.automatic_reject` runs every 15 minutes to auto-reject stale penalty records.
2. **Permission isolation.** Penalties use custom `permission_query_conditions` and `has_permission` hooks — only authorized users can see/modify penalties.
3. **Penalty issuance generates penalties** at 23:37 daily via `issue_penalties` in `api/tasks.py`. Monthly penalty generation runs on the 24th at 00:08.
4. **Deductions link to payroll.** `Penalty Deduction` records feed into salary slip processing.
5. **Investigation sessions are sequenced.** Each session builds on previous findings before determining the penalty outcome.

## Scheduler Events

| Schedule | Method | Purpose |
|---|---|---|
| Every 15 min | `penalty.automatic_reject` | Auto-reject stale penalties |
| `37 23 * * *` | `api.tasks.issue_penalties` | Daily penalty issuance |
| `08 00 24 * *` | `api.tasks.generate_penalties` | Monthly penalty generation |

## Cross-Module Dependencies

- **operations/**: Attendance violations and operational non-compliance trigger penalties
- **api/tasks.py**: Penalty generation and issuance logic
- **overrides/salary_slip.py**: Penalty deductions applied during payroll
- **hooks.py**: Custom permission hooks for Penalty and Penalty Issuance

## Testing

```bash
bench run-tests --module one_fm.legal
```
