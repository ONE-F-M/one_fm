# GRD Module (Government Relations Department)

Owner: GRD team
Path: `one_fm/one_fm/grd/`

## Purpose

Manages all government-relations workflows required to employ staff in Kuwait: work permits, residency (MOI), PACI (civil ID), medical insurance, PIFSS (social security), PAM (Public Authority for Manpower) compliance, and MGRP (manpower government relations processes).

## Key DocTypes

### Work Permits

- **Work Permit** — tracks work permit lifecycle (new application, renewal, transfer). Has automated daily reminders for GRD operators.
- **Work Permit Document** / **Work Permit Required Documents** / **Work Permit Required Documents Template** — document checklists per work permit type
- **Transfer Work Permit** — transferring work permits between employers

### Residency (MOI)

- **Residency** — Ministry of Interior residency permit tracking. Daily reminders for renewals/transfers.
- **Residency Payment Request** / **Residency Payment Request Reference** — payment tracking for residency fees

### PACI (Public Authority for Civil Information)

- **PACI** — civil ID tracking with Hawiyati renewal/transfer notifications
- **PACI Number** — PACI number records

### Medical Insurance

- **Medical Insurance** / **Medical Insurance Item** — employee health insurance management
- **Medical Appointment** — scheduling medical appointments for employees
- **Health Insurance Provider Detail** — insurance provider configuration

### PIFSS (Public Institution for Social Security)

- **PIFSS Settings** / **PIFSS Settings Users** — PIFSS configuration
- **PIFSS Authorized Signatory** — authorized signatories for PIFSS forms
- **PIFSS Form 103** — employee registration/deregistration form
- **PIFSS Form 55** / **Form 55 Employees** — annual salary declaration
- **PIFSS Monthly Deduction** / **PIFSS Monthly Deduction Employees** — monthly social security deductions
- **PIFSS Monthly Deduction Tool** — bulk deduction processing tool
- **Public Institution for Social Security** — PIFSS master record

### PAM (Public Authority for Manpower)

- **PAM File** / **PAM File Table** — PAM file number tracking
- **PAM Authorized Signatory Setting** / **PAM Authorized Signatory List** / **PAM Authorized Signatory Table** — authorized signatories
- **PAM Salary Certificate** / **PAM Salary Certificate Setting** — salary certificates for PAM
- **PAM Designation List** — designation mappings for PAM compliance

### Other

- **GRD Settings** — module-wide configuration
- **GRD Renewal Extension Cost** — cost tracking for renewals
- **Preparation** / **Preparation Record** — document preparation workflows
- **Article of Association** / **Changes of Article of Association** — company legal documents
- **MOCI License** — Ministry of Commerce license tracking
- **MGRP** — manpower government relations process tracking
- **Fingerprint Appointment** / **Fingerprint Appointment Settings** — biometric appointment scheduling
- **Agency Country Process Template** — country-specific hiring process templates
- **Children Details Table** — dependent information for visa/residency

## Key Business Rules

1. **GRD processes are employee-linked.** Every GRD document links to an Employee record. Check employee status before modifying GRD documents.
2. **Renewal reminders are automated.** Multiple daily/weekly cron jobs notify GRD operators about upcoming expirations for work permits, residency, PACI, and medical insurance.
3. **PIFSS monthly deductions auto-create.** `auto_create_pifss_monthly_deduction_record` runs on the 1st of each month at 04:15.
4. **Hawiyati (PACI smart card) notifications** are separate from PACI renewal — dedicated handlers for Hawiyati renewal and transfer.
5. **Document flow:** Hiring → Work Permit → Residency → PACI → Medical Insurance. Each step may depend on the previous.
6. **PAM file numbers and designations** must be validated against PAM's official designation list.

## Utilities

- `one_fm/grd/utils.py` — helper functions including:
  - `sendmail_reminder_to_book_appointment_for_pifss`
  - `sendmail_reminder_to_collect_pifss_documents`

## Scheduler Events (Cron)

| Schedule | Method | Purpose |
|---|---|---|
| `40 5 * * 0-4` | Work permit/MI/Residency/PACI renewal reminders | Working-day reminders (Sun–Thu) |
| `15 4 1 * *` | `auto_create_pifss_monthly_deduction_record` | Monthly PIFSS deduction |
| `15 6 * * *` | Multiple GRD notifications | Fingerprint appts, PIFSS form 103, MGRP |

## Cross-Module Dependencies

- **hiring/**: GRD processes are triggered post-Job Offer acceptance
- **one_fm/one_fm/**: Contains `PAM Visa`, `PAM Visa Setting` DocTypes
- **paci/**: Separate PACI signature management module
- **overrides/employee.py**: Employee record links to GRD documents

## Testing

```bash
bench run-tests --module one_fm.grd
```
