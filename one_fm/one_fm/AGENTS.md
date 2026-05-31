# Core One FM Module

Owner: Development team
Path: `one_fm/one_fm/one_fm/`

## Purpose

The core module containing shared DocTypes that don't fit neatly into a single business domain. This is the largest DocType collection in the app (~170+ DocTypes) spanning HR, operations, procurement, GRD, and general-purpose functionality.

## Major DocType Groups

### HR & Employee Management
- **Employee Schedule** / **Request Employee Schedule** / **Request Employee Assignment** — daily roster schedule assignments
- **Overtime Request** — overtime hour requests
- **Indemnity Allocation** — end-of-service indemnity tracking (daily allocation via scheduler)
- **Leave Acknowledgement Form** — leave acknowledgement workflow (auto-generated at 02:00 daily)
- **Missing Checkin** — tracks missing checkin records (created hourly)
- **Attendance Check** — pending attendance approval checker (runs at 13:15 daily)
- **Reliever Assignment** / **Reliever Assignment Document** / **Reliever Assignment Settings** — document reassignment when employees are on leave
- **Employee Separation** — custom termination/exit workflow

### Operations & Roster
- **Roster Post Actions** / **Roster Employee Actions** — daily roster action items (created at 06:15 daily)
- **Roster Daily Report** — daily roster summary
- **Post Daily Report** — per-post daily report
- **Temporary Deployment** / **Temporary Deployment Item** — ad-hoc deployments
- **Operations Settings** / **ONEFM General Setting** — operations configuration

### Recruitment & Hiring (Shared)
- **Project Manpower Request** (PMR) / **PMR Fulfilled Employee** / **PMR Fulfillment Action** / **PMR Linked Candidate** / **PMR Resignation Link** — manpower requisition system
- **Client Interview Shortlist** — client-facing interview shortlist
- **Candidate Rating** / **Rating Scale** — candidate evaluation
- **Agency** — recruitment agency management
- **Recruitment Document** / **Recruitment Document Checklist** — document collection tracking

### Procurement (Shared)
- **Purchase Request** / **Purchase Request Item** — internal purchase requests
- **Supplier Purchase Order** / **Supplier Purchase Order Item** — supplier-facing POs
- **Request for Supplier Quotation** — RFQ to suppliers
- **Customer Asset** — assets owned by customers
- **Transit Log** / **Transit Item** — goods-in-transit tracking (syncs every 12 hours)
- **Stock Check** / **Stock Document** — stock verification

### GRD & Compliance (Shared)
- **PAM Visa** / **PAM Visa Setting** — visa processing through PAM
- **Visa Stamping** / **Visa Type** — visa types and stamping
- **Overseas Medical Appointment WAFID** / **Overseas Remedical** — overseas medical processes
- **PCC Clearance** — police clearance certificates
- **Social Security** — social security records
- **Residency Expiry Notification Digest** — residency expiry batch notifications

### Project & Task Management
- **Process Roadmap** / **Processes** / **Process Change Request** / **Process Doctype** / **Process Role** — business process management
- **Process Artefact Checklist** — checklist items for processes
- **Task Assignment** — custom task assignment beyond standard ToDo
- **Google Sheet Data Export** — automated Google Sheets sync (every 15 minutes)

### Other
- **Twilio Setting** — Twilio SMS/voice integration
- **User App Service** — mobile app service configuration
- **Password Reset Token** — custom password reset with token expiry (revoked every 5 minutes)
- **Pathfinder Log** — HD Ticket routing/pathfinder audit trail
- **Training Evaluation Form** / **Training Program Certificate** — training management
- **WhatsApp Questionnaire** — WhatsApp-based surveys
- **Website Info** / **Our Mission** / **Our Vision** — company website content

## Key Business Rules

1. **Employee Schedule is the roster backbone.** Created monthly (1st of month at midnight) via `create_employee_schedule`.
2. **Indemnity allocates daily.** `allocate_daily_indemnity` runs daily to accrue end-of-service benefits.
3. **Transit logs sync externally.** `sync_transit_log_status` runs every 12 hours to update courier tracking.
4. **Google Sheet exports are real-time.** `update_google_sheet_daily` runs every 15 minutes.

## Scheduler Events (Key)

| Schedule | Method | Purpose |
|---|---|---|
| Daily | `daily_indemnity_allocation_builder` + `allocate_daily_indemnity` | Indemnity accrual |
| `00 2 * * *` | `generate_leave_acknowledgement` | Leave acknowledgement forms |
| `0 * * * *` | `create_missing_checkin_record` | Missing checkin records |
| `*/15 * * * *` | `update_google_sheet_daily` | Google Sheets sync |
| `0/5 * * * *` | `revoke_password_tokens` | Token cleanup |
| `0 */12 * * *` | `sync_transit_log_status` | Transit log sync |
| `15 6 * * *` | `roster_post_actions.create` + `roster_employee_actions.create` | Daily roster actions |

## Testing

```bash
bench run-tests --module one_fm.one_fm
```

Note: Many tests for DocTypes in this module are in `one_fm/tests/` rather than inline.
