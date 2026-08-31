# Hiring Module

Owner: HR / Recruitment team
Path: `one_fm/one_fm/hiring/`

## Purpose

Manages the full recruitment pipeline: Employee Requisition Form (ERF) → Job Opening → Applicant sourcing → Interviews → Job Offer → Onboarding → Duty Commencement. Includes head-hunting, recruitment trips, transfer papers, and work contract management.

## Key DocTypes

### Recruitment Pipeline

- **Hiring Settings** — global configuration for recruitment workflows
- **Applicant Lead** — initial lead before formal application
- **Head Hunt** / **Head Hunt Item** — proactive candidate sourcing
- **Recruitment Trip Request** — travel for overseas recruitment

### Onboarding

- **Onboard Employee** — custom onboarding checklist document (not the standard HRMS one)
- **Onboard Employee Activity** — individual activity items within onboarding
- **Onboard Employee Template** — reusable onboarding templates
- **Candidate Orientation** / **Candidate Orientation Check List** — orientation tracking
- **Check List Template** — reusable checklist templates for onboarding steps

### Offers & Contracts

- **Job Offer Templates** / **Offer Terms Table Template** / **Offer Value** — templated offer letter generation
- **Work Contract** — employment contract document
- **Transfer Paper** — for transferring employees between entities. Has a daily checker: `check_signed_workContract_employee_completed`
- **Duty Commencement** — formal duty start record

### Job Opening Enhancements

- **Job Opening Add** / **Job Opening Add Job** — bulk job opening creation
- **Job Applicant Interview Round** — tracks interview rounds per applicant

### Signatures

- **Electronic Signature Declaration** — e-signature capture for contracts and declarations

### ERF (Employee Requisition Form)

- **ERF Employee** — child table linking ERF to employees (in `one_fm/one_fm/` module as core DocType)

## Key Business Rules

1. **ERF drives hiring.** A `Project Manpower Request` (PMR) creates an ERF, which creates a Job Opening, which sources Job Applicants.
2. **Interview flow is multi-round.** `Job Applicant Interview Round` tracks progression. Overrides in `overrides/interview.py` and `overrides/job_applicant.py` customize the standard HRMS interview workflow.
3. **Job Offer is heavily customized.** `overrides/job_offer.py` (17KB) adds salary component details, GRD integration, PAM file linking, and work permit initiation.
4. **Onboarding creates the Employee.** Duty Commencement finalizes the employee record.
5. **GRD dependency.** Hiring flow triggers GRD processes (work permit, residency, medical insurance) for non-local hires.
6. **Transfer Papers have deadline tracking.** `check_signed_workContract_employee_completed` runs at 06:15 daily to notify about incomplete transfers.

## Utilities

- `one_fm/hiring/utils.py` — helper functions for the hiring pipeline
  - `notify_finance_job_offer_salary_advance` (daily scheduler)
  - `update_leave_policy_assignments_expires_today` (daily scheduler)

## Scheduler Events

| Schedule | Method | Purpose |
|---|---|---|
| Daily | `notify_finance_job_offer_salary_advance` | Notify finance about salary advances |
| Daily | `update_leave_policy_assignments_expires_today` | Expire leave policies |
| `15 6 * * *` | `check_signed_workContract_employee_completed` | Transfer paper deadline check |
| `30 12 * * *` | `notify_hr_manager_about_local_transfer` | HR notification for local transfers |

## Cross-Module Dependencies

- **overrides/**: `job_applicant.py`, `job_offer.py`, `job_opening.py`, `interview.py`, `interview_feedback.py` — heavy customization of standard HRMS DocTypes
- **grd/**: Work permit and residency flows triggered after Job Offer acceptance
- **one_fm/one_fm/**: Core DocTypes like `Project Manpower Request`, `ERF Employee`, `PAM Visa`
- **api/doc_events.py**: Training event and certification data updates

## Testing

```bash
bench run-tests --module one_fm.hiring
```

Individual DocType tests live in `hiring/doctype/<name>/test_<name>.py`.
